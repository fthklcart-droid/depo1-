import sys
import time

import pytest

from core import store
from core.action_loader import discover
from core.context import Context
from memory.memory_manager import Memory


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DIR", tmp_path / "mem")
    return Context(memory=Memory(tmp_path / "m.json"), confirm=lambda p: True)


@pytest.fixture
def reg():
    return discover()


def mod(reg, tool):
    return sys.modules[reg.handlers[tool].__module__]


# ── doc_search ──────────────────────────────────────────────────────────────
def test_doc_search_ranks_updates_and_forgets(reg, ctx, tmp_path):
    d = tmp_path / "docs"
    d.mkdir()
    (d / "tax.md").write_text("Vergi beyannamesi için gerekli belgeler: kira geliri, makbuz, banka dökümü.")
    (d / "recipe.txt").write_text("Mercimek çorbası: mercimek, soğan, havuç, tereyağı.")
    (d / "image.png").write_bytes(b"\x89PNG")
    r = reg.call("doc_search", {"action": "index", "path": str(d)}, ctx).text
    assert "2 new" in r
    hit = reg.call("doc_search", {"action": "search", "query": "mercimek çorbası"}, ctx).text
    assert hit.splitlines()[0].endswith("recipe.txt")
    assert "tax.md" in reg.call("doc_search", {"action": "search", "query": "kira geliri vergi"}, ctx).text
    assert "1 new/changed, 1 unchanged" in (time.sleep(0.01) or (d / "tax.md").write_text("vergi iadesi") and
                                           reg.call("doc_search", {"action": "index", "path": str(d)}, ctx).text)
    (d / "recipe.txt").unlink()
    assert "1 removed" in reg.call("doc_search", {"action": "index", "path": str(d)}, ctx).text
    assert reg.call("doc_search", {"action": "search", "query": "mercimek"}, ctx).text == "No matches."
    reg.call("doc_search", {"action": "forget", "path": str(d)}, ctx)
    assert "No index" in reg.call("doc_search", {"action": "search", "query": "vergi"}, ctx).text


def test_docx_text_extraction(tmp_path):
    import zipfile
    from actions.doc_search import read_text
    f = tmp_path / "a.docx"
    with zipfile.ZipFile(f, "w") as z:
        z.writestr("word/document.xml", "<w:p><w:t>Merhaba dünya</w:t></w:p>")
    assert "Merhaba dünya" in read_text(f)


# ── calendar ────────────────────────────────────────────────────────────────
def test_calendar_conflicts_undo_and_ics(reg, ctx, tmp_path):
    c = lambda **k: reg.call("calendar", k, ctx).text  # noqa: E731
    assert "Added #1" in c(action="add", title="Toplantı", start="2030-01-10T10:00", duration_min=60)
    out = c(action="add", title="Diş", start="2030-01-10T10:30", duration_min=30)
    assert "Overlaps" in out and "Toplantı" in out
    assert "Toplantı" in c(action="list", date="2030-01-10")
    assert "end must be after" in c(action="add", title="x", start="2030-01-10T10:00", end="2030-01-10T09:00")
    assert "Could not read" in c(action="add", title="x", start="yarın")
    ics = tmp_path / "out.ics"
    c(action="export_ics", path=str(ics))
    ctx.undo.undo()                                   # removes 'Diş'
    assert "Diş" not in c(action="list", date="2030-01-10")
    c(action="delete", id=1)
    assert "Imported 2" in c(action="import_ics", path=str(ics))
    assert "Diş" in c(action="list", date="2030-01-10")


# ── finance / utilities ─────────────────────────────────────────────────────
def test_expenses_summary_and_undo(reg, ctx):
    e = lambda **k: reg.call("expenses", k, ctx).text  # noqa: E731
    e(action="add", amount=120.5, category="Market", date="2030-02-03")
    e(action="add", amount=80, category="market", date="2030-02-09")
    e(action="add", amount=50, category="ulaşım", date="2030-02-10")
    s = e(action="summary", month="2030-02")
    assert "TRY total 250.5" in s and s.index("market: 200.5") < s.index("ulaşım")
    ctx.undo.undo()
    assert "TRY total 200.5" in e(action="summary", month="2030-02")
    assert "must be a number" in e(action="add", amount="abc")


def test_utilities(reg, ctx):
    u = lambda **k: reg.call("utilities", k, ctx).text  # noqa: E731
    pw = u(action="password", length=24)
    assert len(pw) == 24 and any(c.isdigit() for c in pw) and any(c.isupper() for c in pw)
    assert u(action="hash", text="abc", algo="sha256").startswith("ba7816bf")
    assert u(action="base64_decode", text=u(action="base64_encode", text="Türkçe")) == "Türkçe"
    assert u(action="timestamp", value="0").startswith("1970-01-01")
    assert u(action="timestamp", value="1970-01-01T00:00:00+00:00") == "0"
    assert "2 matches" in u(action="regex_test", pattern=r"\d+", text="a1 b22")
    assert "Bad pattern" in u(action="regex_test", pattern="(", text="x")
    assert "Invalid JSON" in u(action="json_format", text="{")
    assert 3 <= int(u(action="random_int", low=3, high=5)) <= 5


# ── file tools ──────────────────────────────────────────────────────────────
def test_organize_dry_run_apply_and_undo(reg, ctx, tmp_path):
    for n in ("a.jpg", "b.pdf", "c.mp3", "notes.unknown"):
        (tmp_path / n).write_text("x")
    dry = reg.call("organize_folder", {"path": str(tmp_path)}, ctx).text
    assert "Would move" in dry and (tmp_path / "a.jpg").exists()
    assert "Moved 3 files" in reg.call("organize_folder", {"path": str(tmp_path), "dry_run": False}, ctx).text
    assert (tmp_path / "Images" / "a.jpg").exists() and (tmp_path / "notes.unknown").exists()
    ctx.undo.undo()
    assert (tmp_path / "a.jpg").exists() and not (tmp_path / "Images").exists()


def test_duplicates_largest_and_zip(reg, ctx, tmp_path):
    (tmp_path / "a.txt").write_text("same content")
    (tmp_path / "b.txt").write_text("same content")
    (tmp_path / "c.txt").write_text("different!!!!")
    (tmp_path / "e.txt").write_text("")
    d = reg.call("find_duplicates", {"path": str(tmp_path)}, ctx).text
    assert "1 duplicate groups" in d and "a.txt" in d and "c.txt" not in d
    assert reg.call("largest_files", {"path": str(tmp_path), "count": 1}, ctx).text.count("\n") == 0
    z = reg.call("make_zip", {"path": str(tmp_path / "a.txt")}, ctx).text
    assert "Created" in z and (tmp_path / "a.zip").exists()
    assert "Refusing" in reg.call("make_zip", {"path": str(tmp_path / "a.txt")}, ctx).text
    ctx.undo.undo()
    assert not (tmp_path / "a.zip").exists()


# ── rss / email / home assistant ────────────────────────────────────────────
def test_rss_parses_rss_and_atom():
    from actions.rss import parse
    rss = "<rss><channel><item><title>Bir</title><link>http://a</link><description>d</description></item></channel></rss>"
    atom = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>İki</title><link href="http://b"/><summary>s</summary></entry></feed>'
    assert parse(rss) == [("Bir", "http://a", "d")]
    assert parse(atom) == [("İki", "http://b", "s")]


def test_email_and_home_assistant_unconfigured(reg, ctx, monkeypatch):
    from core.config import Config
    monkeypatch.setattr(Config, "get", lambda self, k: None)
    assert "not configured" in reg.call("email", {"action": "unread"}, ctx).text
    assert "not configured" in reg.call("home_assistant", {"action": "states"}, ctx).text


def test_email_send_needs_human(reg, tmp_path, monkeypatch):
    from core.config import Config
    cfg = {"user": "a@b.c", "password": "x", "imap_host": "i", "smtp_host": "s"}
    monkeypatch.setattr(Config, "get", lambda self, k: cfg if k == "email" else None)
    no = Context(memory=Memory(tmp_path / "m.json"), confirm=lambda p: False)
    assert "declined" in reg.call("email", {"action": "send", "to": "x@y.z", "subject": "s", "body": "b"}, no).text
    assert "valid" in reg.call("email", {"action": "send", "to": "nope", "body": "b"}, no).text


def test_home_assistant_sensitive_domains_confirm(reg, tmp_path, monkeypatch):
    from core.config import Config
    m = mod(reg, "home_assistant")
    monkeypatch.setattr(Config, "get", lambda self, k: {"url": "http://h", "token": "t"} if k == "home_assistant" else None)
    calls = []
    monkeypatch.setattr(m, "_req", lambda c, path, body=None: calls.append(path) or [])
    no = Context(memory=Memory(tmp_path / "m.json"), confirm=lambda p: False)
    assert "declined" in reg.call("home_assistant", {"action": "call", "domain": "lock", "service": "unlock", "entity_id": "lock.door"}, no).text
    assert calls == []
    assert "Called light.turn_on" in reg.call("home_assistant", {"action": "call", "domain": "light", "service": "turn_on", "entity_id": "light.x"}, no).text
    assert calls == ["/services/light/turn_on"]


# ── briefing composes other skills and survives failures ────────────────────
def test_briefing_composes_and_isolates_failures(reg, ctx):
    reg.handlers["weather"] = lambda p, c: "Ankara: Güneşli, 21°C"
    reg.handlers["rss_feed"] = lambda p, c: (_ for _ in ()).throw(OSError("offline"))
    reg.call("calendar", {"action": "add", "title": "Standup", "start": time.strftime("%Y-%m-%dT23:00"), "duration_min": 15}, ctx)
    out = reg.call("daily_briefing", {}, ctx).text
    assert "Güneşli" in out and "Standup" in out and "unavailable" in out and "OSError" not in out


# ── reminders repeat / audit / thought signatures ───────────────────────────
def test_reminder_repeat_is_stored(reg, ctx, tmp_path, monkeypatch):
    m = mod(reg, "reminder")
    monkeypatch.setattr(m, "FILE", tmp_path / "r.json")
    monkeypatch.setattr(m, "_ensure", lambda c: None)
    out = reg.call("reminder", {"action": "set", "message": "su iç", "in_minutes": 5, "repeat": "daily"}, ctx).text
    assert "repeating daily" in out
    assert "(daily)" in reg.call("reminder", {"action": "list"}, ctx).text


def test_audit_log_records_calls(reg, ctx, tmp_path, monkeypatch):
    import core.action_loader as al
    monkeypatch.delenv("JARVIS_NO_AUDIT")
    monkeypatch.setattr(al, "AUDIT", tmp_path / "audit.jsonl")
    reg.call("calculate", {"expression": "1+1"}, ctx)
    reg.call("file_controller", {"action": "write", "path": str(tmp_path / "s"), "content": "SECRET"}, ctx)
    log = reg.call("audit_log", {}, ctx).text
    assert "calculate" in log and "file_controller" in log and "SECRET" not in log
    monkeypatch.setenv("JARVIS_NO_AUDIT", "1")


def test_gemini_history_keeps_raw_content_for_thought_signatures():
    from core.backends import GeminiBackend
    b = GeminiBackend.__new__(GeminiBackend)
    from google.genai import types
    b._types = types
    raw = types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(name="x", args={}), thought_signature=b"sig")])
    out = b._contents([{"role": "user", "text": "hi"}, {"role": "model", "text": "", "calls": [{"name": "x", "args": {}}], "raw": raw}])
    assert out[1] is raw and out[1].parts[0].thought_signature == b"sig"
