"""Run the relocated, signed bundle interpreter with no developer PATH/PYTHONPATH."""
import json
import os
from pathlib import Path
import plistlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

app=Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='eis-smoke-') as temporary:
    directory=Path(temporary)
    # Relocation ensures the embedded runtime does not depend on the original bundle path.
    relocated=directory/'Relocated.app'
    shutil.copytree(app,relocated,symlinks=True)
    resources=relocated/'Contents/Resources'
    info=plistlib.loads((relocated/'Contents/Info.plist').read_bytes())
    assert info['CFBundleExecutable']=='OpenStudio'
    assert info['CFBundleDisplayName']=='OpenStudio'
    assert info['CFBundleIconFile']=='OpenStudio.icns'
    assert (resources/info['CFBundleIconFile']).read_bytes()[:4]==b'icns'
    for name in ('OpenStudioMenuBar.png', 'OpenStudioMenuBar@2x.png'):
        assert list((resources/'OpenStudio_OpenStudioApp.bundle').rglob(name)), name
    sock=directory/'e.sock'
    env={'PATH':'/usr/bin:/bin','HOME':str(directory),'AGNO_TELEMETRY':'false'}
    child=subprocess.Popen([str(resources/'python/bin/python3.12'),'-I','-B',str(resources/'engine/bootstrap.py'),'--workspace',str(directory/'workspace'),'--socket',str(sock)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    def request(command,payload=None):
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
            connection.settimeout(10)
            connection.connect(str(sock))
            connection.sendall(json.dumps({'schema_version':1,'request_id':str(uuid4()),'command':command,'payload':payload or {}}).encode()+b'\n')
            result=b''
            while not result.endswith(b'\n'):
                result+=connection.recv(65536)
        response=json.loads(result)
        assert response['event']!='failed',response
        return response['result']
    try:
        for _ in range(600):
            if sock.exists(): break
            if child.poll() is not None: raise RuntimeError(child.stderr.read().decode())
            time.sleep(.05)
        if not sock.exists(): raise RuntimeError('Bundled engine socket did not appear within 30 seconds')
        health=request('runtime.health')
        assert health['sqlite_vec']
        library=request('news.library')
        assert len(library['feeds']) == 12
        for language in ('ar','en'):
            localized=resources/'OpenStudio_OpenStudioApp.bundle'/f'{language}.json'
            if not localized.exists():
                localized=localized.parent/'Contents/Resources'/f'{language}.json'
            assert localized.exists(), localized
            assert json.loads(localized.read_text()), language
        imported=request('sources.add',{'title':'اختبار حزمة مستقل','text':'كيف تكتب بوضوح؟\n\nاختر فكرة واحدة.','rights_status':'owned'})
        job=request('analysis.run',{'item_ids':[imported['item_id']],'idempotency_key':str(uuid4())})
        for _ in range(50):
            status=request('jobs.get',{'job_id':job['job_id']})
            if status['state'] in {'completed','failed'}: break
            time.sleep(.1)
        assert status['state']=='completed',status
        state=request('workspace.snapshot')
        assert len(state['techniques'])==1 and not state['rules']
        request('dna.approve',{'technique_id':state['techniques'][0]['id']})
        assert len(request('workspace.snapshot')['rules'])==1
        providers=request('providers.catalog')
        print(json.dumps({'result':'passed','runtime':health,'provider_count':len(providers['providers']),'scope':'relocated bundled Python, SQLite/vec, socket, import-analysis-evidence-DNA; same host'},ensure_ascii=False))
    finally:
        child.terminate()
        try: child.wait(timeout=10)
        except subprocess.TimeoutExpired: child.kill(); child.wait()
    assert not sock.exists(),'Engine failed to remove socket on shutdown'
