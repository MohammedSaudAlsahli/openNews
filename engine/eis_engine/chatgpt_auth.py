"""Official local-app Sign in with ChatGPT. No shared-client IDs or private APIs.

Protocol: https://developers.openai.com/siwc/token-sharing-open-source/sign-in
Credentials are never serialized to IPC, SQLite, logs, or browser callback pages.
"""
import asyncio
import base64
import hashlib
import json
import os
import secrets
import stat
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import UUID
import httpx
import jwt
from .contracts import Failure
from .storage import encode, now, uid

ISSUER = "https://auth.openai.com"
RESOURCE = "https://api.openai.com/v1"
DISCOVERY = ISSUER + "/.well-known/openid-configuration"
AUTHORIZE = ISSUER + "/api/accounts/authorize"
TOKEN = ISSUER + "/api/accounts/oauth/token"
JWKS = ISSUER + "/.well-known/jwks.json"
SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
ERROR = "تعذّر تسجيل الدخول إلى ChatGPT. حاول مجددًا."
EXPIRED = "انتهت جلسة ChatGPT. سجّل الدخول مجددًا."
ENTRY = dict(id="openai-chatgpt",name="ChatGPT",module="eis_engine.chatgpt_auth",class_name="ChatGPTResponses",
             status="ready",fields=[],default_model="",credential="oauth",credential_fields=[],
             note="تسجيل الدخول باشتراك ChatGPT عبر المتصفح.",live_validated=False,default_base_url=RESOURCE)
_locks = {}


def client():
    return httpx.AsyncClient(timeout=25, follow_redirects=False, trust_env=False)


def private_directory(directory):
    if any(p.is_symlink() for p in (directory,*directory.parents)):
        raise Failure("AUTH_REQUIRED",EXPIRED)
    directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    info=directory.stat()
    if stat.S_IMODE(info.st_mode)!=0o700 or info.st_uid!=os.getuid():
        raise Failure("AUTH_REQUIRED",EXPIRED)


def directory_fd(directory):
    private_directory(directory)
    fd=os.open("/",os.O_RDONLY|os.O_DIRECTORY)
    try:
        for part in directory.parts[1:]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd); fd=child
        info=os.fstat(fd)
        if stat.S_IMODE(info.st_mode)!=0o700 or info.st_uid!=os.getuid():
            raise Failure("AUTH_REQUIRED",EXPIRED)
        return fd
    except BaseException:
        os.close(fd); raise


def read_record(path):
    directory=directory_fd(path.parent)
    try:
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        with os.fdopen(fd) as stream:
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode)!=0o600 or info.st_uid!=os.getuid() or info.st_size>65536:
                raise Failure("AUTH_REQUIRED",EXPIRED)
            result=json.load(stream)
        if not isinstance(result,dict): raise Failure("AUTH_REQUIRED",EXPIRED)
        return result
    finally: os.close(directory)


def write_record(path, record):
    data=json.dumps(record,ensure_ascii=False).encode()
    if len(data)>65536: raise Failure("AUTH_REQUIRED",ERROR)
    directory=directory_fd(path.parent)
    temporary=".oauth-"+secrets.token_hex(16)
    try:
        try:
            info=os.stat(path.name,dir_fd=directory,follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid(): raise Failure("AUTH_REQUIRED",EXPIRED)
        except FileNotFoundError: pass
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
        with os.fdopen(fd,"wb") as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary,path.name,src_dir_fd=directory,dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        try: os.unlink(temporary,dir_fd=directory)
        except FileNotFoundError: pass
        os.close(directory)


def credential_path(profile):
    path=Path(profile["credential_path"])
    UUID(path.stem)
    if not path.is_absolute() or path.suffix!=".json" or path.parent.name!=".providers":
        raise Failure("AUTH_REQUIRED",EXPIRED)
    return path


async def json_request(http, method, url, **kwargs):
    try:
        response = await http.request(method, url, **kwargs)
    except httpx.HTTPError:
        raise Failure("NETWORK_ERROR", "تعذّر الوصول إلى المزوّد. بيانات دخولك محفوظة؛ تحقق من الشبكة وحاول مجددًا.") from None
    if response.status_code >= 500:
        raise Failure("PROVIDER_UNAVAILABLE", "الخدمة غير متاحة مؤقتًا. بيانات دخولك محفوظة؛ حاول لاحقًا.")
    if response.status_code == 429: raise response_failure(status=429)
    if response.status_code == 403: raise response_failure(status=403)
    if response.status_code == 401: raise Failure("AUTH_REQUIRED", EXPIRED)
    if response.is_redirect or len(response.content)>1000000:
        raise Failure("PROVIDER_UNAVAILABLE", ERROR)
    try: value = response.json()
    except ValueError: raise Failure("PROVIDER_UNAVAILABLE", ERROR) from None
    if not isinstance(value, dict): raise Failure("PROVIDER_UNAVAILABLE", ERROR)
    if not response.is_success:
        code = value.get("error")
        if isinstance(code, dict): code = code.get("code")
        if code in {"invalid_grant", "invalid_refresh_token", "token_expired", "invalid_token"}:
            raise Failure("AUTH_REQUIRED", EXPIRED)
        raise Failure("PROVIDER_UNAVAILABLE", ERROR)
    return value


async def validate_identity(http, token, client_id, nonce=None):
    if not isinstance(token,str) or len(token)>32000: raise Failure("AUTH_REQUIRED",ERROR)
    header=jwt.get_unverified_header(token)
    if header.get("alg") not in {"RS256","ES256"} or not isinstance(header.get("kid"),str):
        raise Failure("AUTH_REQUIRED",ERROR)
    keys=await json_request(http,"GET",JWKS)
    key=next((x for x in keys.get("keys",[]) if x.get("kid")==header["kid"] and x.get("use","sig")=="sig"),None)
    if key is None: raise Failure("AUTH_REQUIRED",ERROR)
    public=jwt.PyJWK.from_dict(key,algorithm=header["alg"]).key
    claims=jwt.decode(token,public,algorithms=[header["alg"]],audience=client_id,issuer=ISSUER,leeway=5,
                      options={"require":["sub","exp","iat","iss","aud"]})
    if not isinstance(claims["sub"],str) or not claims["sub"] or (nonce is not None and claims.get("nonce")!=nonce):
        raise Failure("AUTH_REQUIRED",ERROR)
    if isinstance(claims["aud"],list) and len(claims["aud"])>1 and claims.get("azp")!=client_id:
        raise Failure("AUTH_REQUIRED",ERROR)
    return claims


def token_record(tokens, base):
    scope=tokens.get("scope")
    if not isinstance(scope,str) or not {"resource.invoke","chatgpt.tokens.use.direct"}.issubset(scope.split()):
        raise Failure("PERMISSION_DENIED","لم يُمنح التطبيق إذن استخدام اشتراك ChatGPT.")
    if tokens.get("token_type","").lower()!="bearer": raise Failure("AUTH_REQUIRED",ERROR)
    for key in ("access_token","refresh_token"):
        if not isinstance(tokens.get(key),str) or not 1<=len(tokens[key])<=32000: raise Failure("AUTH_REQUIRED",ERROR)
    expires=tokens.get("expires_in")
    if not isinstance(expires,(float,int)) or not 0<expires<=86400: raise Failure("AUTH_REQUIRED",ERROR)
    return base | {k:tokens[k] for k in ("access_token","refresh_token","token_type","scope")} | {"expires_at":time.time()+expires}


async def access_token(profile):
    """Engine is workspace-single-instance; serialize rotating refresh within it."""
    path=credential_path(profile)
    lock=_locks.setdefault(str(path),asyncio.Lock())
    async with lock:
        try:
            record=read_record(path)
            if record.get("issuer")!=ISSUER or not record.get("client_id") or not record.get("subject"):
                raise Failure("AUTH_REQUIRED",EXPIRED)
            if not {"resource.invoke","chatgpt.tokens.use.direct"}.issubset(record.get("scope","").split()):
                raise Failure("AUTH_REQUIRED",EXPIRED)
            if record["expires_at"]>time.time()+60: return record["access_token"]
            async with client() as http:
                tokens=await json_request(http,"POST",TOKEN,data={"grant_type":"refresh_token","client_id":record["client_id"],"refresh_token":record["refresh_token"],"resource":RESOURCE})
                # OAuth permits scope omission during renewal: preserve the granted set.
                tokens.setdefault("scope",record["scope"])
                if tokens.get("id_token"):
                    identity=await validate_identity(http,tokens["id_token"],record["client_id"])
                    if identity["sub"]!=record["subject"]: raise Failure("AUTH_REQUIRED",EXPIRED)
                    record["id_token"]=tokens["id_token"]
                renewed=token_record(tokens,record)
                write_record(path,renewed)
                return renewed["access_token"]
        except Failure: raise
        except Exception: raise Failure("AUTH_REQUIRED",EXPIRED) from None


class ChatGPTAuth:
    def __init__(self,service):
        self.service=service
        self.attempts={}

    async def start(self,payload):
        if payload.get("provider_key") not in {"openai","openai-chatgpt"}: raise Failure("VALIDATION_ERROR",ERROR)
        existing = None
        if payload.get("profile_id"):
            profile = self.service.profile(payload["profile_id"])
            if profile["provider_key"] != "openai-chatgpt": raise Failure("VALIDATION_ERROR",ERROR)
            try: registration = read_record(credential_path(profile))
            except FileNotFoundError: registration = {}
            existing = registration | {"profile_id":profile["id"]}
        # One pending browser attempt per workspace; bounded retained status records.
        for attempt in list(self.attempts.values()):
            if attempt["status"]=="waiting": self.cancel(attempt["id"])
        while len(self.attempts)>=20: self.attempts.pop(next(iter(self.attempts)))
        directory=self.service.store.path.parent/".chatgpt"
        host_path=directory/"host.json"
        if host_path.exists(): host=read_record(host_path)["host_id"]
        else:
            host="urn:uuid:"+uid(); write_record(host_path,{"host_id":host})
        verifier=secrets.token_urlsafe(64)
        attempt={"id":uid(),"status":"waiting","state":secrets.token_urlsafe(32),"nonce":secrets.token_urlsafe(32),"verifier":verifier,"host_id":host,"claimed":False,"existing":existing,"language":"ar" if payload.get("language")=="ar" else "en"}
        server=await asyncio.start_server(lambda reader,writer:self.callback(attempt,reader,writer),"127.0.0.1",0,limit=16384)
        attempt["server"]=server
        port=server.sockets[0].getsockname()[1]
        attempt["redirect_uri"]=f"http://127.0.0.1:{port}/auth/callback"
        self.attempts[attempt["id"]]=attempt
        attempt["timer"]=asyncio.get_running_loop().call_later(600,self.expire,attempt["id"])
        params={"client_id":"dynamic_agent_client","agent_name_hint":"Editorial Intelligence Studio","ext_agent_host_id":host,
                "response_type":"code","redirect_uri":attempt["redirect_uri"],"scope":SCOPES,"resource":RESOURCE,
                "state":attempt["state"],"nonce":attempt["nonce"],"code_challenge_method":"S256",
                "code_challenge":base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")}
        if existing and existing.get("client_id"): params["client_id"] = existing["client_id"]; params.pop("agent_name_hint")
        return {"auth_id":attempt["id"],"authorization_url":AUTHORIZE+"?"+urlencode(params)}

    def status(self,identifier):
        attempt=self.attempts.get(identifier)
        if not attempt: raise Failure("VALIDATION_ERROR",ERROR)
        return {k:attempt[k] for k in ("status","profile_id","error") if k in attempt}

    def finish(self,attempt,status,error=None):
        attempt["status"]=status
        if error: attempt["error"]=error
        attempt["server"].close(); attempt["timer"].cancel()
        for key in ("state","nonce","verifier"): attempt.pop(key,None)

    def expire(self,identifier):
        attempt=self.attempts.get(identifier)
        if attempt and attempt["status"]=="waiting": self.finish(attempt,"failed",ERROR)

    def cancel(self,identifier):
        attempt=self.attempts.get(identifier)
        if not attempt: raise Failure("VALIDATION_ERROR",ERROR)
        if attempt["status"]=="waiting": self.finish(attempt,"cancelled")
        return {"cancelled":True}

    async def callback(self,attempt,reader,writer):
        status=400
        accepted=False
        message="Sign-in could not be completed. Return to Editorial Intelligence Studio."
        try:
            header=await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"),timeout=5)
            lines=header.decode("ascii").split("\r\n")
            method,target,_=lines[0].split(" ",2)
            uri=urlsplit(target)
            headers=dict(line.split(": ",1) for line in lines[1:] if ": " in line)
            expected_host=urlsplit(attempt["redirect_uri"]).netloc
            if method!="GET" or uri.path!="/auth/callback" or uri.scheme or headers.get("Host",headers.get("host"))!=expected_host:
                raise ValueError()
            query=parse_qs(uri.query,keep_blank_values=True,strict_parsing=True)
            if any(len(v)!=1 for v in query.values()): raise ValueError()
            values={k:v[0] for k,v in query.items()}
            if attempt["status"]!="waiting" or attempt["claimed"] or not secrets.compare_digest(values.get("state",""),attempt.get("state","!")):
                raise ValueError()
            attempt["claimed"]=True
            accepted=True
            if values.get("error"): raise Failure("AUTH_REQUIRED",ERROR)
            existing=attempt["existing"]
            client_id=values.get("client_id",existing.get("client_id", "") if existing else "")
            if existing and existing.get("client_id") and client_id!=existing["client_id"]: raise Failure("AUTH_REQUIRED",ERROR)
            if not client_id or client_id=="dynamic_agent_client" or len(client_id)>200 or not values.get("code"):
                raise Failure("AUTH_REQUIRED",ERROR)
            async with client() as http:
                discovery=await json_request(http,"GET",DISCOVERY)
                if any(discovery.get(k)!=v for k,v in {"issuer":ISSUER,"authorization_endpoint":AUTHORIZE,"token_endpoint":TOKEN,"jwks_uri":JWKS}.items()):
                    raise Failure("AUTH_REQUIRED",ERROR)
                tokens=await json_request(http,"POST",TOKEN,data={"grant_type":"authorization_code","client_id":client_id,"code":values["code"],"code_verifier":attempt["verifier"],"redirect_uri":attempt["redirect_uri"],"resource":RESOURCE})
                identity=await validate_identity(http,tokens.get("id_token"),client_id,attempt["nonce"])
                if existing and existing.get("subject") and identity["sub"]!=existing["subject"]: raise Failure("AUTH_REQUIRED",ERROR)
                record=token_record(tokens,{"issuer":ISSUER,"subject":identity["sub"],"client_id":client_id,"ext_agent_host_id":attempt["host_id"],"id_token":tokens["id_token"]})
            # Cancel/expiry may occur while token/JWKS requests are awaiting.
            if attempt["status"]!="waiting": raise ValueError()
            pid=existing["profile_id"] if existing else uid(); s=self.service
            path=s.store.path.parent/".providers"/(pid+".json")
            write_record(path,record)
            try:
                with s.db:
                    if existing:
                        s.db.execute("UPDATE provider_profiles SET updated_at=? WHERE id=? AND workspace_id=?",(now(),pid,s.ws))
                    else:
                        s.db.execute("INSERT INTO provider_profiles VALUES(?,?,?,?,?,?,?,?)",(pid,s.ws,"openai-chatgpt","","{}",pid,now(),now()))
                    email=identity.get("email")
                    label="ChatGPT"+(" — "+email[:120] if isinstance(email,str) else "")
                    if not existing: s.db.execute("INSERT INTO provider_preferences VALUES(?,?,?,1)",(pid,s.ws,label))
            except Exception:
                if not existing: path.unlink(missing_ok=True)
                raise
            s.connections.generations[pid] = s.connections.generation(pid) + 1
            s.connections.set(pid, "connected", reset=True)
            attempt["profile_id"]=pid
            self.finish(attempt,"complete")
            status=200; message="Connected. Return to Editorial Intelligence Studio."
        except Exception:
            if accepted and attempt["status"]=="waiting": self.finish(attempt,"failed",ERROR)
        finally:
            from .auth_page import callback_page
            body=callback_page(status == 200, attempt.get("language", "en"))
            writer.write(f"HTTP/1.1 {status} Result\r\nContent-Type: text/html; charset=utf-8\r\nCache-Control: no-store\r\nContent-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'\r\nReferrer-Policy: no-referrer\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\nContent-Length: {len(body)}\r\n\r\n".encode()+body)
            try: await writer.drain()
            except (OSError,ConnectionError): pass
            writer.close()
            try: await writer.wait_closed()
            except (OSError,ConnectionError): pass

    async def close(self):
        for attempt in self.attempts.values():
            if attempt["status"]=="waiting": self.finish(attempt,"cancelled")
            await attempt["server"].wait_closed()


async def discover_models(profile):
    token=await access_token(profile)
    async with client() as http:
        result=await json_request(http,"GET",RESOURCE+"/models",headers={"Authorization":"Bearer "+token})
    models=[]
    for item in result.get("models",[]):
        if isinstance(item,dict) and item.get("visibility")=="list" and isinstance(item.get("slug"),str) and 0<len(item["slug"])<=200:
            models.append({"id":item["slug"],"name":item.get("display_name") or item["slug"],"available":True})
    return {"models":models,"source":"ChatGPT account"}


# Agno retains schema prompting, validation, and orchestration. This adapter consumes
# HTTP streaming internally and refuses failed/incomplete/truncated streams.
from agno.models.openai import OpenAIResponses

def response_failure(error=None, status=None):
    """Map public error codes to safe recovery text; never expose provider bodies."""
    code = error.get("code") if isinstance(error, dict) else getattr(error, "code", None)
    if code == "subscription_sharing_usage_limit_exceeded":
        return Failure("RATE_LIMITED", "وصل هذا التطبيق إلى حد استخدام اشتراك ChatGPT. راجع الاستخدام في إعدادات ChatGPT أو حاول لاحقًا.")
    if code in {"subscription_sharing_usage_unavailable", "subscription_sharing_user_unavailable"} or (status and status >= 500):
        return Failure("PROVIDER_UNAVAILABLE", "خدمة ChatGPT غير متاحة مؤقتًا. اتصال حسابك محفوظ؛ حاول لاحقًا.")
    if code in {"subscription_sharing_user_not_eligible", "chatpass_v2_scope_not_authorized", "chatpass_v2_invalid_authorization_context"} or status == 403:
        return Failure("PERMISSION_DENIED", "حساب ChatGPT متصل، لكن صلاحيات الحساب أو سياسة مساحة العمل لا تسمح بهذا الطلب.")
    if code == "subscription_sharing_invalid_user" or status == 401:
        return Failure("AUTH_REQUIRED", EXPIRED)
    if status == 429:
        return Failure("RATE_LIMITED", "بلغ الطلب حد استخدام ChatGPT. انتظر قليلًا ثم حاول مجددًا.")
    if code in {"subscription_sharing_unsupported_capability", "subscription_sharing_route_not_supported"} or status in {400, 404, 422}:
        return Failure("MODEL_REQUEST_REJECTED", "حساب ChatGPT متصل، لكن الخدمة رفضت النموذج أو صيغة الطلب. حدّث قائمة النماذج واختر نموذجًا متاحًا.")
    return Failure("MODEL_RESPONSE_INCOMPLETE", "لم يكتمل رد ChatGPT. اتصال حسابك محفوظ؛ حاول مجددًا.")


class ChatGPTResponses(OpenAIResponses):
    async def ainvoke(self,messages,assistant_message,response_format=None,tools=None,tool_choice=None,run_response=None,compress_tool_results=False):
        from openai import APIStatusError, APIConnectionError, APITimeoutError
        if tools: raise Failure("MODEL_UNSUPPORTED","أدوات ChatGPT غير مفعلة في هذا الاتصال.")
        items=self._format_messages(messages,compress_tool_results,tools=None)
        assistant_message.metrics.start_timer()
        complete=None
        finalized={}
        stream=None
        try:
            stream=await self.get_async_client().responses.create(model=self.id,input=items,store=False,stream=True)
            async for event in stream:
                if event.type=="response.output_item.done":
                    # Plan-usage streams can omit all items from response.completed.
                    # Keep finalized items (including annotations/refusals), not partial deltas.
                    finalized[event.output_index]=event.item
                elif event.type=="response.completed": complete=event.response
                elif event.type=="response.failed":
                    raise response_failure(getattr(event.response,"error",None))
                elif event.type=="error":
                    raise response_failure(event)
                elif event.type=="response.incomplete":
                    raise response_failure()
        except APIStatusError as error:
            body=error.body if isinstance(error.body,dict) else {}
            raise response_failure(body.get("error",body),error.status_code) from None
        except (APIConnectionError, APITimeoutError):
            raise Failure("NETWORK_ERROR","تعذّر الوصول إلى ChatGPT. تحقق من الإنترنت وحاول مجددًا؛ لا تحتاج إلى تسجيل الدخول من جديد.") from None
        finally:
            if stream is not None: await stream.close()
            assistant_message.metrics.stop_timer()
        if complete is None or complete.status!="completed":
            raise response_failure()
        if not complete.output and finalized:
            complete=complete.model_copy(update={"output":[finalized[index] for index in sorted(finalized)]})
        parsed=self._parse_provider_response(complete,response_format=response_format)
        if not parsed.content:
            raise Failure("MODEL_RESPONSE_INVALID","اتصال ChatGPT ناجح، لكن الرد لا يحتوي نصًا صالحًا. حاول مجددًا أو اختر نموذجًا آخر.")
        return parsed
