"""Read public skill catalogs and pinned Markdown; no installer or repository code runs."""
import base64
import json
import re
from urllib.parse import quote, unquote, urlsplit, urljoin
import httpx
import yaml
from .contracts import Failure

HEADERS = {'User-Agent': 'openNews-skills', 'Accept': 'application/vnd.github+json'}


async def fetch_json(client, url, **kwargs):
    try:
        initial_host = urlsplit(url).hostname
        for redirect in range(4):
            async with client.stream('GET', url, **kwargs) as response:
                if response.is_redirect:
                    target = urljoin(str(response.url), response.headers.get('location', ''))
                    parsed = urlsplit(target)
                    hosts = {'skills.sh', 'www.skills.sh'} if initial_host in {'skills.sh', 'www.skills.sh'} else {'api.github.com'}
                    if parsed.scheme != 'https' or parsed.hostname not in hosts or parsed.username or parsed.password or parsed.port not in {None, 443}:
                        raise Failure('VALIDATION_ERROR', 'أعاد المصدر التوجيه إلى عنوان غير مدعوم.')
                    url, kwargs = target, {}
                    continue
                if response.status_code in {403, 429}:
                    raise Failure('RATE_LIMITED', 'وصل المصدر إلى حد الطلبات. حاول لاحقًا أو استخدم رابط مهارة آخر.')
                if response.status_code == 404:
                    raise Failure('VALIDATION_ERROR', 'لم نجد المهارة في هذا الرابط. تحقق أن المستودع عام وأن الملف موجود.')
                response.raise_for_status()
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > 4_000_000:
                        raise Failure('VALIDATION_ERROR', 'المصدر كبير جدًا. استخدم رابط ملف SKILL.md مباشرة.')
                return json.loads(content)
        raise Failure('VALIDATION_ERROR', 'تعذّر تتبع رابط المصدر. انسخ رابط GitHub الحالي.')
    except (httpx.HTTPError, ValueError) as error:
        raise Failure('REQUEST_FAILED', 'تعذّر الوصول إلى مصدر المهارات. تحقق من الاتصال وأعد المحاولة.') from error


def source_parts(address):
    if not isinstance(address, str) or len(address) > 2000:
        raise Failure('VALIDATION_ERROR', 'أضف رابط GitHub أو skills.sh صالحًا.')
    url = urlsplit(address.strip())
    parts = [unquote(part) for part in url.path.strip('/').split('/') if part]
    try:
        port = url.port
    except ValueError as error:
        raise Failure('VALIDATION_ERROR', 'رابط المصدر غير صالح.') from error
    if url.scheme != 'https' or url.username or url.password or port not in {None, 443}:
        raise Failure('VALIDATION_ERROR', 'استخدم رابط HTTPS عامًا دون بيانات دخول.')
    host = (url.hostname or '').lower()
    if host not in {'github.com', 'www.github.com', 'raw.githubusercontent.com', 'skills.sh', 'www.skills.sh'} or len(parts) < 2:
        raise Failure('VALIDATION_ERROR', 'انسخ رابط GitHub الأصلي للمهارة أو رابطها من skills.sh.')
    owner, repo = parts[:2]
    repo = repo.removesuffix('.git')
    if not re.fullmatch(r'[A-Za-z0-9-]{1,39}', owner) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', repo) or repo in {'.', '..'}:
        raise Failure('VALIDATION_ERROR', 'رابط المستودع غير صالح.')
    rest = parts[2:]
    if any(part in {'.', '..'} or '/' in part or '\\' in part or '\x00' in part for part in rest):
        raise Failure('VALIDATION_ERROR', 'مسار المهارة غير صالح.')
    ref, path, desired = '', '', ''
    if host in {'skills.sh', 'www.skills.sh'}:
        desired = rest[-1] if rest else ''
    elif host == 'raw.githubusercontent.com':
        if len(rest) < 2: raise Failure('VALIDATION_ERROR', 'أضف رابط ملف SKILL.md كاملًا.')
        ref, path = rest[0], '/'.join(rest[1:])
    elif rest:
        if rest[0] not in {'tree', 'blob'} or len(rest) < 2:
            raise Failure('VALIDATION_ERROR', 'استخدم رابط المستودع أو مجلد المهارة أو ملف SKILL.md.')
        ref, path = rest[1], '/'.join(rest[2:])
    return owner, repo, ref, path, desired


async def search(query):
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 120:
        raise Failure('VALIDATION_ERROR', 'اكتب موضوعًا للبحث، مثل كتابة المقالات أو research.')
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        data = await fetch_json(client, 'https://skills.sh/api/search', params={'q': query.strip(), 'limit': 20})
    rows = []
    for item in data.get('skills', [])[:20]:
        source = item.get('source', '')
        name = item.get('skillId') or item.get('name', '')
        if not isinstance(source, str) or not re.fullmatch(r'[A-Za-z0-9-]+/[A-Za-z0-9_.-]+', source): continue
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', name): continue
        rows.append({'id': source + '/' + name, 'title': name, 'repository': source,
                     'source_url': 'https://skills.sh/' + source + '/' + name})
    return {'skills': rows, 'source': 'skills.sh', 'query': query.strip()}


async def preview(address):
    owner, repo, ref, path, desired = source_parts(address)
    root = 'https://api.github.com/repos/' + owner + '/' + repo
    async with httpx.AsyncClient(timeout=15, follow_redirects=False, headers=HEADERS) as client:
        metadata = await fetch_json(client, root)
        revision = await fetch_json(client, root + '/commits/' + quote(ref or metadata['default_branch'], safe=''))
        commit = revision['sha']
        if path.endswith('SKILL.md'):
            blob = await fetch_json(client, root + '/contents/' + quote(path, safe='/'), params={'ref': commit})
            if not isinstance(blob, dict) or blob.get('type') != 'file' or blob.get('encoding') != 'base64':
                raise Failure('VALIDATION_ERROR', 'الرابط لا يشير إلى ملف تعليمات Markdown مدعوم.')
            item = {'path': path, 'sha': blob['sha'], 'size': blob.get('size', 0)}
            if item['size'] > 100_000:
                raise Failure('VALIDATION_ERROR', 'تعليمات المهارة أطول من الحد المدعوم. اختر مهارة أقصر.')
            tree = {'tree': []}
        else:
            tree = await fetch_json(client, root + '/git/trees/' + commit, params={'recursive': '1'})
            candidates = [item for item in tree.get('tree', []) if item.get('type') == 'blob' and
                          (item.get('path') == 'SKILL.md' or item.get('path', '').endswith('/SKILL.md'))]
            if path.endswith('SKILL.md'):
                candidates = [item for item in candidates if item['path'] == path]
            elif path:
                candidates = [item for item in candidates if item['path'] == path.rstrip('/') + '/SKILL.md' or item['path'].startswith(path.rstrip('/') + '/')]
            if desired:
                candidates = [item for item in candidates if item['path'].split('/')[-2:-1] == [desired]]
            if not candidates:
                raise Failure('VALIDATION_ERROR', 'لم نجد ملف SKILL.md في هذا المصدر. جرّب رابط الملف مباشرة.')
            if len(candidates) > 1:
                return {'kind': 'collection', 'repository': owner + '/' + repo, 'truncated': bool(tree.get('truncated')),
                        'skills': [{'id': item['path'], 'title': item['path'].removesuffix('/SKILL.md'),
                                    'source_url': f'https://github.com/{owner}/{repo}/blob/{commit}/' + quote(item['path'], safe='/')} for item in candidates[:100]]}
            item = candidates[0]
            if item.get('size', 0) > 100_000:
                raise Failure('VALIDATION_ERROR', 'تعليمات المهارة أطول من الحد المدعوم. اختر مهارة أقصر.')
            blob = await fetch_json(client, root + '/git/blobs/' + item['sha'])
    try:
        text = base64.b64decode(blob['content'], validate=False).decode('utf-8-sig')
        header, body = {}, text
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', text, re.S)
        if match:
            header = yaml.safe_load(match[1]) or {}
            if not isinstance(header, dict): raise ValueError()
            body = match[2]
        if not body.strip() or '\x00' in body: raise ValueError()
    except (ValueError, UnicodeError, yaml.YAMLError) as error:
        raise Failure('VALIDATION_ERROR', 'تعذّر قراءة تعليمات المهارة كنص Markdown.') from error
    folder = item['path'].rsplit('/', 1)[0] + '/' if '/' in item['path'] else ''
    supporting = bool(re.search(r'(?:scripts|references|assets|templates)/|\$\{[^}]*SKILL[^}]*\}', body, re.I)) or any(row.get('type') == 'blob' and row.get('path', '').startswith(folder) and
                     row.get('path') != item['path'] for row in tree.get('tree', []))
    title = str(header.get('name') or (item['path'].split('/')[-2] if '/' in item['path'] else repo))
    description = str(header.get('description') or 'Writing instructions imported from GitHub.')
    identifier = re.sub(r'[^a-z0-9-]+', '-', title.lower()).strip('-')[:40] or 'imported-skill'
    if not identifier[0].isalpha(): identifier = 'skill-' + identifier[:34]
    license_name = header.get('license') or (metadata.get('license') or {}).get('spdx_id') or ''
    return {'kind': 'skill', 'id': identifier, 'title': title[:100], 'description': description[:300],
            'content': body.strip(), 'limit': 12000, 'repository': owner + '/' + repo,
            'source_url': f'https://github.com/{owner}/{repo}/blob/{commit}/' + quote(item['path'], safe='/'),
            'source_sha': item['sha'], 'license': str(license_name)[:100],
            'supporting_files': supporting, 'requires_tools': bool(header.get('allowed-tools'))}
