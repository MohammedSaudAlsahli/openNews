"""Actual Agno/OpenAI-compatible HTTP contract, synthetic model, isolated workspace.
No live provider, paid request, or personal content. Optional bundled .app argument.
"""
import asyncio
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine'))
from eis_engine.storage import Store,now,uid

calls=[]
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def answer(self,data):
        raw=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(200); self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self): self.answer({'object':'list','data':[{'id':'local-editorial-test','object':'model'}]})
    def do_POST(self):
        request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        context=json.loads(request['messages'][-1]['content'])
        calls.append(context)
        aid=context['news'][0]['id']
        fmt={'x_posts':'x_post','youtube_long':'youtube_long','tiktok':'tiktok'}.get(context['format'])
        result={'message':'هذه صياغة اختبارية تستند إلى الخبر المحدد.','article_ids':[aid],'drafts':([{'title':'مسودة اختبار '+fmt,'text':'خبر تجريبي لا يمثل واقعة حقيقية. هذه صياغة خاصة باختبار الربط المحلي.','format':fmt,'article_ids':[aid]}] if fmt else [])}
        if request.get('stream'):
            self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.end_headers()
            content=json.dumps(result,ensure_ascii=False)
            for offset in range(0,len(content),12):
                chunk={'id':'test-completion','object':'chat.completion.chunk','created':int(time.time()),'model':'local-editorial-test','choices':[{'index':0,'delta':{'content':content[offset:offset+12]},'finish_reason':None}]}
                self.wfile.write(('data: '+json.dumps(chunk,ensure_ascii=False)+'\n\n').encode()); self.wfile.flush(); time.sleep(.01)
            self.wfile.write(b'data: [DONE]\n\n'); self.wfile.flush()
        else:
            self.answer({'id':'test-completion','object':'chat.completion','created':int(time.time()),'model':'local-editorial-test','choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(result,ensure_ascii=False)},'finish_reason':'stop'}],'usage':{'prompt_tokens':10,'completion_tokens':10,'total_tokens':20}})
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
with tempfile.TemporaryDirectory(prefix='eis-chat-smoke-') as temporary:
    directory=Path(temporary).resolve(); workspace=directory/'workspace';sock=directory/'e.sock'
    store=Store(workspace); subscription,article=uid(),uid()
    with store.db:
        store.db.execute('INSERT INTO news_subscriptions(id,workspace_id,title,url,feed_url,kind,enabled,created_at) VALUES(?,?,?,?,?,?,0,?)',(subscription,store.workspace,'Synthetic','https://example.org/feed','https://example.org/feed','rss',now()))
        store.db.execute('INSERT INTO news_articles(id,workspace_id,subscription_id,guid,title,url,published_at,discovered_at,summary,text,body_status) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(article,store.workspace,subscription,article,'خبر اختبار محلي','https://example.org/story',now(),now(),'ملخص تجريبي','هذا نص خبر اصطناعي لا يستخدم بيانات المستخدم.','full'))
    store.close()
    resources=Path(sys.argv[1])/'Contents/Resources' if len(sys.argv)>1 else None
    python=resources/'python/bin/python3.12' if resources else ROOT/'engine/.venv/bin/python'
    entry=resources/'engine/bootstrap.py' if resources else ROOT/'engine/bootstrap.py'
    child=subprocess.Popen([str(python),'-I','-B',str(entry),'--workspace',str(workspace),'--socket',str(sock)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,env={'PATH':'/usr/bin:/bin','HOME':str(directory),'AGNO_TELEMETRY':'false'})
    def call(command,payload=None):
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
            connection.settimeout(30);connection.connect(str(sock))
            connection.sendall(json.dumps({'schema_version':1,'request_id':uid(),'command':command,'payload':payload or {}}).encode()+b'\n')
            raw=b''
            while not raw.endswith(b'\n'):
                piece=connection.recv(65536)
                if not piece:raise RuntimeError('closed socket')
                raw+=piece
        answer=json.loads(raw)
        assert 'error' not in answer,answer
        return answer['result']
    try:
        started = time.monotonic()
        for _ in range(600):
            if sock.exists():break
            if child.poll() is not None:raise RuntimeError(child.stderr.read().decode())
            time.sleep(.05)
        if not sock.exists(): raise RuntimeError('Engine did not become ready within the app startup limit of 30 seconds')
        startup_seconds = round(time.monotonic()-started,3)
        profile=call('providers.save',{'provider_key':'lmstudio','label':'Isolated mock','config':{'base_url':f'http://127.0.0.1:{server.server_port}/v1'}})['profile_id']
        keys=workspace/'.providers';keys.mkdir(mode=0o700);credential=keys/(profile+'.json');credential.write_text('{}');credential.chmod(0o600)
        catalog=call('providers.models',{'profile_id':profile,'refresh':True})
        assert catalog['models'] and catalog['models'][0]['id']=='local-editorial-test',catalog
        source=call('sources.add',{'title':'أسلوب اختباري','text':'هذه كتابتي التجريبية المخصصة للاختبار.','rights_status':'owned','purpose':'style'})
        conversation=call('chat.create',{})['conversation_id']
        previews=[]
        call('assistant.save',{'scope':'general','settings':{'style':'Brief and clear'}})
        for fmt in ['discussion','x_posts','youtube_long','tiktok']:
            job=call('chat.send',{'conversation_id':conversation,'message':'طلب اختباري '+fmt,'profile_id':profile,'model_id':'local-editorial-test','consent':True,'idempotency_key':uid(),'article_ids':[article],'format':fmt,'target_seconds':600 if fmt=='youtube_long' else 60})['job_id']
            for _ in range(300):
                progress=call('chat.progress',{'job_id':job})
                if progress['message']: previews.append(progress['message'])
                state=call('jobs.get',{'job_id':job})
                if state['state'] not in {'queued','running'}:break
                time.sleep(.05)
            assert state['state']=='completed',state
        detail=call('chat.detail',{'conversation_id':conversation})
        assert previews, 'No incremental preview observed over IPC'
        assert len(detail['messages'])==8
        assert len(call('workspace.snapshot')['drafts'])==3
        assert len(calls)==4 and all(c['style_samples'][0]['id']==source['item_id'] for c in calls)
        assert all(c['news'][0]['id']==article for c in calls)
        assert all(c['style_samples'][0]['text'] not in c['news'][0]['text'] for c in calls)
        output=detail['messages'][-1]['outputs'][0]['draft_id']
        exported=call('drafts.export',{'draft_id':output})['text']
        assert 'https://example.org/story' in exported
        print(json.dumps({'result':'passed','actual_agno_calls_to_mock':len(calls),'formats':['discussion','x_posts','youtube_long','tiktok'],'stream_previews':len(previews),'persistent_messages':8,'separate_drafts':3,'style_and_news_isolated':True,'export_has_source':True,'bundled':resources is not None,'startup_seconds':startup_seconds}))
    finally:
        child.terminate()
        try:child.wait(timeout=10)
        except subprocess.TimeoutExpired:child.kill();child.wait()
        server.shutdown()
