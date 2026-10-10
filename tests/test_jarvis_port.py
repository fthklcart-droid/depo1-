import io
import json
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser

import pytest

from core import store
from core.action_loader import discover
from core.context import Context
from core.voice_router import route
from memory.memory_manager import Memory


class Resp:
    def __init__(self, obj):
        self.b = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
    def read(self, n=-1): return self.b if n < 0 else self.b[:n]
    def __enter__(self): return self
    def __exit__(self, *a): return False


@pytest.fixture
def reg():
    return discover()


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DIR", tmp_path / "mem")
    return Context(memory=Memory(tmp_path / "m.json"), confirm=lambda p: True)


def mod(reg, tool):
    return sys.modules[reg.handlers[tool].__module__]


# ── vikipedi ────────────────────────────────────────────────────────────────
def test_wikipedia_summary_falls_back_to_english_and_labels_untrusted(reg, ctx, monkeypatch):
    seen = []
    def fake(req, timeout=0):
        u = req.full_url; seen.append(u)
        assert req.headers["User-agent"].startswith("SiriusAssistant")                   # Wikimedia requires an identifying agent
        if "tr.wikipedia.org/w/api.php" in u:
            return Resp({"query": {"search": []}})
        if "en.wikipedia.org/w/api.php" in u:
            return Resp({"query": {"search": [{"title": "Sirius B"}]}})
        return Resp({"title": "Sirius B", "extract": "Sirius B is a white dwarf. It orbits Sirius A. Discovered in 1862. Fourth sentence.", "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Sirius_B"}}})
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    out = reg.call("vikipedi", {"konu": "Sirius B", "cumle": 2}, ctx).text
    assert out.startswith("[UNTRUSTED") and "white dwarf. It orbits Sirius A." in out and "Discovered" not in out and "en.wikipedia.org/wiki/Sirius_B" in out
    assert any("Sirius_B" in u and "rest_v1" in u for u in seen)


def test_wikipedia_no_result_and_network_error(reg, ctx, monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda r, timeout=0: Resp({"query": {"search": []}}))
    assert "sonuç yok" in reg.call("vikipedi", {"konu": "asdfqwer"}, ctx).text
    def boom(r, timeout=0): raise urllib.error.URLError("offline")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert "ulaşılamadı" in reg.call("vikipedi", {"konu": "x"}, ctx).text


# ── sozluk ──────────────────────────────────────────────────────────────────
def test_dictionary_offline_exact_and_suggestions(reg, ctx, tmp_path, monkeypatch):
    m = mod(reg, "sozluk"); f = tmp_path / "sozluk.json"
    f.write_text(json.dumps({"serendipity": ["Finding good things by chance."], "separate": ["To divide."], "apple": ["A fruit."]}), "utf-8")
    monkeypatch.setattr(m, "DATA", f); m._cache.clear()
    assert reg.call("sozluk", {"kelime": "Serendipity"}, ctx).text == "serendipity: Finding good things by chance."
    out = reg.call("sozluk", {"kelime": "seperate"}, ctx).text
    assert "bulunamadı" in out and "separate" in out and "apple" not in out                # a typo gets the near word, not noise
    assert "bulunamadı" in reg.call("sozluk", {"kelime": "zzzzzz"}, ctx).text and "mu demek" not in reg.call("sozluk", {"kelime": "zzzzzz"}, ctx).text
    assert reg.call("sozluk", {}, ctx).text == "kelime ver."


def test_dictionary_online_fallback(reg, ctx, tmp_path, monkeypatch):
    m = mod(reg, "sozluk"); monkeypatch.setattr(m, "DATA", tmp_path / "yok.json"); m._cache.clear()
    monkeypatch.setattr(urllib.request, "urlopen", lambda r, timeout=0: Resp([{"meanings": [{"definitions": [{"definition": "A lucky find."}, {"definition": "Chance."}]}]}]))
    assert reg.call("sozluk", {"kelime": "serendipity"}, ctx).text == "serendipity: A lucky find. | Chance."
    def nf(r, timeout=0): raise urllib.error.HTTPError(r.full_url, 404, "nf", {}, io.BytesIO(b""))
    monkeypatch.setattr(urllib.request, "urlopen", nf)
    assert "bulunamadı" in reg.call("sozluk", {"kelime": "qqqq"}, ctx).text
    def down(r, timeout=0): raise urllib.error.URLError("x")
    monkeypatch.setattr(urllib.request, "urlopen", down)
    assert "indir" in reg.call("sozluk", {"kelime": "x"}, ctx).text


def test_dictionary_download_needs_consent_and_validates(reg, tmp_path, monkeypatch):
    m = mod(reg, "sozluk"); f = tmp_path / "data" / "sozluk.json"; monkeypatch.setattr(m, "DATA", f)
    no = Context(memory=Memory(tmp_path / "m.json"), confirm=lambda p: False)
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: pytest.fail("must not download without consent"))
    assert reg.call("sozluk", {"action": "indir"}, no).text == "İndirilmedi." and not f.exists()
    yes = Context(memory=Memory(tmp_path / "m.json"), confirm=lambda p: True)
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: Resp({"a": ["x"], "b": ["y"]}))
    assert "2 kelime" in reg.call("sozluk", {"action": "indir"}, yes).text and f.exists()
    f.unlink()
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: Resp([1, 2, 3]))
    assert "biçimde değil" in reg.call("sozluk", {"action": "indir"}, yes).text and not f.exists()
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: Resp({"a": "not-a-list"}))
    assert "biçimde değil" in reg.call("sozluk", {"action": "indir"}, yes).text


# ── quick links, ocr, screenshot, jokes ─────────────────────────────────────
def test_quick_links_encode_the_query(reg, ctx, monkeypatch):
    opened = []; monkeypatch.setattr(webbrowser, "open", lambda u: opened.append(u))
    reg.call("youtube_ara", {"sorgu": "lofi müzik & jazz"}, ctx); reg.call("harita_ara", {"yer": "Kızılay Ankara"}, ctx); reg.call("harita_ara", {"yer": "x", "saglayici": "osm"}, ctx)
    assert opened[0] == "https://www.youtube.com/results?search_query=lofi%20m%C3%BCzik%20%26%20jazz"
    assert opened[1].startswith("https://www.google.com/maps/search/?api=1&query=K%C4%B1z%C4%B1lay") and "openstreetmap.org" in opened[2]


def test_ocr_degrades_gracefully(reg, ctx, tmp_path):
    assert "Dosya yok" in reg.call("ocr", {"yol": str(tmp_path / "yok.png")}, ctx).text
    img = tmp_path / "a.png"; img.write_bytes(b"x")
    assert any(w in reg.call("ocr", {"yol": str(img)}, ctx).text for w in ("pytesseract", "Tesseract"))


def test_screenshot_saves_and_undoes(reg, ctx, monkeypatch):
    from PIL import Image, ImageGrab
    monkeypatch.setattr(ImageGrab, "grab", lambda *a, **k: Image.new("RGB", (40, 30), "black"))
    out = reg.call("ekran_goruntusu", {}, ctx).text
    path = out.split("Kaydedildi: ")[1]
    import os
    assert os.path.exists(path) and Image.open(path).size == (40, 30)
    ctx.undo.undo(); assert not os.path.exists(path)
    def nodisplay(*a, **k): raise OSError("no display")
    monkeypatch.setattr(ImageGrab, "grab", nodisplay)
    assert "alınamadı" in reg.call("ekran_goruntusu", {}, ctx).text


def test_jokes(reg, ctx):
    assert len(reg.call("saka", {}, ctx).text) > 20


# ── power: always asks ──────────────────────────────────────────────────────
def test_power_commands_exist_for_every_system():
    from importlib import util
    import pathlib
    spec = util.spec_from_file_location("g", pathlib.Path("plugins/guc_islemi.py")); g = util.module_from_spec(spec); spec.loader.exec_module(g)
    for system in ("Windows", "Darwin", "Linux"):
        for op in ("kapat", "yeniden_baslat", "uyut", "kilitle"):
            assert isinstance(g.command(op, system), list) and all(isinstance(a, str) for a in g.command(op, system)), (system, op)
    assert g.command("kapat", "Windows")[:2] == ["shutdown", "/s"] and "/t" in g.command("kapat", "Windows")        # delayed so it can be cancelled
    assert g.command("iptal", "Windows") == ["shutdown", "/a"] and g.command("iptal", "Darwin") is None and g.command("kapat", "Plan9") is None


def test_power_never_runs_without_consent(reg, tmp_path, monkeypatch):
    m = mod(reg, "guc_islemi"); ran = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **k: ran.append(cmd) or subprocess.CompletedProcess(cmd, 0, "", ""))
    asked = []
    no = Context(memory=Memory(tmp_path / "m.json"), confirm=lambda p: asked.append(p) or False)
    assert "onaylamadı" in reg.call("guc_islemi", {"islem": "kapat"}, no).text and ran == [] and "kapat" in asked[0]
    yes = Context(memory=Memory(tmp_path / "m.json"), confirm=lambda p: asked.append(p) or True)
    monkeypatch.setattr(m.platform, "system", lambda: "Linux")
    assert "gönderildi" in reg.call("guc_islemi", {"islem": "uyut"}, yes).text and ran == [["systemctl", "suspend"]]
    n = len(asked); reg.call("guc_islemi", {"islem": "iptal"}, no)
    assert len(asked) == n and ran[-1] == ["shutdown", "-c"]                                    # cancelling never needs a prompt
    monkeypatch.setattr(subprocess, "run", lambda cmd, **k: subprocess.CompletedProcess(cmd, 1, "", "izin yok"))
    assert "başarısız" in reg.call("guc_islemi", {"islem": "kilitle"}, yes).text
    monkeypatch.setattr(m.platform, "system", lambda: "Darwin")
    assert "desteklenmiyor" in reg.call("guc_islemi", {"islem": "iptal"}, yes).text


@pytest.mark.parametrize("text,expected", [
    ("youtube'da ara lofi müzik", ("youtube_ara", {"sorgu": "lofi müzik"})), ("YouTube ara: jazz", ("youtube_ara", {"sorgu": "jazz"})),
    ("haritada Kızılay göster", ("harita_ara", {"yer": "kızılay"})), ("vikipedi'de ara Ankara", ("vikipedi", {"konu": "ankara"})),
    ("sözlük: serendipity", ("sozluk", {"kelime": "serendipity"})), ("serendipity kelimesinin anlamı", ("sozluk", {"kelime": "serendipity"})),
    ("şaka yap", ("saka", {})), ("ekran görüntüsü al", ("ekran_goruntusu", {})),
    ("bilgisayarı kapat", ("guc_islemi", {"islem": "kapat"})), ("bilgisayarı yeniden başlat", ("guc_islemi", {"islem": "yeniden_baslat"})),
    ("ekranı kilitle", ("guc_islemi", {"islem": "kilitle"})), ("kapatmayı iptal et", ("guc_islemi", {"islem": "iptal"})),
])
def test_router_new_commands(text, expected):
    assert route(text) == expected


@pytest.mark.parametrize("text", ["youtube hakkında bir makale yaz", "bilgisayarım yavaş, ne yapayım", "kapatmayı unutma", "haritada ne kadar yol var", "şaka gibi bir teklif yaz"])
def test_router_does_not_overreach(text):
    assert route(text) is None


def test_attribution_files_are_present():
    from pathlib import Path
    t = Path("THIRD_PARTY.md").read_text("utf-8")
    assert "GauravSingh9356" in t and "trainer.yml" in t and "data.json" in t
    assert Path("licenses/JARVIS-GauravSingh9356-LICENSE.txt").read_text().startswith("MIT License")
    assert Path("licenses/holo-gestures-zubair-trabzada-LICENSE.txt").read_text().startswith("MIT License")
