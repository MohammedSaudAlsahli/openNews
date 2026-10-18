"""Verify DMGs; retry only macOS transient resource errors, never corruption."""
import subprocess
import sys
import time


def verify(path, run=subprocess.run, sleep=time.sleep):
    for attempt in range(3):
        result = run(['hdiutil','verify',str(path)],capture_output=True,text=True)
        print(result.stdout, end='')
        print(result.stderr, end='', file=sys.stderr)
        if result.returncode == 0: return
        if 'Resource temporarily unavailable' not in result.stderr or attempt == 2:
            raise subprocess.CalledProcessError(result.returncode,result.args,output=result.stdout,stderr=result.stderr)
        sleep(2 ** (attempt + 1))


if __name__ == '__main__': verify(sys.argv[1])
