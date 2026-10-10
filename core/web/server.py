"""Local web UI: the HUD in a browser, wired to the real assistant.

Security: binds to 127.0.0.1 only, every request needs a per-run token, and the Host header must be
ours (blocks DNS rebinding). A random web page therefore cannot send commands or press CONFIRM.
"""
from __future__ import annotations

import json
import mimetypes
import queue
import secrets
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent.parent / "web"
CONFIRM_TIMEOUT = 120


class WebUI:
    """Implements core.ui.UI for a browser. Events fan out to every connected page over SSE."""
    muted = False

    def __init__(self):
        self._clients: list[queue.Queue] = []
        self._lock = threading.Lock()
        self._history: list[dict] = []
        self._pending: dict[str, tuple[threading.Event, list]] = {}
        self.state = "LISTENING"
        self.ask = None                      # callable(text) -> str, set by serve()/main
        self.registry = self.ctx = self.cfg = None
        self._busy = threading.Lock()

    # ---- UI protocol --------------------------------------------------------------------
    def emit(self, kind: str, **data) -> None:
        ev = {"type": kind, **data}
        with self._lock:
            if kind in ("log", "content", "state"):
                self._history = (self._history + [ev])[-60:]
            for q in list(self._clients):
                q.put(ev)

    def set_state(self, state):
        self.state = state
        self.emit("state", state=state)

    def write_log(self, line):
        self.emit("log", line=str(line))

    def set_audio_level(self, level):
        pass

    def push_visemes(self, frames, hop, at):
        pass

    def show_content(self, title, body):
        self.emit("content", title=title, body=body)

    def confirm(self, prompt: str) -> bool:
        """Blocks the asking thread until the human presses a button in the browser."""
        cid = secrets.token_hex(6)
        ev, box = threading.Event(), [False]
        self._pending[cid] = (ev, box)
        self.emit("confirm", id=cid, prompt=prompt)
        ev.wait(CONFIRM_TIMEOUT)
        self._pending.pop(cid, None)
        self.emit("confirm_done", id=cid)
        return box[0]

    def answer_confirm(self, cid: str, ok: bool) -> bool:
        item = self._pending.get(cid)
        if not item:
            return False
        item[1][0] = bool(ok)
        item[0].set()
        return True

    # ---- a user message -----------------------------------------------------------------
    def say(self, text: str) -> None:
        threading.Thread(target=self._run_say, args=(text,), daemon=True).start()

    def _run_say(self, text: str) -> None:
        if not self.ask:
            self.write_log("SYS: Asistan modeli bağlı değil (API anahtarı yok).")
            return
        if not self._busy.acquire(blocking=False):
            self.write_log("SYS: Önceki işlem sürüyor, bitince tekrar dene.")
            return
        try:
            self.write_log(f"Sen: {text}")
            self.set_state("THINKING")
            try:
                answer = self.ask(text)
            except Exception as e:  # noqa: BLE001 - a model error must not kill the server
                self.write_log(f"ERR: {type(e).__name__}: {e}")
                return
            self.emit("say", text=answer)
            self.write_log(f"{(self.cfg.get('assistant_name') if self.cfg else 'SIRIUS')}: {answer}")
            self.set_state("SPEAKING")
            time.sleep(min(8.0, 0.8 + len(answer) * 0.03))   # no audio in text mode: hold the pose while it is "read"
        finally:
            self.set_state("LISTENING")
            self._busy.release()

    # ---- data for the page --------------------------------------------------------------
    def tools(self) -> list[dict]:
        return [{"name": n, "description": t["description"]} for n, t in sorted(self.registry.tools.items())] if self.registry else []

    def call(self, tool: str, **params) -> str:
        return self.registry.call(tool, params, self.ctx).text


def make_handler(ui: WebUI, token: str, port: int):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _ok(self) -> bool:
            if self.headers.get("Host", "") not in allowed_hosts:
                self._send(403, b"bad host", "text/plain")
                return False
            return True

        def _authed(self, qs) -> bool:
            sent = self.headers.get("X-Token") or (qs.get("token") or [""])[0]
            if not secrets.compare_digest(sent, token):
                self._send(401, b"token required", "text/plain")
                return False
            return True

        def _send(self, code, body: bytes, ctype="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") or "json" in ctype else ""))
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode())

        def do_GET(self):
            if not self._ok():
                return
            u = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(u.query)
            if u.path in ("/", "/index.html", "/s3d.js"):
                if u.path != "/s3d.js" and not self._authed(qs):
                    return
                f = WEB / ("index.html" if u.path != "/s3d.js" else "s3d.js")
                body = f.read_bytes()
                if f.name == "index.html":
                    body = body.replace(b"__TOKEN__", token.encode())
                return self._send(200, body, mimetypes.guess_type(f.name)[0] or "text/plain")
            if not self._authed(qs):
                return
            if u.path == "/events":
                return self._sse()
            if u.path == "/api/tools":
                return self._json(ui.tools())
            if u.path == "/api/today":
                return self._json({"events": ui.call("calendar", action="today"), "todos": ui.call("notes", action="list", kind="todo")})
            if u.path == "/api/connections":
                return self._json(ui.call("connections", action="list"))
            self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if not self._ok() or not self._authed({}):
                return
            n = int(self.headers.get("Content-Length") or 0)
            if n > 100_000:
                return self._send(413, b"too large", "text/plain")
            try:
                data = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._send(400, b"bad json", "text/plain")
            path = urllib.parse.urlparse(self.path).path
            if path == "/api/say":
                text = str(data.get("text", "")).strip()[:4000]
                if text:
                    ui.say(text)
                return self._json({"ok": bool(text)})
            if path == "/api/confirm":
                return self._json({"ok": ui.answer_confirm(str(data.get("id", "")), bool(data.get("ok")))})
            if path == "/api/connections":
                allowed = {"add_site", "remove_site", "read_site", "add_file", "remove_file", "add_app", "remove_app", "list"}
                action = data.get("action")
                if action not in allowed:
                    return self._json({"ok": False, "text": "bad action"}, 400)
                params = {k: v for k, v in data.items() if k in ("url", "path", "name", "alias", "command", "watch") and isinstance(v, (str, bool))}
                return self._json({"ok": True, "text": ui.call("connections", action=action, **params)})
            if path == "/api/undo":
                return self._json({"ok": True, "text": ui.ctx.undo.undo()})
            self._send(404, b"not found", "text/plain")

        def _sse(self):
            q: queue.Queue = queue.Queue()
            with ui._lock:
                ui._clients.append(q)
                replay = list(ui._history)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                for ev in replay + [{"type": "state", "state": ui.state}]:
                    self.wfile.write(f"data: {json.dumps(ev, ensure_ascii=False)}\n\n".encode())
                self.wfile.flush()
                while True:
                    try:
                        ev = q.get(timeout=15)
                        self.wfile.write(f"data: {json.dumps(ev, ensure_ascii=False)}\n\n".encode())
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                with ui._lock:
                    if q in ui._clients:
                        ui._clients.remove(q)

    return H


class Server:
    def __init__(self, ui: WebUI, port: int = 0):
        self.ui, self.token = ui, secrets.token_urlsafe(24)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), lambda *a, **k: make_handler(ui, self.token, self.httpd.server_address[1])(*a, **k))
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}/?token={self.token}"

    def start(self) -> "Server":
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
