import argparse
import asyncio
import fcntl
import json
import logging
import os
from pathlib import Path
import signal
import socket
import sys
from pydantic import ValidationError
from .contracts import Failure, Request
from .service import Service
from .storage import Store

MAX_FRAME = 1024 * 1024


async def serve(directory, socket_path):
    os.umask(0o077)
    directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    # Do not let a second process reclassify live jobs or unlink an active socket.
    lock = (directory / "engine.lock").open("w")
    try:
        fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(3)
    if socket_path.exists():
        socket_path.unlink()
    service = Service(Store(directory))
    service.catalog_task = asyncio.create_task(service.refresh_catalogs())
    service.news_task = asyncio.create_task(service.news.poll())
    service.digest_task = asyncio.create_task(service.news_digest.poll())
    service.knowledge_task = asyncio.create_task(service.news.knowledge.poll())
    stop = asyncio.Event()

    async def connected(reader,writer):
        request_id = None
        try:
            raw = await asyncio.wait_for(reader.readline(),timeout=10)
            if not raw or len(raw)>MAX_FRAME or not raw.endswith(b"\n"):
                raise Failure("VALIDATION_ERROR","حجم الرسالة غير صالح.")
            request = Request.model_validate_json(raw)
            request_id = str(request.request_id)
            result = await service.dispatch(request.command,request.payload)
            answer = {"schema_version":1,"request_id":request_id,"event":"accepted" if "job_id" in result else "completed","result":result}
        except Failure as error:
            answer = {"schema_version":1,"request_id":request_id,"event":"failed","error":{"code":error.code,"message":error.message}}
        except (ValidationError,ValueError,KeyError,TypeError,asyncio.TimeoutError):
            answer = {"schema_version":1,"request_id":request_id,"event":"failed","error":{"code":"VALIDATION_ERROR","message":"تعذّر التحقق من الطلب."}}
        except Exception:
            answer = {"schema_version":1,"request_id":request_id,"event":"failed","error":{"code":"ENGINE_CRASHED","message":"حدث خطأ داخلي. بياناتك المحلية محفوظة؛ أعد المحاولة."}}
        try:
            encoded = json.dumps(answer,ensure_ascii=False).encode()+b"\n"
            if len(encoded)>MAX_FRAME:
                encoded = json.dumps({"schema_version":1,"request_id":request_id,"event":"failed","error":{"code":"VALIDATION_ERROR","message":"النتيجة أكبر من حد الرسالة؛ قلل النطاق."}}).encode()+b"\n"
            writer.write(encoded)
            await writer.drain()
        except (ConnectionError,BrokenPipeError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_unix_server(connected,path=str(socket_path),limit=MAX_FRAME)
    os.chmod(socket_path,0o600)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM,signal.SIGINT):
        loop.add_signal_handler(sig,stop.set)
    parent = os.getppid()

    async def parent_watch():
        while not stop.is_set():
            await asyncio.sleep(1)
            if os.getppid()!=parent:
                stop.set()
    watch = asyncio.create_task(parent_watch())
    try:
        async with server:
            await stop.wait()
    finally:
        watch.cancel()
        await service.close()
        socket_path.unlink(missing_ok=True)
        lock.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace",type=Path,required=True)
    parser.add_argument("--socket",type=Path,required=True)
    args = parser.parse_args()
    # Suppress third-party logs: provider exceptions can contain private request bodies.
    logging.disable(logging.CRITICAL)
    asyncio.run(serve(args.workspace,args.socket))


if __name__ == "__main__":
    main()
