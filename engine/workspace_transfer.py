"""Offline, reversible transfer between the native and Tauri workspaces.

Called only by the desktop shell after stopping its own engine. Never moves or
modifies the source database. Refuse transfer while the source engine is running.
"""
import fcntl
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import uuid


def validate(root):
    if root.is_symlink() or any(p.is_symlink() for p in root.parents):
        raise ValueError('Workspace must not be a symbolic link.')
    for path in root.rglob('*'):
        if path.is_symlink():
            try: path.resolve().relative_to(root.resolve())
            except ValueError: raise ValueError('Workspace contains a link outside its folder.') from None


def transfer(source, destination):
    source, destination = Path(source).absolute(), Path(destination).absolute()
    if source == destination or not (source/'editorial.sqlite').is_file():
        raise ValueError('The original workspace was not found.')
    validate(source)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists(): validate(destination)
    # Opening without truncation preserves the original lock file contents.
    with (source/'engine.lock').open('a') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError('Quit the original OpenStudio app before importing.') from None
        staging = Path(tempfile.mkdtemp(prefix='.import-',dir=destination.parent))
        backup = destination.parent/'backups'/('before-import-'+uuid.uuid4().hex)
        try:
            # APFS copy-on-write preserves large model/cache files without downloading again.
            if sys.platform == 'darwin':
                subprocess.run(['/bin/cp','-cR',str(source)+ '/.',str(staging)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            else: shutil.copytree(source,staging,dirs_exist_ok=True,symlinks=True)
            # Absolute links inside the source must not keep pointing to live source files.
            for link in staging.rglob('*'):
                if link.is_symlink():
                    original = source / link.relative_to(staging)
                    relative_target = original.resolve().relative_to(source.resolve())
                    link.unlink()
                    link.symlink_to(os.path.relpath(staging/relative_target, link.parent))
            os.chmod(staging,0o700)
            # Copying is performed while the source engine lock is held; verify the result.
            db=sqlite3.connect(staging/'editorial.sqlite')
            try:
                if db.execute('PRAGMA quick_check').fetchone()[0]!='ok': raise ValueError('Database integrity verification failed.')
                if db.execute('PRAGMA foreign_key_check').fetchone(): raise ValueError('Database relationship verification failed.')
                counts={name:db.execute('SELECT count(*) FROM '+name).fetchone()[0] for name in ('news_articles','conversations','provider_profiles','drafts')}
            finally: db.close()
            # User opt-ins are preserved, but the import itself must not send model requests.
            # Background generation resumes only when the user explicitly enables it again.
            db=sqlite3.connect(staging/'editorial.sqlite')
            try:
                for table in ('news_digest_settings','news_search_settings','daily_report_settings'):
                    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone(): db.execute('UPDATE '+table+' SET enabled=0')
                db.commit()
            finally: db.close()
            if destination.exists():
                backup.parent.mkdir(parents=True,exist_ok=True)
                destination.rename(backup)
            try: staging.rename(destination)
            except BaseException:
                if backup.exists(): backup.rename(destination)
                raise
            result={'imported':True,'counts':counts,'backup':str(backup) if backup.exists() else None}
            (destination.parent/'last-import.json').write_text(json.dumps(result))
            return result
        finally:
            if staging.exists(): shutil.rmtree(staging)

def restore(destination):
    destination=Path(destination).absolute()
    manifest=destination.parent/'last-import.json'
    record=json.loads(manifest.read_text())
    backup=Path(record['backup'])
    if backup.parent.resolve() != (destination.parent/'backups').resolve() or not backup.is_dir():
        raise ValueError('The saved workspace backup was not found.')
    validate(backup); validate(destination)
    current=backup.parent/('before-restore-'+uuid.uuid4().hex)
    destination.rename(current)
    try: backup.rename(destination)
    except BaseException:
        current.rename(destination)
        raise
    result={'restored':True,'backup':str(current)}
    manifest.write_text(json.dumps(result))
    return result

if __name__=='__main__':
    try: print(json.dumps(restore(sys.argv[2]) if sys.argv[1]=='--restore' else transfer(sys.argv[1],sys.argv[2])))
    except Exception as error:
        # No source content or credentials in error output.
        print(json.dumps({'error':str(error) if isinstance(error,ValueError) else 'Workspace import failed. Your original data is unchanged.'}))
        sys.exit(1)
