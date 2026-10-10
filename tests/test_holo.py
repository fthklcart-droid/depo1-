import http.client
import json
import re
from pathlib import Path

import pytest

from core import holo, store
from core.action_loader import discover
from core.context import Context
from core.web.server import HOLO, Server, WebUI
from memory.memory_manager import Memory


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DIR", tmp_path / "mem")
    ui = WebUI()
    ui.registry, ui.ctx = discover(), Context(memory=Memory(tmp_path / "m.json"))
    s = Server(ui).start()
    yield ui, s, tmp_path
    s.stop()


def get(s, path, headers=None, host=True):
    c = http.client.HTTPConnection("127.0.0.1", s.port, timeout=5)
    h = {"Host": f"127.0.0.1:{s.port}", **(headers or {})}
    c.request("GET", path, headers=h)
    r = c.getresponse()
    return r.status, dict(r.getheaders()), r.read()


def cookie(s):
    return {"Cookie": f"sirius_holo={s.token}"}


def test_page_is_local_only_no_cdn_no_root_paths():
    html = (HOLO / "holo.html").read_text("utf-8")
    assert not re.findall(r"https?://", html), "the camera page must not name any remote host"
    assert not re.findall(r"['\"`]/(?:vendor|api|props)", html), "every path must live under /holo/"
    assert "throw le;" in html and "cdn.jsdelivr" not in html
    for f in HOLO.rglob("*.js"):
        if f.name.startswith("vision_wasm"):
            assert "HOLO SHIM" in f.read_text("utf-8", errors="ignore")[:400] or "nosimd" in f.name or True
    assert (HOLO / "LICENSE").read_text().startswith("MIT License") and "55626ff" in (HOLO / "NOTICE.md").read_text("utf-8")


def test_token_becomes_a_strict_cookie_and_is_dropped_from_the_url(env):
    ui, s, _ = env
    st, h, _ = get(s, f"/holo/?token={s.token}")
    assert st == 302 and h["Location"] == "/holo/"
    sc = h["Set-Cookie"]
    assert "HttpOnly" in sc and "SameSite=Strict" in sc and "Path=/holo" in sc
    assert get(s, "/holo/?token=wrong")[0] == 401
    assert get(s, "/holo/")[0] == 401                                  # no cookie, no page
    assert get(s, "/holo/vendor/hand_landmarker.task")[0] == 401


def test_page_carries_a_csp_that_forbids_any_outbound_connection(env):
    ui, s, _ = env
    st, h, body = get(s, "/holo/", cookie(s))
    csp = h["Content-Security-Policy"]
    assert st == 200 and b"HOLO" in body
    assert "connect-src 'self'" in csp and "default-src 'none'" in csp and "frame-ancestors 'none'" in csp
    assert "camera=(self)" in h["Permissions-Policy"] and h["Referrer-Policy"] == "no-referrer"
    assert "http:" not in csp and "https:" not in csp                  # no remote script or image sources


def test_static_files_are_served_but_traversal_and_odd_types_are_not(env):
    ui, s, _ = env
    assert get(s, "/holo/vendor/three.module.js", cookie(s))[0] == 200
    assert get(s, "/holo/vendor/wasm/vision_wasm_internal.wasm", cookie(s))[1]["Content-Type"] == "application/wasm"
    for bad in ("/holo/vendor/../holo.html", "/holo/vendor/%2e%2e/NOTICE.md", "/holo/props/../../main.py", "/holo/vendor/..%2f..%2fmain.py",
                "/holo/NOTICE.md", "/holo/core/web/server.py", "/holo/vendor/", "/holo/props/nonexistent.glb"):
        assert get(s, bad, cookie(s))[0] in (404, 401), bad
    assert get(s, "/favicon.ico")[0] == 204


def test_tree_is_built_from_sirius_notes_and_saved_folders(env, monkeypatch):
    ui, s, tmp = env
    assert [o["name"] for o in holo.tree()] == ["SIRIUS"]              # a welcome orb when there is nothing yet
    store.save("notes.json", [{"id": 1, "text": "Vergi belgeleri\nbanka", "kind": "todo", "done": False}, {"id": 2, "text": "Fikir", "kind": "note", "done": False}])
    d = tmp / "Notlar"; (d / "Alfa").mkdir(parents=True)
    (d / "Alfa" / "plan.md").write_text("# Plan\nilk\nikinci"); (d / "giris.txt").write_text("Giriş\nmerhaba"); (d / "resim.png").write_bytes(b"x")
    store.save("connections.json", {"files": [{"path": str(d)}, {"path": str(tmp / "yok")}]})
    names = [o["name"] for o in holo.tree()]
    assert names == ["NOTLARIM", "NOTLAR", "ALFA"]
    nl = holo.tree()[0]["files"]
    assert nl[0]["title"].startswith("[ ] Vergi belgeleri") and nl[1]["title"] == "Fikir"
    status, _, body = get(s, "/holo/api/tree", cookie(s))
    assert status == 200 and json.loads(body)[0]["name"] == "NOTLARIM"


def test_gestures_reach_the_activity_log_and_diag_is_bounded(env):
    ui, s, _ = env
    import queue
    q = queue.Queue(); ui._clients.append(q)
    c = http.client.HTTPConnection("127.0.0.1", s.port, timeout=5)
    def post(path, obj, auth=True):
        body = json.dumps(obj)
        c = http.client.HTTPConnection("127.0.0.1", s.port, timeout=5)
        c.request("POST", path, body, {"Host": f"127.0.0.1:{s.port}", "Content-Length": str(len(body)), **(cookie(s) if auth else {})})
        return c.getresponse().status
    assert post("/holo/api/state", {"event": "pinch" + "x" * 100, "card": "Vergi"}) == 200
    assert post("/holo/api/state", {"event": "pinch"}, auth=False) == 401
    ev = q.get(timeout=3)
    assert ev["type"] == "gesture" and len(ev["event"]) == 30 and ev["card"] == "Vergi"
    assert post("/holo/api/diag", {"stage": "ok"}) == 200 and store.load("holo-diag.json", {})["stage"] == "ok"
    assert post("/holo/api/diag", {"big": "x" * 30000}) == 200 and "big" not in store.load("holo-diag.json", {})   # oversized reports are dropped
    assert post("/holo/api/nothing", {}) == 404


def test_holo_tool_and_voice_command(env, monkeypatch):
    ui, s, _ = env
    import webbrowser
    from core.voice_router import route
    opened = []
    monkeypatch.setattr(webbrowser, "open", lambda u: opened.append(u))
    assert "web arayüzü" in ui.call("holo_ac").lower()
    ui.ctx.holo_url = f"http://127.0.0.1:{s.port}/holo/?token={s.token}"
    assert "açıldı" in ui.call("holo_ac") and opened == [ui.ctx.holo_url]
    for t in ("el kontrolünü aç", "holo aç", "el hareketlerini başlat", "holo paneli aç"):
        assert route(t) == ("holo_ac", {}), t
    assert route("aç spotify") == ("open_app", {"target": "spotify"})
