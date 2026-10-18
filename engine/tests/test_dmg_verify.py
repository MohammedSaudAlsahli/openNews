import importlib.util
from pathlib import Path
import subprocess
import pytest

spec=importlib.util.spec_from_file_location('dmg_verify',Path(__file__).parents[2]/'scripts/dmg_verify.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_transient_verify_retries_but_corruption_never_does():
    calls=[];waits=[]
    def run(args,**kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args,1 if len(calls)==1 else 0,'','Resource temporarily unavailable' if len(calls)==1 else '')
    m.verify('image.dmg',run,waits.append)
    assert len(calls)==2 and waits==[2]
    calls.clear()
    def corrupt(args,**kwargs):
        calls.append(args);return subprocess.CompletedProcess(args,1,'','checksum INVALID')
    with pytest.raises(subprocess.CalledProcessError):m.verify('image.dmg',corrupt,waits.append)
    assert len(calls)==1
