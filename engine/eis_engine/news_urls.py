"""Shared limits and public URL validation for news ingestion."""
import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit

MAX_BYTES = 4 * 1024 * 1024
MAX_TEXT = 120_000


class NewsError(Exception):
    pass


def public_ip(value):
    address = ipaddress.ip_address(value)
    if not address.is_global or address.is_multicast or address.is_reserved or address.is_unspecified:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped and not public_ip(str(address.ipv4_mapped)): return False
        if address.sixtofour and not public_ip(str(address.sixtofour)): return False
        if address.teredo and not all(public_ip(str(x)) for x in address.teredo): return False
    return True


def canonical_url(value):
    if not isinstance(value, str) or len(value) > 2048 or re.search(r"[\x00-\x20\x7f]", value):
        raise NewsError("أدخل رابط HTTP أو HTTPS عامًا وصحيحًا.")
    try:
        p = urlsplit(value)
        host = (p.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
        port = p.port
        if p.scheme not in {"http", "https"} or not host or p.username is not None or p.password is not None:
            raise ValueError()
        if port not in {None, 80 if p.scheme == "http" else 443}: raise ValueError()
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")) or "%" in host:
            raise ValueError()
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if not re.fullmatch(r"[a-z0-9.-]+", host) or "." not in host: raise ValueError()
        else:
            if not public_ip(str(address)): raise ValueError()
        netloc = f"[{host}]" if ":" in host else host
        return urlunsplit((p.scheme, netloc, p.path or "/", p.query, ""))
    except (ValueError, UnicodeError):
        raise NewsError("الرابط يجب أن يكون عامًا، دون بيانات دخول أو منفذ خاص.") from None
