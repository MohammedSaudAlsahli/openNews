"""Read real public skill sources and exercise import in the isolated native QA workspace."""
import argparse,json,re,socket,subprocess,uuid,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True);args=p.parse_args()
expected=Path.home()/'Library/Application Support/com.opennews.ui-qa/default'
engine_socket=None
for pid in subprocess.check_output(['pgrep','-P',str(args.pid)],text=True).split():
    command=subprocess.check_output(['ps','-ww','-p',pid,'-o','command='],text=True)
    match=re.search(r' --workspace (.+) --socket (\S+)\s*$',command)
    if match:
        assert Path(match[1])==expected,'Refusing a non-QA workspace'
        engine_socket=match[2]
assert engine_socket

def call(command,payload=None):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as stream:
        stream.settimeout(70);stream.connect(engine_socket)
        stream.sendall((json.dumps({'schema_version':1,'request_id':str(uuid.uuid4()),'command':command,'payload':payload or {}})+'\n').encode())
        response=json.loads(stream.makefile('rb').readline());assert response['event']!='failed',response.get('error');return response['result']
started=time.perf_counter()
results=call('skills.search',{'query':'article writing'});assert results['skills'] and results['source']=='skills.sh'
preview=call('skills.preview',{'url':'https://github.com/affaan-m/everything-claude-code/blob/main/skills/article-writing/SKILL.md'})
assert preview['kind']=='skill' and len(preview['source_sha'])==40 and preview['content'].strip()
identifier='native-import-'+uuid.uuid4().hex[:8]
try:
    call('skills.add',{**preview,'id':identifier})
    row=next(row for row in call('skills.catalog')['skills'] if row['id']==identifier)
    assert row['source_url']==preview['source_url'] and row['origin']=='custom'
    assert call('instructions.get',{'id':'skill:'+identifier})['content']==preview['content']
finally:
    call('skills.remove',{'id':identifier})
assert all(row['id']!=identifier for row in call('skills.catalog')['skills'])
print(json.dumps({'workspace':'isolated native QA','checks':['live skills.sh search','live pinned GitHub preview','add with source provenance','read actual instructions','remove and verify'],'directory_results':len(results['skills']),'source_url':preview['source_url'],'source_sha':preview['source_sha'],'characters':len(preview['content']),'seconds':round(time.perf_counter()-started,2)},indent=2))
