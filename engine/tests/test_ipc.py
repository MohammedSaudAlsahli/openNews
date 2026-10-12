import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from uuid import uuid4
import pytest


@pytest.fixture
def engine():
    with tempfile.TemporaryDirectory(prefix='eis-ipc-',dir='/tmp') as temporary:
        root=Path(temporary)
        sock=root/'e.sock'
        process=subprocess.Popen([sys.executable,'-m','eis_engine','--workspace',str(root/'workspace'),'--socket',str(sock)],
                                 env={'PATH':'/usr/bin:/bin','PYTHONPATH':str(Path(__file__).parents[1]),'HOME':temporary},
                                 stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                if sock.exists(): break
                assert process.poll() is None
                time.sleep(.05)
            assert sock.exists()
            yield root,sock,process
        finally:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait()


def send(sock,message):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.settimeout(5)
        client.connect(str(sock))
        client.sendall(message)
        response=b''
        while not response.endswith(b'\n'):
            part=client.recv(65536)
            if not part: break
            response+=part
    return json.loads(response)


def request(command,payload=None):
    return json.dumps({'schema_version':1,'request_id':str(uuid4()),'command':command,'payload':payload or {}}).encode()+b'\n'


def test_real_socket_health_mode_and_shutdown(engine):
    root,sock,process=engine
    result=send(sock,request('runtime.health'))
    assert result['result']['sqlite_vec']
    assert sock.stat().st_mode & 0o777 == 0o600
    assert (root/'workspace').stat().st_mode & 0o777 == 0o700
    process.terminate(); process.wait(timeout=5)
    assert not sock.exists()


@pytest.mark.parametrize('message',[b'not json\n',b'{}\n',json.dumps({'schema_version':2,'request_id':str(uuid4()),'command':'runtime.health'}).encode()+b'\n',b'x'*(1024*1024+20)+b'\n'])
def test_bad_frames_do_not_crash_engine(engine,message):
    _,sock,process=engine
    result=send(sock,message)
    assert result['error']['code']=='VALIDATION_ERROR'
    assert process.poll() is None
    assert send(sock,request('runtime.health'))['event']=='completed'


def test_unknown_commands_and_extra_secret_fields_rejected(engine):
    _,sock,_=engine
    assert send(sock,request('shell.execute',{'command':'env'}))['error']['code']=='MODEL_UNSUPPORTED'
    result=send(sock,request('providers.save',{'provider_key':'openai','model_id':'test','api_key':'synthetic-secret'}))
    assert result['error']['code']=='VALIDATION_ERROR'
    assert 'synthetic-secret' not in json.dumps(result)


def test_duplicate_engine_cannot_mutate_active_workspace(engine):
    root,sock,process=engine
    second=subprocess.run([sys.executable,'-m','eis_engine','--workspace',str(root/'workspace'),'--socket',str(sock)],
                          env={'PATH':'/usr/bin:/bin','PYTHONPATH':str(Path(__file__).parents[1])},capture_output=True,timeout=5)
    assert second.returncode==3
    assert process.poll() is None
    assert send(sock,request('runtime.health'))['event']=='completed'
