#!/usr/bin/env python3
"""Serve the dice page and the shared roll file on this machine."""
import json
import mimetypes
import threading

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("font/ttf", ".ttf")
mimetypes.add_type("image/jpeg", ".jpg")
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
SAVES = ROOT / "saves" / "rolls.json"
MAX_AGE = timedelta(days=3)
HOST = "127.0.0.1"
PORT = 8099
LOCK = threading.Lock()


def parse_time(value):
    if not isinstance(value, str):
        return None
    try:
        when = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone(timezone.utc)


def load_rows():
    if not SAVES.is_file():
        return []
    try:
        data = json.loads(SAVES.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def fresh(rows):
    cut = datetime.now(timezone.utc) - MAX_AGE
    kept = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        when = parse_time(row.get("rolledAt"))
        if when is not None and when >= cut:
            kept.append(row)
    kept.sort(key=lambda row: row.get("rolledAt", ""), reverse=True)
    return kept


def store(rows):
    SAVES.parent.mkdir(parents=True, exist_ok=True)
    tmp = SAVES.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(rows, indent=2) + "\n")
    tmp.replace(SAVES)


def clean_name(value):
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:40]


def clean_dice(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 2:
        return None
    faces = []
    for n in value:
        if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 20:
            return None
        faces.append(n)
    return faces


def list_rolls():
    with LOCK:
        rows = fresh(load_rows())
        store(rows)
        return rows


def save_roll(name, dice):
    name = clean_name(name)
    faces = clean_dice(dice)
    if not name or faces is None:
        return None
    row = {
        "id": uuid4().hex[:12],
        "name": name,
        "rolledAt": datetime.now(timezone.utc).isoformat(),
        "dice": faces,
    }
    with LOCK:
        rows = fresh(load_rows())
        rows.insert(0, row)
        store(rows)
    return row


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def send_json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/rolls":
            self.send_json(200, {"rows": list_rolls()})
            return
        self.send_file(path)

    def do_POST(self):
        if urlparse(self.path).path != "/api/rolls":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > 2000:
            self.send_json(400, {"error": "bad request"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self.send_json(400, {"error": "bad request"})
            return
        if not isinstance(payload, dict):
            self.send_json(400, {"error": "bad request"})
            return
        row = save_roll(payload.get("name"), payload.get("dice"))
        if row is None:
            self.send_json(400, {"error": "name and dice required"})
            return
        self.send_json(200, {"row": row})

    def send_file(self, url_path):
        rel = unquote(url_path).lstrip("/") or "index.html"
        path = (ROOT / rel).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            self.send_error(404)
            return
        if "saves" in path.parts or ".git" in path.parts:
            self.send_error(404)
            return
        data = path.read_bytes()
        kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
