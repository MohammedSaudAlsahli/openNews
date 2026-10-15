"""On-demand official runtime, checksum verified, installed only in app-owned storage."""
import asyncio
import hashlib
import os
import re
from pathlib import Path
import shutil
import tarfile
import httpx
from .contracts import Failure

class LocalRuntime:
    def __init__(self, root):
        self.root=Path(root)
        self.asset=None

    def executable(self):
        managed=self.root/'runtime'
        for relative in ['bin/ollama','ollama']:
            candidate=managed/relative
            if candidate.is_file(): return str(candidate)
        return next((p for p in ['/opt/homebrew/bin/ollama','/usr/local/bin/ollama','/Applications/Ollama.app/Contents/Resources/ollama'] if Path(p).is_file()),None)

    async def compatible(self, minimum):
        executable = self.executable()
        if not executable: return False
        try:
            process = await asyncio.create_subprocess_exec(executable,'--version',stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT)
            try: output,_ = await asyncio.wait_for(process.communicate(),5)
            except TimeoutError:
                process.kill(); await process.wait(); return False
            versions = re.findall(r'(\d+)\.(\d+)\.(\d+)',output.decode())
            return bool(versions) and tuple(map(int,versions[-1])) >= minimum
        except OSError: return False

    async def metadata(self, force=False):
        if self.executable() and not force: return 0
        if not self.asset:
            async with httpx.AsyncClient(trust_env=False,timeout=6) as client:
                r=await client.get('https://api.github.com/repos/ollama/ollama/releases/latest')
                r.raise_for_status()
                self.asset=next(x for x in r.json()['assets'] if x['name']=='ollama-darwin.tgz')
            if not self.asset.get('digest','').startswith('sha256:') or not self.asset['browser_download_url'].startswith('https://github.com/ollama/ollama/releases/download/'):
                raise Failure('RUNTIME_UNAVAILABLE','تعذّر التحقق من ملفات التشغيل. أعد المحاولة لاحقًا.')
        return self.asset['size']

    async def install(self, progress, force=False):
        if self.executable() and not force: return self.executable()
        await self.metadata(force=force)
        self.root.mkdir(parents=True,exist_ok=True)
        archive=self.root/'runtime-download.tgz'
        staging=self.root/'runtime-unpacking'
        sha=hashlib.sha256()
        progress.update(phase='preparing',completed=0,total=self.asset['size'])
        try:
            async with httpx.AsyncClient(trust_env=False,timeout=60,follow_redirects=True) as client:
                async with client.stream('GET',self.asset['browser_download_url']) as response:
                    response.raise_for_status()
                    with archive.open('wb') as target:
                        async for chunk in response.aiter_bytes(1024*1024):
                            if shutil.disk_usage(self.root).free<2*10**9: raise Failure('DISK_FULL','المساحة المتاحة انخفضت. حرر مساحة ثم أعد المحاولة.')
                            target.write(chunk);sha.update(chunk);progress['completed']+=len(chunk)
                            if progress['completed']>self.asset['size']: raise ValueError('Unexpected runtime size')
            if sha.hexdigest()!=self.asset['digest'].split(':')[1]: raise ValueError('Runtime checksum mismatch')
            if staging.exists(): shutil.rmtree(staging)
            staging.mkdir()
            # Python's data filter rejects traversal and unsafe links/devices.
            with tarfile.open(archive) as contents:
                if sum(x.size for x in contents.getmembers())>2*10**9: raise ValueError('Runtime expansion limit')
                contents.extractall(staging,filter='data')
            executable=next((staging/x for x in ['bin/ollama','ollama'] if (staging/x).is_file()),None)
            if not executable: raise ValueError('Missing executable')
            executable.chmod(executable.stat().st_mode | 0o700)
            destination = self.root/'runtime'
            previous = self.root/'runtime-previous'
            if previous.exists(): shutil.rmtree(previous)
            if destination.exists(): destination.rename(previous)
            try: staging.rename(destination)
            except BaseException:
                if previous.exists(): previous.rename(destination)
                raise
            if previous.exists(): shutil.rmtree(previous)
            return self.executable()
        finally:
            archive.unlink(missing_ok=True)
            if staging.exists(): shutil.rmtree(staging)
