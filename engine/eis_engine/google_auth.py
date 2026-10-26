"""Google desktop OAuth for Vertex AI, consumed by Agno's Gemini adapter.

Only fixed Google endpoints are used. Registration and tokens stay in the
workspace's owner-only credential store, never in profile config or snapshots.
"""
import asyncio
import base64
import hashlib
import json
import re
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlsplit
import httpx
from .chatgpt_auth import ChatGPTAuth, credential_path, read_record, write_record, _locks
from .contracts import Failure
from .storage import now, uid

AUTHORIZE = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN = 'https://oauth2.googleapis.com/token'
SCOPE = 'https://www.googleapis.com/auth/cloud-platform'
ERROR = 'تعذّر ربط Google Cloud. تحقق من إعداد تطبيق سطح المكتب وصلاحيات المشروع ثم حاول مجددًا.'
ENTRY = dict(id='google-oauth', name='Gemini — Google Cloud', module='agno.models.google', class_name='Gemini',
             status='ready', fields=['project_id','location'], default_model='', credential='oauth',
             credential_fields=[], note='Google Cloud OAuth; Vertex AI billing applies.', live_validated=False)


def client():
    return httpx.AsyncClient(timeout=25, follow_redirects=False, trust_env=False)


async def exchange(http, data):
    try:
        response = await http.post(TOKEN, data=data)
    except httpx.HTTPError:
        raise Failure('NETWORK_ERROR', 'تعذّر الوصول إلى Google. تحقق من الشبكة وحاول مجددًا.') from None
    if response.status_code == 429: raise Failure('RATE_LIMITED', 'طلب Google الانتظار قبل المحاولة مجددًا.')
    if response.status_code >= 500: raise Failure('PROVIDER_UNAVAILABLE', 'Google غير متاح مؤقتًا. حاول لاحقًا.')
    if response.is_redirect or len(response.content) > 65536: raise Failure('AUTH_REQUIRED', ERROR)
    try: value = response.json()
    except ValueError: raise Failure('AUTH_REQUIRED', ERROR) from None
    if not response.is_success or not isinstance(value, dict): raise Failure('AUTH_REQUIRED', ERROR)
    return value


def tokens_record(tokens, base):
    scope = tokens.get('scope', base.get('scope', ''))
    refresh = tokens.get('refresh_token', base.get('refresh_token'))
    expires = tokens.get('expires_in')
    if (not isinstance(scope,str) or SCOPE not in scope.split() or
        tokens.get('token_type','').lower() != 'bearer' or
        type(expires) not in (int,float) or not 0 < expires <= 86400 or
        any(not isinstance(v,str) or not 1 <= len(v) <= 16000 for v in (tokens.get('access_token'),refresh))):
        raise Failure('AUTH_REQUIRED', ERROR)
    return base | dict(access_token=tokens['access_token'], refresh_token=refresh, scope=scope, expires_at=time.time()+expires)


async def access_token(profile):
    path = credential_path(profile)
    async with _locks.setdefault(str(path), asyncio.Lock()):
        try:
            record = read_record(path)
            if record.get('issuer') != 'google' or not record.get('refresh_token') or SCOPE not in record.get('scope','').split():
                raise Failure('AUTH_REQUIRED', ERROR)
            if record.get('expires_at',0) > time.time()+60: return record['access_token']
            async with client() as http:
                tokens = await exchange(http, dict(grant_type='refresh_token', client_id=record['client_id'],
                    client_secret=record['client_secret'], refresh_token=record['refresh_token']))
            renewed = tokens_record(tokens, record)
            write_record(path, renewed)
            return renewed['access_token']
        except Failure: raise
        except Exception: raise Failure('AUTH_REQUIRED', ERROR) from None


class GoogleAuth(ChatGPTAuth):
    async def start(self, payload):
        if payload.get('provider_key') != 'google-oauth': raise Failure('VALIDATION_ERROR', ERROR)
        existing = None
        if payload.get('profile_id'):
            profile = self.service.profile(payload['profile_id'])
            if profile['provider_key'] != 'google-oauth': raise Failure('VALIDATION_ERROR', ERROR)
            existing = read_record(credential_path(profile)) | {'profile_id':profile['id']}
            registration = existing
            config = json.loads(profile['config_json'])
        else:
            registration = payload.get('registration', {})
            config = payload.get('config', {})
        if not isinstance(registration,dict) or not isinstance(config,dict): raise Failure('VALIDATION_ERROR', ERROR)
        client_id, secret = registration.get('client_id',''), registration.get('client_secret','')
        project, location = config.get('project_id',''), config.get('location','us-central1')
        if (not isinstance(client_id,str) or not re.fullmatch(r'[a-zA-Z0-9_-]+\.apps\.googleusercontent\.com',client_id) or
            not isinstance(secret,str) or not 1 <= len(secret) <= 512 or
            not isinstance(project,str) or not re.fullmatch(r'[a-z][a-z0-9-]{4,61}[a-z0-9]',project) or
            not isinstance(location,str) or not re.fullmatch(r'[a-z]+-[a-z]+[0-9]',location)):
            raise Failure('VALIDATION_ERROR', ERROR)
        for attempt in list(self.attempts.values()):
            if attempt['status']=='waiting': self.cancel(attempt['id'])
        while len(self.attempts)>=20: self.attempts.pop(next(iter(self.attempts)))
        verifier = secrets.token_urlsafe(64)
        attempt = dict(id=uid(),status='waiting',state=secrets.token_urlsafe(32),verifier=verifier,claimed=False,
            existing=existing,registration=dict(client_id=client_id,client_secret=secret),
            config=dict(project_id=project,location=location),language='ar' if payload.get('language')=='ar' else 'en')
        server = await asyncio.start_server(lambda r,w:self.callback(attempt,r,w),'127.0.0.1',0,limit=16384)
        attempt['server']=server
        attempt['redirect_uri']=f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}/auth/callback"
        self.attempts[attempt['id']]=attempt
        attempt['timer']=asyncio.get_running_loop().call_later(600,self.expire,attempt['id'])
        params=dict(client_id=client_id,redirect_uri=attempt['redirect_uri'],response_type='code',scope=SCOPE,
            access_type='offline',prompt='consent',state=attempt['state'],code_challenge_method='S256',
            code_challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('='))
        return dict(auth_id=attempt['id'],authorization_url=AUTHORIZE+'?'+urlencode(params))

    def expire(self, identifier):
        attempt = self.attempts.get(identifier)
        if attempt and attempt["status"] == "waiting":
            self.finish(attempt, "failed", ERROR)

    def finish(self, attempt, status, error=None):
        super().finish(attempt,status,error)
        attempt.pop('registration',None)
        attempt.pop('existing',None)

    async def callback(self, attempt, reader, writer):
        status, accepted = 400, False
        try:
            header = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'),5)
            lines = header.decode('ascii').split('\r\n')
            method,target,_ = lines[0].split(' ',2)
            uri = urlsplit(target)
            headers = dict((k.lower(),v.strip()) for k,v in (x.split(':',1) for x in lines[1:] if ':' in x))
            if method!='GET' or uri.path!='/auth/callback' or uri.scheme or headers.get('host')!=urlsplit(attempt['redirect_uri']).netloc: raise ValueError()
            query = parse_qs(uri.query,keep_blank_values=True,strict_parsing=True)
            if any(len(v)!=1 for v in query.values()): raise ValueError()
            values = {k:v[0] for k,v in query.items()}
            if attempt['status']!='waiting' or attempt['claimed'] or not secrets.compare_digest(values.get('state',''),attempt.get('state','!')): raise ValueError()
            attempt['claimed']=True; accepted=True
            if values.get('error') or not values.get('code'): raise ValueError()
            registration = dict(attempt['registration'])
            async with client() as http:
                tokens = await exchange(http, registration | dict(grant_type='authorization_code',code=values['code'],
                    code_verifier=attempt['verifier'],redirect_uri=attempt['redirect_uri']))
            record = tokens_record(tokens, registration | {'issuer':'google'})
            if attempt['status']!='waiting': raise ValueError()
            existing = attempt['existing']; s=self.service
            pid = existing['profile_id'] if existing else uid()
            path = s.store.path.parent/'.providers'/(pid+'.json')
            write_record(path,record)
            try:
                with s.db:
                    if existing: s.db.execute('UPDATE provider_profiles SET updated_at=? WHERE id=? AND workspace_id=?',(now(),pid,s.ws))
                    else:
                        s.db.execute('INSERT INTO provider_profiles VALUES(?,?,?,?,?,?,?,?)',(pid,s.ws,'google-oauth','',json.dumps(attempt['config']),pid,now(),now()))
                        s.db.execute('INSERT INTO provider_preferences VALUES(?,?,?,1)',(pid,s.ws,'Gemini — '+attempt['config']['project_id']))
            except Exception:
                if not existing: path.unlink(missing_ok=True)
                raise
            s.connections.generations[pid]=s.connections.generation(pid)+1
            # OAuth succeeded; API/project entitlement still needs a connection check.
            s.connections.set(pid,'configured',reset=True)
            attempt['profile_id']=pid
            self.finish(attempt,'complete'); status=200
        except Exception:
            if accepted and attempt['status']=='waiting': self.finish(attempt,'failed',ERROR)
        finally:
            from .auth_page import callback_page
            body=callback_page(status==200,attempt.get('language','en'))
            writer.write(f"HTTP/1.1 {status} Result\r\nContent-Type: text/html; charset=utf-8\r\nCache-Control: no-store\r\nContent-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'\r\nReferrer-Policy: no-referrer\r\nConnection: close\r\nContent-Length: {len(body)}\r\n\r\n".encode()+body)
            try: await writer.drain()
            except (OSError,ConnectionError): pass
            writer.close()
            try: await writer.wait_closed()
            except (OSError,ConnectionError): pass
