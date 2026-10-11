"""The avatar-only ('sade') mode must never hide the one thing that has to stay reachable: the confirmation card."""
import html.parser
import os
import pathlib
import sys
import tempfile
import threading

import pytest

INDEX = pathlib.Path(__file__).resolve().parent.parent / "web" / "index.html"


class Tree(html.parser.HTMLParser):
    VOID = {"meta", "link", "input", "br", "img", "path", "circle", "svg"}

    def __init__(self):
        super().__init__(); self.stack, self.ancestors = [], {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ancestors[a["id"]] = [c for _, c in self.stack for c in (c or "").split()]
        if tag not in self.VOID:
            self.stack.append((tag, a.get("class")))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]; break


def test_confirm_card_does_not_live_inside_a_hideable_panel():
    t = Tree(); t.feed(INDEX.read_text("utf-8"))
    for hidden in ("left", "right", "sw"):
        assert hidden not in t.ancestors["confirm"], f"the confirm card sits inside .{hidden}, which sade mode hides"
    css = INDEX.read_text("utf-8")
    assert ".confirm{position:fixed" in css and ".sade .left,.sade .right" in css and "#confirm" not in css.split("/* sade mod")[1].split("@media")[0]


def test_sade_is_the_default_and_remembered():
    h = INDEX.read_text("utf-8")
    assert "sade = true" in h and "localStorage.getItem('sirius.sade') !== '0'" in h and "localStorage.setItem('sirius.sade'" in h
    assert "innerHTML = " not in h.replace("el.innerHTML", "")


def test_in_a_real_browser_confirm_is_answerable_with_panels_hidden():
    sync = pytest.importorskip("playwright.sync_api")
    exe = "/opt/pw-browsers/chromium"
    if not os.path.exists(exe):
        pytest.skip("chromium not available")
    from core import store
    from core.action_loader import discover
    from core.context import Context
    from core.web.server import Server, WebUI
    from memory.memory_manager import Memory
    d = pathlib.Path(tempfile.mkdtemp()); old = store.DIR; store.DIR = d
    try:
        ui = WebUI(); ui.registry = discover(); ui.ctx = Context(memory=Memory(d / "m.json"), confirm=ui.confirm)
        srv = Server(ui).start()
        with sync.sync_playwright() as p:
            b = p.chromium.launch(executable_path=exe, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
            pg = b.new_page(viewport={"width": 1280, "height": 760}); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://127.0.0.1:{srv.port}/?token={srv.token}"); pg.wait_for_timeout(1500)
            shown = lambda sel: pg.evaluate(f"(()=>{{const e=document.querySelector('{sel}');return !!e&&getComputedStyle(e).display!=='none'&&e.getBoundingClientRect().width>0}})()")
            assert not shown(".left") and not shown(".right") and shown("#stage canvas")
            out = []
            t = threading.Thread(target=lambda: out.append(ui.registry.call("run_shell", {"command": "echo ok-sade"}, ui.ctx).text)); t.start()
            pg.wait_for_selector("#confirm.show", timeout=5000)
            r = pg.evaluate("(()=>{const r=document.querySelector('#cYes').getBoundingClientRect();return [r.x,r.y,r.right,r.bottom,innerWidth,innerHeight]})()")
            assert r[0] >= 0 and r[1] >= 0 and r[2] <= r[4] and r[3] <= r[5]
            pg.click("#cYes"); t.join(8)
            assert "ok-sade" in out[0] and not errs
            pg.click("#sadeBtn"); pg.wait_for_timeout(300)
            assert shown(".left") and shown(".right")
            b.close()
    finally:
        store.DIR = old; srv.stop()
