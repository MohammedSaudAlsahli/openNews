"""Run the actual packaging shell with fake build tools, including macOS Bash 3."""
import os
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]

@pytest.mark.parametrize(('channel', 'expected', 'name'), [
    ('--development', 'build --bundles app --config src-tauri/tauri.dev.conf.json', 'openNews Dev.app'),
    ('--release', 'build --bundles app', 'openNews.app'),
])
def test_packaging_channel_arguments_in_system_bash(tmp_path, channel, expected, name):
    (tmp_path/'scripts').mkdir()
    script=tmp_path/'scripts/build_app.sh'
    script.write_text((ROOT/'scripts/build_app.sh').read_text())
    binary=tmp_path/'bin';binary.mkdir()
    python=tmp_path/'engine/.venv/bin/python';python.parent.mkdir(parents=True)
    python.write_text('#!/bin/bash\nexit 0\n');python.chmod(0o755)
    commands={
        'git': 'echo main',
        'uv': 'exit 0',
        'codesign': 'printf "%s\\n" "$*" >> "$CHANNEL_LOG"',
        'npm': 'if [[ "$*" == *"run tauri"* ]]; then printf "%s\\n" "$*" >> "$CHANNEL_LOG"; fi',
    }
    for tool,body in commands.items():
        p=binary/tool;p.write_text('#!/bin/bash\n'+body+'\n');p.chmod(0o755)
    log=tmp_path/'commands.log'
    env={**os.environ,'PATH':str(binary)+os.pathsep+os.environ['PATH'],'CHANNEL_LOG':str(log),'GITHUB_ACTIONS':'true','GITHUB_REF':'refs/heads/main'}
    subprocess.run(['/bin/bash',str(script),channel],env=env,check=True)
    calls=log.read_text().splitlines()
    assert calls[0] == '--prefix desktop run tauri -- '+expected
    assert all(name in call for call in calls[1:])
