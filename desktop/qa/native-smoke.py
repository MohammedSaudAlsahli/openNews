"""Exercise the packaged QA engine, never the installed user's workspace.

Run with the PID of the isolated com.opennews.ui-qa application. No model
requests, credentials, model downloads or user workspace reads are needed.
The optional --feed check retrieves public feed/article content.
"""
import argparse
import json
from pathlib import Path
import re
import socket
import subprocess
import time
import uuid

parser = argparse.ArgumentParser()
parser.add_argument("--pid", type=int, required=True)
parser.add_argument("--feed", help="Optional public RSS/Atom URL for a live retrieval check")
args = parser.parse_args()
expected = Path.home() / "Library/Application Support/com.opennews.ui-qa/default"
children = subprocess.check_output(["pgrep", "-P", str(args.pid)], text=True).split()
engine_socket = None
for child in children:
    command = subprocess.check_output(["ps", "-ww", "-p", child, "-o", "command="], text=True)
    match = re.search(r" --workspace (.+) --socket (\S+)\s*$", command)
    if match:
        assert Path(match[1]) == expected, "Refusing a non-QA workspace"
        engine_socket = match[2]
assert engine_socket, "No packaged QA engine is running"

timings = {}

def call(command, payload=None):
    started = time.perf_counter()
    identifier = str(uuid.uuid4())
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
        stream.settimeout(45)
        stream.connect(engine_socket)
        stream.sendall((json.dumps({"schema_version": 1, "request_id": identifier, "command": command, "payload": payload or {}}) + "\n").encode())
        response = json.loads(stream.makefile("rb").readline())
    timings[command] = round((time.perf_counter() - started) * 1000, 1)
    assert response["request_id"] == identifier and response["event"] != "failed", response.get("error")
    return response["result"]

assert call("runtime.health")["schema_version"] == 1
original = call("assistant.get", {"scope": "general"})["settings"]
assert len(original["role"]) > 10
try:
    changed = {**original, "style": "# QA style\n\nKeep <u>formatting</u> and `code` readable."}
    call("assistant.save", {"scope": "general", "settings": changed})
    assert call("assistant.get", {"scope": "general"})["settings"]["style"] == changed["style"]
finally:
    call("assistant.save", {"scope": "general", "settings": original})

chat = call("chat.create", {"title": "QA · محفوظة محليًا"})
assert call("chat.detail", {"conversation_id": chat["conversation_id"]})["title"] == "QA · محفوظة محليًا"
draft = call("drafts.create", {"topic": "QA · صياغة قابلة للتعديل", "format": "linkedin", "language": "ar", "text": "# فكرة\n\nمسودة اختبار."})
call("drafts.save", {"draft_id": draft["draft_id"], "text": "# فكرة معدّلة\n\nمسودة اختبار محفوظة."})
assert len(call("drafts.detail", {"draft_id": draft["draft_id"]})["versions"]) == 2
snapshot = call("workspace.snapshot")
assert any(row["id"] == draft["draft_id"] for row in snapshot["drafts"])
assert isinstance(call("news.list", {"limit": 10})["articles"], list)
call("news.search.status")
call("news.digest.status")
feed_result = None
if args.feed:
    source = call("news.subscribe", {"url": args.feed, "title": "QA · Live feed"})["subscription_id"]
    deadline = time.monotonic() + 60
    articles = []
    while time.monotonic() < deadline:
        articles = call("news.list", {"source_id": source, "limit": 1})["articles"]
        if articles:
            break
        time.sleep(1)
    assert articles, "The public feed did not return an article within 60 seconds"
    article = call("news.reader", {"article_id": articles[0]["id"]})
    assert article["body_status"] == "full" and len(article["text"]) > 80
    history = call("news.history", {"article_id": article["id"]})
    assert history["revisions"]
    call("news.bookmark", {"article_id": article["id"], "saved": True})
    assert call("news.list", {"scope": "saved", "limit": 10})["articles"]
    feed_result = {"url": args.feed, "body_status": article["body_status"], "characters": len(article["text"]), "revisions": len(history["revisions"])}
print(json.dumps({"workspace": "isolated QA", "checks": ["packaged engine", "instructions read/save/restore", "conversation persistence", "draft versions", "snapshot", "article list", "processing status"], "milliseconds": timings}, ensure_ascii=False))
if feed_result:
    print(json.dumps({"live_feed": feed_result}, ensure_ascii=False))
