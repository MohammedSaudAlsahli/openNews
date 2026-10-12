"""Editable, local YAML feed suggestions. Reading this file never subscribes or fetches."""
from datetime import date
import os
from pathlib import Path
import re
import stat
import yaml
from .contracts import Failure
from .news import canonical_url, NewsError

MAX_BYTES = 1024 * 1024
SEED_PATH = Path(__file__).with_name("feed_library.yml")


class UniqueSafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in mapping:
                raise yaml.constructor.ConstructorError(None, None, "duplicate or non-string key", key_node.start_mark)
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def invalid(message):
    raise Failure("VALIDATION_ERROR", "ملف sources.yml: " + message)


def field(row, key, maximum, required=True, default=""):
    value = row.get(key, default)
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        invalid(f"الحقل {key} يجب أن يكون نصًا بطول {'1–' if required else '0–'}{maximum} حرف.")
    return value.strip()


def parse_library(text):
    try:
        # Avoid recursive aliases and alias expansion; this editable list does not need them.
        for token in yaml.scan(text):
            if isinstance(token, yaml.tokens.AliasToken):
                invalid(f"مراجع YAML غير مدعومة؛ السطر {token.start_mark.line + 1}.")
        value = yaml.load(text, Loader=UniqueSafeLoader)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        position = f" في السطر {mark.line + 1}، العمود {mark.column + 1}" if mark else ""
        invalid("صياغة YAML غير صالحة" + position + ". صحّح الملف وأعد التحميل؛ لم يُعدّل الملف.")
    except RecursionError:
        invalid("بنية YAML متداخلة أكثر من اللازم.")
    if not isinstance(value, dict) or type(value.get("version")) is not int or value["version"] != 1:
        invalid("يجب أن يحتوي الملف version: 1 وقائمة feeds.")
    feeds = value.get("feeds")
    if not isinstance(feeds, list) or len(feeds) > 500:
        invalid("يجب أن تكون feeds قائمة لا تتجاوز 500 مصدر.")
    normalized, ids, urls = [], set(), set()
    for index, row in enumerate(feeds, 1):
        if not isinstance(row, dict): invalid(f"المصدر رقم {index} يجب أن يكون مجموعة حقول.")
        identifier = field(row, "id", 100)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", identifier): invalid(f"معرّف المصدر رقم {index} يقبل الحروف الإنجليزية والأرقام و - و _ فقط.")
        if identifier in ids: invalid(f"معرّف مكرر في المصدر رقم {index}.")
        title = field(row, "title", 300)
        category = field(row, "category", 80)
        if category.casefold() == "all": invalid("التصنيف all محجوز للعرض الشامل؛ اختر اسم تصنيف آخر.")
        language = field(row, "language", 35)
        if not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", language): invalid(f"لغة المصدر رقم {index} غير صالحة؛ استخدم مثل ar أو en.")
        url = field(row, "url", 2048)
        publisher = field(row, "publisher_url", 2048, required=False, default=url) or url
        try:
            canonical = canonical_url(url)
            canonical_url(publisher)
        except NewsError:
            invalid(f"رابط المصدر رقم {index} غير صالح؛ استخدم رابط HTTP أو HTTPS عامًا دون بيانات دخول.")
        if canonical in urls: invalid(f"رابط مكرر في المصدر رقم {index}.")
        verified = row.get("verified_at", "")
        if isinstance(verified, date): verified = verified.isoformat()
        if verified:
            if not isinstance(verified, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", verified): invalid(f"تاريخ المصدر رقم {index} يجب أن يكون YYYY-MM-DD أو فارغًا.")
            try: date.fromisoformat(verified)
            except ValueError: invalid(f"تاريخ المصدر رقم {index} غير صالح.")
        elif verified is None: verified = ""
        elif not isinstance(verified,str): invalid(f"تاريخ المصدر رقم {index} يجب أن يكون نصًا أو فارغًا.")
        normalized.append({"id":identifier,"title":title,"url":url,"category":category,"language":language,
                           "description_ar":field(row,"description_ar",2000,False),"description_en":field(row,"description_en",2000,False),
                           "publisher_url":publisher,"verified_at":verified})
        ids.add(identifier); urls.add(canonical)
    return {"version":1,"feeds":normalized}


def ensure_library_file(store):
    path = store.path.parent / "sources.yml"
    # Exclusive creation ensures a user-edited file is never overwritten, even on concurrent reads.
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        pass
    except OSError:
        invalid("تعذّر إنشاء الملف المحلي. راجع صلاحيات مجلد مساحة العمل.")
    else:
        try:
            seed = SEED_PATH.read_bytes()
            if len(seed) > MAX_BYTES: invalid("ملف المصادر المضمّن أكبر من الحد.")
            with os.fdopen(descriptor, "wb") as output:
                descriptor = None
                output.write(seed)
                output.flush()
                os.fsync(output.fileno())
        except Exception:
            if descriptor is not None: os.close(descriptor)
            path.unlink(missing_ok=True)
            raise
    return path


def library_path(store):
    return {"path":str(ensure_library_file(store))}


def library(store):
    path = ensure_library_file(store)
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor,"rb") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                invalid("يجب أن يكون ملفًا عاديًا لا يتجاوز 1 ميغابايت.")
            data = source.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES: invalid("حجم الملف يتجاوز 1 ميغابايت.")
        text = data.decode("utf-8-sig")
    except UnicodeError:
        invalid("ترميز النص غير صالح؛ احفظ الملف بصيغة UTF-8.")
    except OSError:
        invalid("تعذّر قراءة الملف المحلي. الروابط الرمزية غير مدعومة؛ لم يُعدّل الملف.")
    return {**parse_library(text), "path":str(path)}
