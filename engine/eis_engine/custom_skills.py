"""Workspace writing guides: bounded text and metadata, never executable plugins."""
import json
import os
import re
import tempfile
from .contracts import Failure

LIMIT = 12000


def read(store):
    path = store.path.parent / 'instructions' / 'custom-skills.json'
    if not path.exists():
        return {}
    # A damaged registry must not be silently overwritten by the next addition.
    try:
        rows = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(rows, dict):
            raise ValueError()
        return rows
    except (ValueError, OSError) as error:
        raise Failure('VALIDATION_ERROR', 'تعذّر قراءة مكتبة المهارات. أعد المحاولة دون استبدال ملفاتها.') from error


def write(store, rows):
    root = store.path.parent / 'instructions'
    root.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=root, prefix='.skills-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(rows, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, root / 'custom-skills.json')
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def add(store, payload):
    from .writing_skills import GUIDES
    identifier = payload.get('id', '')
    title, description, content = (payload.get(key, '') for key in ('title', 'description', 'content'))
    if not isinstance(identifier, str) or not re.fullmatch(r'[a-z][a-z0-9-]{1,39}', identifier):
        raise Failure('VALIDATION_ERROR', 'اختر أمرًا من حرفين إلى 40 حرفًا إنجليزيًا، مع أرقام أو شرطات فقط.')
    for value, limit in ((title, 100), (description, 300), (content, LIMIT)):
        if not isinstance(value, str) or not value.strip() or len(value) > limit or '\x00' in value:
            raise Failure('VALIDATION_ERROR', 'أضف اسمًا ووصفًا وتعليمات ضمن الحد المعروض.')
    if payload.get('source_url'):
        from .skill_discovery import source_parts
        source_parts(payload['source_url'])
    rows = read(store)
    if identifier in GUIDES or identifier in rows:
        raise Failure('VALIDATION_ERROR', 'هذا الأمر مستخدم. اختر اسم أمر مختلفًا.')
    if len(rows) >= 100:
        raise Failure('VALIDATION_ERROR', 'وصلت المكتبة إلى حد 100 مهارة مضافة.')
    rows[identifier] = {'id': identifier, 'title': title.strip(), 'description': description.strip(),
                        'content': content.strip(), 'default_content': content.strip()}
    for key in ('source_url', 'source_sha', 'repository', 'license'):
        value = payload.get(key, '')
        if isinstance(value, str) and len(value) <= (2000 if key == 'source_url' else 100):
            rows[identifier][key] = value
    write(store, rows)
    return {'id': identifier}


def instructions(store, identifier, command, payload):
    rows = read(store)
    if identifier not in rows:
        raise Failure('VALIDATION_ERROR', 'المهارة غير موجودة في مكتبتك.')
    row = rows[identifier]
    if command in {'instructions.save', 'instructions.reset'}:
        content = row['default_content'] if command == 'instructions.reset' else payload.get('content')
        if not isinstance(content, str) or not content.strip() or len(content) > LIMIT or '\x00' in content:
            raise Failure('VALIDATION_ERROR', 'أضف تعليمات ضمن الحد المعروض.')
        row['content'] = content
        write(store, rows)
    return {'id': 'skill:' + identifier, 'content': row['content'], 'default_content': row['default_content'], 'limit': LIMIT}


def remove(store, identifier):
    rows = read(store)
    if not isinstance(identifier, str) or identifier not in rows:
        raise Failure('VALIDATION_ERROR', 'لا يمكن حذف هذه المهارة.')
    del rows[identifier]
    write(store, rows)
    return {'removed': identifier}
