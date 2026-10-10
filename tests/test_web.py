import http.client
import json
import queue
import threading

import pytest

from core import store
from core.action_loader import discover
from core.agent import Agent
from core.backends import ScriptedBackend
from core.context import Context
from core.web import server as srvmod
from core.web.server import Server, WebUI
from memory.memory_manager import Memory


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DIR", tmp_path / "mem")
    monkeypatch.setattr(srvmod.time, "sleep", lambda s: None)
    ui = WebUI()
    ctx = Context(memory=Memory(tmp_path / "m.json"), confirm=ui.confirm, notify=ui.write_log)
    ui.registry, ui.ctx = discover(), ctx
    s = Server(ui).start()
    yield ui, s, tmp_path
    s.stop()


def req(s, method, path, body=None, token=True, host=None):
    c = http.client.HTTPConnection("127.0.0.1", s.port, timeout=5)
    h = {"Host": host or f"127.0.0.1:{s.port}"}
    if token:
        h["X-Token"] = s.token
    if body is not None:
        h["Content-Type"] = "application/json"
    c.request(method, path, json.dumps(body) if body is not None else None, h)
    r = c.getresponse()
    return r.status, r.read()


def test_token_and_host_are_enforced(env):
    ui, s, _ = env
    assert req(s, "GET", "/api/tools", token=False)[0] == 401
    assert req(s, "POST", "/api/say", {"text": "x"}, token=False)[0] == 401
    assert req(s, "GET", "/api/tools", host="evil.example:80")[0] == 403          # DNS-rebinding style request
    assert req(s, "POST", "/api/confirm", {"id": "x", "ok": True}, token=False)[0] == 401
    assert req(s, "GET", "/s3d.js", token=False)[0] == 200                         # a public script, no secrets
    assert req(s, "GET", "/", token=False)[0] == 401                               # the page itself needs the token


def test_index_embeds_token_and_escapes_nothing_dynamic(env):
    ui, s, _ = env
    st, body = req(s, "GET", "/?token=" + s.token, token=False)
    assert st == 200 and s.token.encode() in body and b"__TOKEN__" not in body
    html = (srvmod.WEB / "index.html").read_text("utf-8")
    assert "innerHTML" not in html and "document.write" not in html and "eval(" not in html   # model/web text is textContent only


def test_say_runs_the_agent_and_streams_states(env):
    ui, s, _ = env
    ui.cfg = type("C", (), {"get": lambda self, k: "SIRIUS"})()
    ui.ask = Agent(ScriptedBackend([{"text": "", "calls": [{"name": "calculate", "args": {"expression": "6*7"}}]},
                                    {"text": "Sonuç 42", "calls": []}]), ui.registry, ui.ctx).ask
    q = queue.Queue()
    ui._clients.append(q)
    assert json.loads(req(s, "POST", "/api/say", {"text": "6 çarpı 7?"})[1])["ok"]
    events = []
    while True:
        e = q.get(timeout=5)
        events.append(e)
        if e["type"] == "state" and e["state"] == "LISTENING":
            break
    states = [e["state"] for e in events if e["type"] == "state"]
    assert states == ["THINKING", "SPEAKING", "LISTENING"]
    assert {"type": "say", "text": "Sonuç 42"} in events
    assert any(e["type"] == "log" and e["line"] == "Sen: 6 çarpı 7?" for e in events)


def test_confirm_is_decided_by_the_browser_only(env):
    ui, s, tmp = env
    res = []
    q = queue.Queue(); ui._clients.append(q)
    t = threading.Thread(target=lambda: res.append(ui.registry.call("run_shell", {"command": "echo hi-web"}, ui.ctx).text))
    t.start()
    ev = q.get(timeout=5)
    assert ev["type"] == "confirm" and "echo hi-web" in ev["prompt"]
    assert json.loads(req(s, "POST", "/api/confirm", {"id": "wrong", "ok": True})[1])["ok"] is False   # forged id changes nothing
    assert t.is_alive()
    assert json.loads(req(s, "POST", "/api/confirm", {"id": ev["id"], "ok": True})[1])["ok"] is True
    t.join(5)
    assert "hi-web" in res[0]


def test_confirm_decline_runs_nothing(env):
    ui, s, _ = env
    res, q = [], queue.Queue(); ui._clients.append(q)
    t = threading.Thread(target=lambda: res.append(ui.registry.call("run_shell", {"command": "echo nope"}, ui.ctx).text))
    t.start()
    ev = q.get(timeout=5)
    req(s, "POST", "/api/confirm", {"id": ev["id"], "ok": False}); t.join(5)
    assert "declined" in res[0]


def test_sse_stream_replays_history(env):
    ui, s, _ = env
    ui.write_log("merhaba geçmiş")
    c = http.client.HTTPConnection("127.0.0.1", s.port, timeout=5)
    c.request("GET", "/events?token=" + s.token, headers={"Host": f"127.0.0.1:{s.port}"})
    r = c.getresponse()
    assert r.status == 200 and r.getheader("Content-Type") == "text/event-stream"
    got = r.fp.readline().decode() + r.fp.readline().decode() + r.fp.readline().decode()
    assert "merhaba geçmiş" in got
    c.close()


def test_connections_api_roundtrip(env):
    ui, s, tmp = env
    doc = tmp / "notlar.md"; doc.write_text("Sirius projesi için vergi belgeleri ve fatura notları")
    call = lambda **b: json.loads(req(s, "POST", "/api/connections", b)[1])["text"]  # noqa: E731
    assert "Eklendi" in call(action="add_site", url="ornek.com")
    assert "zaten" in call(action="add_site", url="https://ornek.com")
    assert "1 new/changed" in call(action="add_file", path=str(doc))                 # a single file is indexed too
    assert "Eklendi: Spotify" in call(action="add_app", name="Spotify", alias="müzik", command="")
    listing = call(action="list")
    assert "site: https://ornek.com" in listing and "dosya:" in listing and "uygulama: Spotify (takma ad: müzik)" in listing
    assert "notlar.md" in ui.call("doc_search", action="search", query="vergi fatura")
    assert "Kaldırıldı" in call(action="remove_site", url="https://ornek.com")
    assert "Kaldırıldı" in call(action="remove_file", path=str(doc))
    assert ui.call("doc_search", action="search", query="vergi") in ("No matches.", "No index yet. Call doc_search with action=index and a folder first.")
    assert req(s, "POST", "/api/connections", {"action": "delete_everything"})[0] == 400
    assert "bulunamadı" in call(action="add_file", path=str(tmp / "yok"))


def test_read_site_only_fetches_saved_sites(env):
    ui, s, _ = env
    assert "eklenmemiş" in ui.call("connections", action="read_site", url="https://not-saved.example")


def test_open_app_resolves_saved_alias(env, monkeypatch):
    ui, s, _ = env
    ui.call("connections", action="add_app", name="Editörüm", alias="kod", command="echo launched")
    import subprocess
    seen = []
    monkeypatch.setattr(subprocess, "Popen", lambda argv, **k: seen.append(argv))
    assert "Started Editörüm" in ui.call("open_app", target="kod")
    assert seen == [["echo", "launched"]]


def test_undo_endpoint_and_bad_json(env):
    ui, s, _ = env
    ui.call("connections", action="add_site", url="https://a.example")
    assert "Undone" in json.loads(req(s, "POST", "/api/undo", {})[1])["text"]
    assert "a.example" not in ui.call("connections", action="list")
    c = http.client.HTTPConnection("127.0.0.1", s.port, timeout=5)
    c.request("POST", "/api/say", "{not json", {"Host": f"127.0.0.1:{s.port}", "X-Token": s.token, "Content-Length": "9"})
    assert c.getresponse().status == 400
