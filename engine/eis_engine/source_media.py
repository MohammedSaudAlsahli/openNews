"""Load only media recorded in a workspace article or saved chat citation."""
import hashlib
import os
import tempfile
from .contracts import Failure


def media_type(body):
    if body.startswith(b'\x89PNG\r\n\x1a\n'): return 'image/png'
    if body.startswith(b'\xff\xd8\xff'): return 'image/jpeg'
    if body.startswith((b'GIF87a', b'GIF89a')): return 'image/gif'
    if body.startswith(b'RIFF') and body[8:12] == b'WEBP': return 'image/webp'
    if body.startswith(b'RIFF') and body[8:12] == b'WAVE': return 'audio/wav'
    if body.startswith(b'ID3') or (len(body)>2 and body[0]==255 and body[1]&0xe0==0xe0): return 'audio/mpeg'
    if body.startswith(b'OggS'): return 'audio/ogg'
    if body[4:8] == b'ftyp':
        if body[8:12] in (b'avif', b'avis'): return 'image/avif'
        return 'video/mp4'
    if body.startswith(b'\x1a\x45\xdf\xa3'): return 'video/webm'
    return None


async def load(service, payload):
    import json
    article_id, message_id = payload.get('article_id'), payload.get('message_id')
    blocks = []
    if article_id:
        blocks = service.news.article(article_id, mark_read=False).get('reader', {}).get('blocks', [])
    elif message_id:
        rows = service.store.rows('SELECT citations_json FROM chat_messages WHERE id=? AND workspace_id=?', (message_id, service.ws))
        if rows:
            blocks = [b for c in json.loads(rows[0]['citations_json']) for b in c.get('media', [])]
    block = next((b for b in blocks if b.get('url') == payload.get('url') and b.get('type') in {'image','audio','video'}), None)
    if not block: raise Failure('VALIDATION_ERROR', 'Media is not available in this source.')
    # Existing public transport validates DNS and every redirect and caps downloads at 4 MiB.
    cache = service.store.path.parent / 'source-media'
    cache.mkdir(mode=0o700, exist_ok=True)
    path = cache / (hashlib.sha256(block['url'].encode()).hexdigest() + '.media')
    async with service.news.image_slots:
        if path.exists():
            body = path.read_bytes()
        else:
            result = await service.news.fetch(block['url'], None)
            body = result['body']
        if len(body)>4*1024*1024: raise Failure('VALIDATION_ERROR', 'Media is too large for inline playback.')
    mime = media_type(body)
    if not mime or (block['type']=='image' and not mime.startswith('image/')) or (block['type']!='image' and mime.startswith('image/')):
        raise Failure('VALIDATION_ERROR', 'Unsupported media. Open the original source.')
    if not path.exists():
        files = sorted(cache.glob('*.media'), key=lambda f:f.stat().st_mtime)
        size = sum(f.stat().st_size for f in files)
        while files and size+len(body)>64*1024*1024:
            oldest=files.pop(0);size-=oldest.stat().st_size;oldest.unlink(missing_ok=True)
        with tempfile.NamedTemporaryFile(dir=cache, delete=False) as temporary:
            temporary.write(body)
        try: os.replace(temporary.name,path)
        finally:
            if os.path.exists(temporary.name): os.unlink(temporary.name)
    os.utime(path,None)
    return {'path':str(path), 'mime':mime}
