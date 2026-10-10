import asyncio
import types

import pytest

from core.action_loader import discover
from core.config import Config
from core.context import Context
from core.live import audio
from core.live.session import LiveSession
from memory.memory_manager import Memory


class Sess:
    async def receive(self):
        await asyncio.Event().wait()          # a quiet connection: nothing ever arrives
        yield None

    async def send_client_content(self, **k): pass
    async def send_realtime_input(self, **k): pass
    async def send_tool_response(self, **k): pass


class CM:
    async def __aenter__(self): return Sess()
    async def __aexit__(self, *a): return False


class NullUI:
    muted = False
    def __init__(self): self.lines = []
    def set_state(self, s): pass
    def write_log(self, l): self.lines.append(l)
    def set_audio_level(self, v): pass
    def push_visemes(self, *a): pass
    def show_content(self, t, b): pass
    def confirm(self, p): return False


@pytest.fixture
def session(tmp_path, monkeypatch):
    from google import genai

    class Client:
        def __init__(self, **k):
            self.aio = types.SimpleNamespace(live=types.SimpleNamespace(connect=lambda model, config: CM()))
    monkeypatch.setattr(genai, "Client", Client)

    async def idle(*a, **k):
        while True:
            await asyncio.sleep(1)
    monkeypatch.setattr(audio, "listen", idle); monkeypatch.setattr(audio, "play", idle)
    cfg = Config(tmp_path / "c.json"); cfg.data = {"gemini_api_key": "k", "briefing": False}
    ui = NullUI()
    return LiveSession(ui, discover(), Context(memory=Memory(tmp_path / "m.json")), cfg), ui


def test_cancelling_the_session_stops_it_instead_of_reconnecting(session):
    s, ui = session

    async def go():
        t = asyncio.create_task(s.run())
        for _ in range(50):
            await asyncio.sleep(0.05)
            if s.session is not None:
                break
        assert s.session is not None
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(t, 2)          # before the fix this slept 6 s and reconnected, so Ctrl+C never exited
    asyncio.run(go())
    assert not any("retrying" in l or "Connection failed" in l for l in ui.lines)


def test_a_dropped_connection_still_reconnects(session, monkeypatch):
    s, ui = session
    calls = []

    class Flaky(CM):
        async def __aenter__(self):
            calls.append(1)
            if len(calls) == 1:
                raise OSError("connection reset")
            return Sess()
    from google import genai
    monkeypatch.setattr(genai, "Client", lambda **k: types.SimpleNamespace(aio=types.SimpleNamespace(live=types.SimpleNamespace(connect=lambda model, config: Flaky()))))
    from core.live import session as sess_mod

    async def fast_sleep(d): return None
    monkeypatch.setattr(sess_mod.asyncio, "sleep", fast_sleep) if False else None

    async def go():
        t = asyncio.create_task(s.run())
        for _ in range(200):
            await asyncio.sleep(0.05)
            if len(calls) >= 2 and s.session is not None:
                break
        ok = len(calls) >= 2 and s.session is not None
        t.cancel()
        try:
            await asyncio.wait_for(t, 2)
        except BaseException:
            pass
        return ok
    assert asyncio.run(go())
