import io
import subprocess
import pytest
from eis_engine import public_transport as transport
from eis_engine.news_urls import NewsError, MAX_BYTES

def test_response_separates_headers_body_and_bounds():
    response=transport.PublicResponse(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<p>Article</p>')
    assert response.status==200
    assert dict(response.getheaders())['Content-Type']=='text/html'
    assert response.read1(100)==b'<p>Article</p>'
    with pytest.raises(NewsError): transport.PublicResponse(b'HTTP/1.1 200 OK\r\n\r\n'+b'a'*(MAX_BYTES+1))
    with pytest.raises(NewsError): transport.PublicResponse(b'invalid')

def test_platform_client_pins_dns_without_following_redirects_or_user_config(monkeypatch):
    calls=[]
    monkeypatch.setattr(subprocess,'Popen',lambda args,**kwargs: calls.append((args,kwargs)))
    transport.start('publisher.example',443,'93.184.216.34',True,'/a?x=1',{'Accept':'text/html'},12)
    args, options=calls[0]
    assert args[1]=='--disable'
    assert args[args.index('--resolve')+1]=='publisher.example:443:93.184.216.34'
    assert '--location' not in args
    assert args[args.index('--noproxy')+1]=='*'
    assert args[-1]=='https://publisher.example:443/a?x=1'
    assert options['env']=={'PATH':'/usr/bin:/bin'}

class Process:
    def __init__(self,data,code=0): self.stdout=io.BytesIO(data);self.code=code;self.killed=False
    def wait(self,**kwargs): return self.code
    def poll(self): return self.code
    def kill(self): self.killed=True

def test_failed_download_is_not_accepted_as_complete_article():
    with pytest.raises(NewsError): transport.response(Process(b'HTTP/1.1 200 OK\r\n\r\npartial',28))
