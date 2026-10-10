import asyncio

from core.action_loader import discover
from core.agent import Agent
from core.backends import ScriptedBackend
from core.context import Context
from core.gemini import AllModelsFailed, Ladder, classify
from core.live.policy import Act, LiveLadder, ReconnectSignal, decide
from core.live.state import EchoGuard, MicGate
from core.transcript import TurnBuffer, clean
from memory.memory_manager import Memory

import pytest


@pytest.fixture
def ctx(tmp_path):
    return Context(memory=Memory(tmp_path / "m.json"), confirm=lambda p: True)


# ── ladder ──────────────────────────────────────────────────────────────────
def test_ladder_steps_and_cools_down():
    t = [0.0]
    lad = Ladder(["a", "b", "c"], clock=lambda: t[0])
    calls = []

    def fn(m):
        calls.append(m)
        if m == "a":
            raise RuntimeError("504 DEADLINE_EXCEEDED")
        return m

    assert lad.call(fn) == "b"
    calls.clear()
    assert lad.call(fn) == "b" and calls == ["b"]   # 'a' is resting: not paid for twice
    t[0] += 1801
    calls.clear()
    lad.call(fn)
    assert calls[0] == "a"                           # believed again after its cooldown


def test_ladder_real_errors_propagate_and_exhaustion_raises():
    with pytest.raises(ValueError):
        Ladder(["a"]).call(lambda m: (_ for _ in ()).throw(ValueError("bad request")))
    with pytest.raises(AllModelsFailed):
        Ladder(["a"]).call(lambda m: (_ for _ in ()).throw(RuntimeError("429 quota")))
    assert classify(RuntimeError("404 NOT_FOUND")) > classify(RuntimeError("503"))


# ── loader / agent ──────────────────────────────────────────────────────────
def test_all_bundled_skills_load():
    reg = discover()
    assert not reg.errors
    assert {"file_controller", "calculate", "web_search", "reminder", "notes", "undo", "remember"} <= set(reg.tools)


def test_bad_plugin_is_isolated(tmp_path, ctx):
    (tmp_path / "boom.py").write_text("raise RuntimeError('x')")
    (tmp_path / "ok.py").write_text("TOOL={'name':'ok','description':'d','parameters':{'type':'object'}}\ndef run(p,c): return 'fine'")
    reg = discover([tmp_path])
    assert "boom.py" in reg.errors and reg.call("ok", {}, ctx).text == "fine"


def test_crashing_tool_does_not_raise(tmp_path, ctx):
    (tmp_path / "bad.py").write_text("TOOL={'name':'bad','description':'d','parameters':{'type':'object'}}\ndef run(p,c): 1/0")
    assert "failed" in discover([tmp_path]).call("bad", {}, ctx).text


def test_agent_tool_loop(ctx):
    reg = discover()
    be = ScriptedBackend([
        {"text": "", "calls": [{"name": "calculate", "args": {"expression": "2**10 + 1"}}]},
        {"text": "1025", "calls": []},
    ])
    assert Agent(be, reg, ctx).ask("hesapla") == "1025"


def test_agent_step_budget(ctx):
    reg = discover()
    loop = {"text": "", "calls": [{"name": "calculate", "args": {"expression": "1"}}]}
    assert "steps" in Agent(ScriptedBackend([loop] * 20), reg, ctx).ask("x")


# ── skills ──────────────────────────────────────────────────────────────────
def test_calculator_is_safe(ctx):
    reg = discover()
    assert reg.call("calculate", {"expression": "sqrt(16)*3"}, ctx).text == "12.0"
    assert "Cannot" in reg.call("calculate", {"expression": "__import__('os').system('x')"}, ctx).text
    assert "too large" in reg.call("calculate", {"expression": "9**9999"}, ctx).text


def test_files_are_undoable(tmp_path, ctx):
    reg, f = discover(), tmp_path / "a.txt"
    reg.call("file_controller", {"action": "write", "path": str(f), "content": "one"}, ctx)
    reg.call("file_controller", {"action": "write", "path": str(f), "content": "two"}, ctx)
    assert f.read_text() == "two"
    ctx.undo.undo()
    assert f.read_text() == "one"
    ctx.undo.undo()
    assert not f.exists()


def test_move_refuses_overwrite_and_undoes(tmp_path, ctx):
    reg = discover()
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_text("A"); b.write_text("B")
    assert "Refusing" in reg.call("file_controller", {"action": "move", "path": str(a), "destination": str(b)}, ctx).text
    reg.call("file_controller", {"action": "move", "path": str(a), "destination": str(tmp_path / "c")}, ctx)
    ctx.undo.undo()
    assert a.read_text() == "A"


def test_shell_needs_human_confirmation(tmp_path):
    reg = discover()
    no = Context(memory=Memory(tmp_path / "m.json"), confirm=lambda p: False)
    assert "declined" in reg.call("run_shell", {"command": "echo hi"}, no).text
    yes = Context(memory=Memory(tmp_path / "m.json"), confirm=lambda p: True)
    assert "hi" in reg.call("run_shell", {"command": "echo hi"}, yes).text


# ── memory ──────────────────────────────────────────────────────────────────
def test_memory_budget_and_index(tmp_path):
    m = Memory(tmp_path / "m.json")
    m.remember("name", "Fatih", "identity")
    for i in range(80):
        m.remember(f"pref_{i}", "likes thing number " + "x" * 30, "preferences")
    m.remember("ayse_sister", "older sister", "relationships")
    block = m.prompt_block(budget=400)
    assert "name: Fatih" in block and len(block) < 1400
    assert "ayse_sister" in block or "ayse_sister" in m.prompt_block(budget=400)
    assert m.recall("sister")[0][0] == "ayse_sister"
    assert Memory(tmp_path / "m.json").data == m.data           # persisted


# ── transcript ──────────────────────────────────────────────────────────────
def test_transcript_dedup():
    t = TurnBuffer()
    assert t.add_assistant("Merhaba, size nasıl yardımcı olabilirim?")
    assert not t.add_assistant("size nasıl yardımcı olabilirim?")     # re-sent tail
    t.add_user("selam")
    assert t.flush() == ("selam", "Merhaba, size nasıl yardımcı olabilirim?")
    t.add_assistant("nasıl yardımcı olabilirim?")                     # tail re-sent after a flush
    assert t.flush()[1] == ""
    assert clean("<ctrl46>hi\x01") == "hi"


# ── live policy ─────────────────────────────────────────────────────────────
def _group(msg):
    return BaseExceptionGroup("unhandled errors in a TaskGroup", [RuntimeError(msg)])


KW = dict(resumed=False, tuned=True, enhanced=True, backoff=3)


def test_policy_sees_through_task_groups():
    assert decide(_group("429 RESOURCE_EXHAUSTED"), **KW).act is Act.STEP_MODEL
    d = decide(BaseExceptionGroup("g", [ReconnectSignal(keep_context=False)]), **KW)
    assert d.act is Act.RECONNECT and not d.keep_context
    assert decide(_group("API key not valid"), **KW).act is Act.REKEY


def test_policy_order():
    assert decide(_group("handle expired"), **{**KW, "resumed": True}).act is Act.FRESH
    assert decide(_group("INVALID_ARGUMENT thinking"), **KW).act is Act.DROP_TUNING
    assert decide(_group("INVALID_ARGUMENT"), **{**KW, "tuned": False}).act is Act.DROP_PROACTIVE
    d = decide(_group("getaddrinfo failed"), **{**KW, "backoff": 40})
    assert d.act is Act.RETRY and d.delay == 60


def test_live_ladder_steps_only_on_quota_or_access():
    t = [0.0]
    lad = LiveLadder(["new", "old"], clock=lambda: t[0])
    assert not lad.note_failure("new", "getaddrinfo failed") and lad.current() == "new"
    assert lad.note_failure("new", "429 RESOURCE_EXHAUSTED") and lad.current() == "old"
    t[0] += 301
    assert lad.current() == "new"


# ── mic gate ────────────────────────────────────────────────────────────────
def test_gate_routing():
    t = [0.0]
    g = MicGate(wake_enabled=True, sleep_after=120, clock=lambda: t[0])
    assert g.route(lambda: True) == "detector"            # asleep: nothing leaves the machine
    g.wake()
    assert g.route(lambda: True) == "send"
    g.set_speaking(True)
    assert g.route(lambda: True) == "drop"
    g.set_speaking(False)
    assert g.route(lambda: False) == "drop"               # our own echo tail
    assert g.route(lambda: True) == "send"                # a real voice ends the tail early
    t[0] += 121
    assert g.should_autosleep() and g.sleep() and g.route(lambda: True) == "detector"


def test_gate_ptt_and_mute():
    g = MicGate()
    g.ptt_enabled = True
    assert g.route(lambda: True) == "drop"
    g.ptt(True)
    assert g.route(lambda: True) == "send"
    g.muted = True
    assert g.route(lambda: True) == "drop"


def test_echo_guard():
    e = EchoGuard()
    e.note_output(0.4)
    assert not e.is_user_speech(0.5) and e.is_user_speech(0.9)


# ── audio maths ─────────────────────────────────────────────────────────────
def test_visemes_cover_whole_block():
    np = pytest.importorskip("numpy")
    from core.audio_math import VIS_HOP, pcm_level, pcm_visemes
    t = np.arange(4800) / 24000
    tone = (3000 * np.sin(2 * np.pi * 700 * t)).astype(np.int16)    # 200 ms, open-vowel-ish
    frames = pcm_visemes(tone)
    assert len(frames) == -(-4800 // VIS_HOP) == 10               # no 20% lost off the end
    assert frames[2][1] > 0.5
    assert pcm_level(np.zeros(100, dtype=np.int16)) == 0.0 and pcm_visemes([1, 2, 3]) == []
