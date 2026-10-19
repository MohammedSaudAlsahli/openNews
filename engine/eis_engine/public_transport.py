"""Bounded macOS system HTTP transport with a DNS-pinned destination.

Use the platform HTTP client consistently for public feeds, pages and images.
Redirects remain with the caller, where every hop is validated again. No cookies,
proxy configuration, credentials, curl config, or remote commands are accepted.
"""
import io
import subprocess
from email.parser import BytesParser
from .news_urls import MAX_BYTES, NewsError

class PublicResponse:
    def __init__(self, data):
        head, separator, body = data.partition(b'\r\n\r\n')
        if not separator or len(head) > 65536 or len(body) > MAX_BYTES:
            raise NewsError('Public response exceeds the permitted size.')
        try: self.status = int(head.split(b'\r\n', 1)[0].split()[1])
        except (IndexError, ValueError): raise NewsError('Invalid HTTP response.') from None
        self.headers = list(BytesParser().parsebytes(head.split(b'\r\n',1)[1]).items())
        self.body = io.BytesIO(body)
    def getheaders(self): return self.headers
    def read1(self, size): return self.body.read(size)


def start(host, port, address, secure, path, headers, timeout):
    ip = '[' + address + ']' if ':' in address else address
    authority = '[' + host + ']' if ':' in host else host
    url = ('https' if secure else 'http') + '://' + authority + ':' + str(port) + path
    args = ['/usr/bin/curl', '--disable', '--silent', '--show-error', '--globoff',
            '--noproxy', '*', '--proto', '=http,https', '--max-time', str(max(1,timeout)),
            '--connect-timeout', str(max(1,min(timeout,12))), '--max-filesize', str(MAX_BYTES),
            '--resolve', f'{host}:{port}:{ip}', '--include']
    for key, value in headers.items(): args += ['--header', key + ': ' + value]
    # No --location: a redirect is a response and must return to URL/DNS validation.
    return subprocess.Popen(args + ['--url', url], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL, env={'PATH':'/usr/bin:/bin'})


def response(process):
    try:
        data = process.stdout.read(MAX_BYTES + 65537)
        if len(data) > MAX_BYTES + 65536:
            raise NewsError('Public response exceeds the permitted size.')
        result = process.wait(timeout=2)
        if result: raise NewsError('The public source could not be retrieved within its size or time limit.')
        return PublicResponse(data)
    finally:
        if process.poll() is None: process.kill()
        process.wait()
        process.stdout.close()
