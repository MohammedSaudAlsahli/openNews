"""Conservative storage and memory preflight, not a promise of inference speed."""
import os
import platform
import shutil
import subprocess

GB=10**9
RESERVE=2*GB

def physical_memory():
    if platform.system()=='Darwin':
        return int(subprocess.check_output(['/usr/sbin/sysctl','-n','hw.memsize'],timeout=2))
    return os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_PHYS_PAGES')

def capacity(path, size, runtime_size=0, installed=False):
    path.mkdir(parents=True,exist_ok=True)
    free=shutil.disk_usage(path).free
    ram=physical_memory()
    needed=(0 if installed else size)+runtime_size*3+RESERVE
    # Allow room for the OS, prompt/cache and inference buffers. Actual loading is tested after download.
    memory=int(size*1.25)+GB
    state='disk' if free<needed else 'memory' if memory>ram*0.8 else 'fits'
    return {'free_disk':free,'required_disk':needed,'memory':ram,'estimated_memory':memory,'fit':state,
            'can_download':state=='fits'}
