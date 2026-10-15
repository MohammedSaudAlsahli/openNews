"""User-managed Ollama downloads and Agno summaries. No bundled weights or cloud fallback."""
import asyncio
import json
import os
import platform
import hashlib
import re
import shutil
from pathlib import Path

import httpx
from .contracts import Failure

HOST = 'http://127.0.0.1:11435'
CATALOG = [
    {'id':'qwen3.5:2b-q4_K_M', 'name':'Qwen 3.5 2B', 'languages':'multilingual',
     'source':'https://huggingface.co/Qwen/Qwen3.5-2B', 'purpose':'compact'},
    {'id':'gemma4:e2b-it-qat', 'name':'Gemma 4 E2B', 'languages':'multilingual',
     'source':'https://ai.google.dev/gemma/docs/core', 'purpose':'balanced'},
    {'id':'gemma3:4b-it-qat', 'name':'Gemma 3 4B', 'languages':'multilingual',
     'source':'https://ai.google.dev/gemma/docs/core/model_card_3', 'purpose':'balanced'},
]


def model_name(value):
    if not isinstance(value, str) or len(value)>180 or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*(?:/[a-zA-Z0-9][a-zA-Z0-9_.-]*)?(?::[a-zA-Z0-9][a-zA-Z0-9_.-]*)?', value):
        raise Failure('VALIDATION_ERROR', 'أدخل اسم نموذج من مكتبة Ollama، وليس رابطًا.')
    if 'cloud' in value.lower():
        raise Failure('VALIDATION_ERROR', 'اختر نموذجًا محليًا قابلًا للتحميل؛ النماذج السحابية ضمن الاتصالات.')
    return value if ':' in value else value+':latest'


async def registry_size(client, repository, tag):
    """Match Ollama's runner choice; a legacy manifest can undercount Apple MLX downloads."""
    base = 'https://registry.ollama.ai/v2/'+repository
    response = await client.get(base+'/manifests/'+tag, headers={'Accept':
        'application/vnd.ollama.manifest.list.v2+json, application/vnd.docker.distribution.manifest.v2+json'})
    response.raise_for_status()
    manifest = response.json()
    if 'manifests' in manifest:
        preferences = ['mlx','llamacpp','ggml'] if platform.system()=='Darwin' and platform.machine()=='arm64' else ['llamacpp','ggml','mlx']
        child = next((m for runner in preferences for m in manifest['manifests'] if m.get('runner')==runner), None)
        if not child: raise ValueError('No compatible model')
        if child.get('layers'): manifest = child
        else:
            digest = child['digest']
            if not re.fullmatch(r'sha256:[a-f0-9]{64}',digest): raise ValueError('Invalid manifest digest')
            response = await client.get(base+'/blobs/'+digest)
            response.raise_for_status()
            if hashlib.sha256(response.content).hexdigest()!=digest.split(':')[1]: raise ValueError('Manifest checksum mismatch')
            manifest = response.json()
    size = sum(int(x['size']) for x in manifest['layers']) + int(manifest.get('config',{}).get('size',0))
    if size<=0: raise ValueError('Empty model')
    return size


class LocalSummaryModels:
    def __init__(self, service):
        self.service = service
        self.installed = {}
        self.download = {'phase':'idle','model':'','completed':0,'total':0,'error':''}
        self.task = None
        self.checked = {}
        self.runtime = False
        self.capabilities = {}
        from .local_runtime import LocalRuntime
        from .model_library import ModelLibrary
        base = service.store.path.parent if service else Path.home()/'Library/Application Support/OpenStudio'
        self.root = base/'local-summaries'
        self.models_path = self.root/'models'
        self.runner = LocalRuntime(self.root)
        self.library = ModelLibrary()
        self.process = None
        self.start_lock = asyncio.Lock()

    def executable(self):
        return self.runner.executable()

    async def refresh(self):
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=2) as client:
                response = await client.get(HOST+'/api/tags')
                response.raise_for_status()
                self.installed = {x['name']:x.get('size',0) for x in response.json().get('models',[])}
            self.runtime = True
        except (httpx.HTTPError, ValueError, KeyError):
            self.runtime = False
            self.installed = self.saved_models()
        return self.status()

    def saved_models(self):
        # Preserve the Downloaded list while the app-owned runtime is stopped.
        root = self.models_path/'manifests/registry.ollama.ai'
        result = {}
        for manifest in root.glob('*/*/*'):
            try:
                namespace, repository, tag = manifest.relative_to(root).parts
                name = model_name((repository if namespace=='library' else namespace+'/'+repository)+':'+tag)
                data = json.loads(manifest.read_text())
                layers = data['layers']
                for layer in layers:
                    if not re.fullmatch(r'sha256:[a-f0-9]{64}',layer['digest']): raise ValueError('Invalid layer')
                    blob = self.models_path/'blobs'/layer['digest'].replace(':','-')
                    if blob.stat().st_size != layer['size']: raise ValueError('Incomplete layer')
                result[name] = sum(layer['size'] for layer in layers)
            except (OSError, ValueError, KeyError, TypeError, Failure):
                continue
        return result

    def status(self):
        return {'runtime':self.runtime, 'can_start':bool(self.executable()),
                'models':[dict(x, size=self.installed.get(x['id']) or self.checked.get(x['id']),
                               installed=x['id'] in self.installed, quality='untested') for x in CATALOG],
                'installed':[{'id':k,'size':v} for k,v in self.installed.items() if 'cloud' not in k.lower()],
                'download':dict(self.download)}

    async def start_runtime(self):
        async with self.start_lock:
            await self.refresh()
            if self.runtime: return self.status()
            executable = self.executable()
            if not executable: raise Failure('LOCAL_UNAVAILABLE','يحتاج جهازك إلى تجهيز ملفات التشغيل أولًا.')
            self.models_path.mkdir(parents=True,exist_ok=True)
            env = {**os.environ, 'OLLAMA_HOST':'127.0.0.1:11435','OLLAMA_MODELS':str(self.models_path),
                   'OLLAMA_NO_CLOUD':'1','OLLAMA_NUM_PARALLEL':'1','OLLAMA_MAX_LOADED_MODELS':'1'}
            self.process = await asyncio.create_subprocess_exec(executable,'serve',env=env,
                stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
            for _ in range(20):
                await asyncio.sleep(.25)
                await self.refresh()
                if self.runtime: return self.status()
            raise Failure('LOCAL_UNAVAILABLE','تعذّر تجهيز التلخيص على الجهاز. أعد المحاولة.')

    async def close(self):
        await self.cancel()
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try: await asyncio.wait_for(self.process.wait(),3)
            except TimeoutError:
                self.process.kill()
                await self.process.wait()

    def capacity(self, name, runtime_size=0):
        from .model_capacity import capacity
        return capacity(self.models_path,self.checked.get(name,self.installed.get(name,0)),runtime_size,name in self.installed)

    async def inspect(self, name):
        name = model_name(name)
        repository, tag = name.rsplit(':',1)
        if '/' not in repository: repository = 'library/'+repository
        try:
            size = self.installed.get(name)
            if size is None:
                async with httpx.AsyncClient(trust_env=False, timeout=10, follow_redirects=True) as client:
                    size = await registry_size(client, repository, tag)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise Failure('MODEL_UNSUPPORTED', 'تعذّر قراءة حجم النموذج. تحقق من الاسم والاتصال ثم أعد المحاولة.')
        size = self.installed.get(name, size)
        self.checked[name] = size
        needs_upgrade = name.startswith('embeddinggemma-2:') and not await self.runner.compatible((0,40,0))
        runtime_size = await self.runner.metadata(force=True) if needs_upgrade else await self.runner.metadata()
        return {'id':name,'size':size,'runtime_size':runtime_size,**self.capacity(name,runtime_size)}

    async def begin(self, name, language='ar', purpose='summary'):
        name = model_name(name)
        if purpose not in {'summary','embedding'}: raise Failure('VALIDATION_ERROR','Invalid purpose')
        if language not in {'ar','en'}: raise Failure('VALIDATION_ERROR','لغة غير صالحة.')
        if self.task and not self.task.done(): raise Failure('BUSY','يوجد تحميل قيد التنفيذ.')
        self.download = {'phase':'checking','model':name,'completed':0,'total':0,'error':''}
        self.task = asyncio.create_task(self.prepare(name,language,purpose))
        return self.status()

    async def prepare(self, name, language, purpose='summary'):
        try:
            plan = await self.inspect(name)
            if not plan['can_download']:
                raise Failure('CAPACITY', 'المساحة لا تكفي. حرر مساحة أو اختر نموذجًا أصغر.' if plan['fit']=='disk' else 'هذا النموذج أكبر من ذاكرة جهازك المتاحة للتلخيص. اختر إصدارًا أصغر.')
            needs_upgrade = name.startswith('embeddinggemma-2:') and not await self.runner.compatible((0,40,0))
            if needs_upgrade:
                async with self.service.model_lock:
                    if self.process and self.process.returncode is None:
                        self.process.terminate()
                        await asyncio.wait_for(self.process.wait(),5)
                        self.runtime = False
                    await self.runner.install(self.download,force=True)
            elif not self.executable(): await self.runner.install(self.download)
            await self.start_runtime()
            if name not in self.installed:
                self.download.update(phase='downloading',completed=0,total=self.checked[name])
                await self.pull(name)
                if self.download['phase']=='failed': return
            self.download['phase']='testing'
            if purpose == 'embedding':
                await self.prepare_embedding(name)
                self.download['phase']='ready'
                return
            await self.check_generation(name)
            # Verify that this model can actually load and produce the structured summary schema.
            from .article_summary import ArticleSummary
            await self.run(name,'Summarize this short text in one sentence. Do not add facts.',
                {'text':'The library opens at 9 am and closes at 6 pm.'},ArticleSummary)
            self.service.news_digest.configure({'engine':'local','local_model':name,'enabled':True,'language':language})
            self.download['phase']='ready'
        except asyncio.CancelledError:
            self.download['phase']='cancelled'
            raise
        except Failure as error:
            self.download.update(phase='failed',error=str(error))
        except Exception:
            self.download.update(phase='failed',error='تعذّر تجهيز النموذج. جرّب إصدارًا أصغر أو أعد المحاولة.')

    async def available(self, capability):
        if capability not in {'embedding','completion'}: raise Failure('VALIDATION_ERROR','Invalid capability')
        if not self.executable(): return {'installed':[]}
        await self.start_runtime()
        result = []
        async with httpx.AsyncClient(trust_env=False, timeout=5) as client:
            for name,size in self.installed.items():
                response = await client.post(HOST+'/api/show',json={'model':name})
                response.raise_for_status()
                info = response.json()
                if not info.get('remote_host') and not info.get('remote_model') and capability in info.get('capabilities',[]):
                    result.append({'id':name,'size':size,'capabilities':info['capabilities']})
        return {'installed':result}

    async def prepare_embedding(self, name):
        from .news_embeddings import LocalNewsEmbeddings
        async with self.service.model_lock:
            async with httpx.AsyncClient(trust_env=False, timeout=90) as client:
                shown = await client.post(HOST+'/api/show', json={'model':name})
                shown.raise_for_status()
                info = shown.json()
                if info.get('remote_model') or info.get('remote_host') or 'embedding' not in info.get('capabilities',[]):
                    raise Failure('MODEL_UNSUPPORTED','هذا النموذج لا يدعم البحث بالمعنى. اختر نموذج Embedding.')
                tags = await client.get(HOST+'/api/tags'); tags.raise_for_status()
                digest = next(m['digest'] for m in tags.json()['models'] if m['name']==name)
                probe = await client.post(HOST+'/api/embed', json={'model':name,'input':'اختبار البحث / search test',
                    'keep_alive':0,'options':{'num_thread':2}})
                probe.raise_for_status()
                dimensions = len(probe.json()['embeddings'][0])
                if not 1<=dimensions<=8192: raise ValueError('Invalid dimensions')
            encoder = LocalNewsEmbeddings(name=name, dimensions=dimensions, digest=digest)
            await asyncio.to_thread(encoder.encode, ['اختبار البحث / search test'], query=True)
        await self.service.news.knowledge.select_model(name, dimensions, digest)

    async def pull(self, name):
        layers, totals = {}, {}
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(120,connect=5)) as client:
                async with client.stream('POST',HOST+'/api/pull',json={'model':name,'stream':True}) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if shutil.disk_usage(self.models_path).free<2*10**9:
                            raise Failure('DISK_FULL','المساحة المتاحة انخفضت. حرر مساحة ثم أعد المحاولة.')
                        if not line: continue
                        event = json.loads(line)
                        if event.get('error'): raise ValueError(event['error'])
                        if event.get('digest'):
                            totals[event['digest']] = max(totals.get(event['digest'],0),event.get('total',0))
                            self.download['total'] = max(self.download['total'],sum(totals.values()))
                            layers[event['digest']] = max(layers.get(event['digest'],0),min(event.get('completed',0),event.get('total',0)))
                            self.download['completed'] = min(sum(layers.values()),self.download['total'])
                        if event.get('status','').startswith(('verifying','writing manifest')): self.download['phase'] = 'verifying'
                        if event.get('status') == 'success': self.download['phase'] = 'testing'
            await self.refresh()
            if name not in self.installed: raise ValueError('Model not found after download')
            self.download.update(phase='testing',completed=self.download['total'])
        except asyncio.CancelledError:
            self.download['phase'] = 'cancelled'
            raise
        except Failure as error:
            self.download.update(phase='failed',error=str(error))
        except Exception:
            self.download.update(phase='failed',error='تعذّر التحميل. تحقق من اتصال الإنترنت والمساحة المتاحة ثم أعد المحاولة.')

    async def cancel(self):
        if self.task and not self.task.done():
            self.task.cancel()
            await asyncio.gather(self.task,return_exceptions=True)
        return self.status()

    async def check_generation(self, name):
        name = model_name(name)
        await self.refresh()
        if name not in self.installed: raise Failure('MODEL_UNSUPPORTED','هذا النموذج غير جاهز بعد. اختر تحميل واستخدام.')
        async with httpx.AsyncClient(trust_env=False,timeout=5) as client:
            response = await client.post(HOST+'/api/show',json={'model':name})
            response.raise_for_status()
            info = response.json()
        if info.get('remote_model') or info.get('remote_host') or 'completion' not in info.get('capabilities',[]):
            raise Failure('MODEL_UNSUPPORTED','هذا النموذج لا يدعم التلخيص المحلي. اختر نموذج توليد نصوص.')
        self.capabilities[name] = info.get('capabilities',[])
        return name

    async def run(self, name, instructions, data, schema):
        from agno.agent import Agent
        from agno.models.ollama import Ollama
        if not self.runtime: await self.start_runtime()
        await self.check_generation(name)
        if self.capacity(name)['fit']=='memory':
            raise Failure('CAPACITY','هذا النموذج أكبر من ذاكرة جهازك المتاحة للتلخيص. اختر إصدارًا أصغر.')
        async with self.service.model_lock:
            model = Ollama(id=name,host=HOST,api_key=None,timeout=120,keep_alive=0,client_params={'trust_env':False},
                           options={'num_ctx':8192,'num_predict':800,'num_thread':2,'temperature':0.2},
                           request_params={'think':False} if 'thinking' in self.capabilities.get(name,[]) else None)
            agent = Agent(model=model,instructions=instructions,output_schema=schema,markdown=False)
            try:
                result = await asyncio.wait_for(agent.arun(json.dumps({**data, "output_language": "العربية فقط؛ ترجم الملخص ولا تنسخ النص الإنجليزي." if "Arabic." in instructions else "English only."},ensure_ascii=False)),timeout=120)
            finally:
                # Also release weights on cancellation/error; keep_alive covers normal completion.
                try:
                    async with httpx.AsyncClient(trust_env=False,timeout=5) as client:
                        await client.post(HOST+'/api/generate',json={'model':name,'keep_alive':0,'stream':False})
                except httpx.HTTPError:
                    pass
            if isinstance(result.content,schema): return result.content
            if isinstance(result.content,str): return schema.model_validate_json(result.content)
            return schema.model_validate(result.content)
