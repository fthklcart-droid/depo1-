"""The Gemini Live engine. Orchestrates the pieces; contains no signal maths, no policy, no UI code."""
from __future__ import annotations

import asyncio
import base64
import traceback

from core import sysprompt
from core.action_loader import Registry
from core.config import Config
from core.context import Context
from core.live import audio
from core.live.policy import Act, LiveLadder, ReconnectSignal, decide, error_text
from core.live.state import EchoGuard, MicGate
from core.transcript import TurnBuffer
from core.ui import UI

SLICE = 2400  # 50 ms of 24 kHz int16, so interrupt() stops audio within 50 ms


class LiveSession:
    def __init__(self, ui: UI, registry: Registry, ctx: Context, config: Config, visemes=None):
        self.ui, self.registry, self.ctx, self.cfg, self.visemes = ui, registry, ctx, config, visemes
        self.gate = MicGate(bool(config.get("wake_word")), float(config.get("sleep_after_s")))
        self.gate.ptt_enabled = bool(config.get("push_to_talk"))
        self.echo = EchoGuard()
        self.ladder = LiveLadder(config.get("live_models"))
        self.turns = TurnBuffer()
        self.history: list[str] = []          # for the end-of-session summary
        self.wake_detector = None             # optional, set by whoever owns the wake-word engine
        self._resume: str | None = None       # RAM only: persisting it would stop summaries ever being written
        self._tuned = True
        self._enhanced = bool(config.get("proactive_audio"))
        self._backoff = 3.0
        self._cursor = {"at": 0.0}
        self._interrupted = False
        self._quit = False
        # per-connection state, rebuilt on every connect
        self.session = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._audio_in: asyncio.Queue | None = None
        self._out: asyncio.Queue | None = None
        self._turn_done: asyncio.Event | None = None
        self._reconnect: asyncio.Event | None = None
        self._reconnect_keep = True
        self._pending_media: list[tuple] = []
        self.ctx.shutdown = self._request_quit

    # ── thread-safe entry points (UI / hotkey / dashboard threads) ───────────────
    def _submit(self, coro_fn):
        if self._loop and self.session:
            asyncio.run_coroutine_threadsafe(coro_fn(), self._loop)

    def send_text(self, text: str) -> None:
        if self.gate.wake_enabled and not self.gate.awake:
            self.ui.write_log("SYS: I'm asleep - say 'Hey Jarvis' first.")
            return
        self._say(text)

    def _say(self, text: str) -> None:
        async def go():
            await self.session.send_client_content(
                turns={"role": "user", "parts": [{"text": text}]}, turn_complete=True)
        self._submit(go)

    def interrupt(self) -> None:
        self._interrupted = True
        q, drained = self._audio_in, 0
        while q is not None and not q.empty():
            try:
                q.get_nowait()
                drained += 1
            except asyncio.QueueEmpty:
                break
        self.gate.set_speaking(False)
        if self.visemes:
            self.visemes.reset()
        self._cursor["at"] = 0.0
        if self._turn_done:
            self._turn_done.clear()
        self.ui.write_log("SYS: Interrupted - listening...")

    def request_reconnect(self, keep_context: bool = True, reason: str = "") -> None:
        self._reconnect_keep = keep_context
        self._reconnect_reason = reason
        if self._loop and self._reconnect is not None:
            self._loop.call_soon_threadsafe(self._reconnect.set)

    def on_voice_change(self) -> None:      # the voice is baked in at connect; resuming would restore the old one
        self.request_reconnect(keep_context=False, reason="new voice")

    def on_audio_device_change(self) -> None:
        self.request_reconnect(keep_context=True, reason="audio device")

    def _request_quit(self) -> None:
        self._quit = True

    # ── config ───────────────────────────────────────────────────────────────────
    def _tools(self) -> list[dict]:
        return self.registry.declarations()

    def build_config(self):
        from google.genai import types
        cfg = self.cfg
        system = sysprompt.build(cfg.get("assistant_name"), self._tools(), self.ctx.memory.prompt_block(),
                                 has_mic=True, user_name=cfg.get("user_name") or "")
        live = dict(
            response_modalities=["AUDIO"], output_audio_transcription={}, input_audio_transcription={},
            system_instruction=system,
            tools=[{"function_declarations": [self._declaration(t) for t in self._tools()]}],
            session_resumption=types.SessionResumptionConfig(handle=self._resume),
            context_window_compression=types.ContextWindowCompressionConfig(sliding_window=types.SlidingWindow()),
            speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=cfg.get("voice")))),
        )
        if self._enhanced:
            live["proactivity"] = types.ProactivityConfig(proactive_audio=True)
        if self._tuned:
            live["media_resolution"] = types.MediaResolution.MEDIA_RESOLUTION_MEDIUM
        return types.LiveConnectConfig(**live)

    @staticmethod
    def _declaration(tool: dict) -> dict:
        def up(s):  # Live wants upper-case JSON-schema types
            if isinstance(s, dict):
                return {k: (v.upper() if k == "type" and isinstance(v, str) else up(v)) for k, v in s.items()
                        if k not in ("additionalProperties", "default")}
            return [up(x) for x in s] if isinstance(s, list) else s
        return {**tool, "parameters": up(tool["parameters"])}

    # ── tool dispatch ────────────────────────────────────────────────────────────
    async def _dispatch(self, fc):
        from google.genai import types
        args = dict(fc.args or {})
        self.ui.set_state("THINKING")
        self.ui.write_log(f"-> {fc.name}")
        result = await asyncio.to_thread(self.registry.call, fc.name, args, self.ctx)
        if result.image:
            self._pending_media.append((result.image, result.source or "IMAGE", args.get("text", "")))
        if fc.name == "web_search" and result.text and not result.text.startswith("No results"):
            self.ui.show_content(f"SEARCH - {args.get('query', '')[:38]}", result.text)
        if not self.ui.muted:
            self.ui.set_state("LISTENING")
        return types.FunctionResponse(id=fc.id, name=fc.name, response={"result": result.text})

    async def _flush_media(self) -> None:
        """Attach a captured frame right behind its tool response: one answer, no improvised first one."""
        while self._pending_media and self.session:
            (data, mime), source, question = self._pending_media.pop(0)
            await self.session.send_client_content(turns={"role": "user", "parts": [
                {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode("ascii")}},
                {"text": f"[IMAGE SOURCE: {source}]\n\n{question}"}]}, turn_complete=True)

    # ── receive ──────────────────────────────────────────────────────────────────
    async def _receive(self) -> None:
        while True:
            async for r in self.session.receive():
                self._capture_handle(r)
                if r.data and not self._interrupted:
                    self._turn_done.clear()
                    for i in range(0, len(r.data), SLICE):
                        self._audio_in.put_nowait(r.data[i:i + SLICE])
                if r.server_content:
                    self._on_content(r.server_content)
                if r.tool_call:
                    responses = [await self._dispatch(fc) for fc in r.tool_call.function_calls]
                    await self.session.send_tool_response(function_responses=responses)
                    await self._flush_media()
                    if self._quit:
                        await self._goodbye()
                        raise ReconnectSignal()   # unwinds the TaskGroup; run() sees _quit and stops

    def _capture_handle(self, r) -> None:
        u = getattr(r, "session_resumption_update", None)
        if u is not None and getattr(u, "resumable", False) and getattr(u, "new_handle", None):
            self._resume = u.new_handle   # only resumable handles: replaying one from mid-turn is what the flag prevents

    def _on_content(self, sc) -> None:
        if sc.output_transcription and sc.output_transcription.text:
            fresh = self.turns.add_assistant(sc.output_transcription.text)
            if fresh and self.visemes:
                self.visemes.feed_text(fresh)
        if sc.input_transcription and sc.input_transcription.text:
            if self.turns.add_user(sc.input_transcription.text):
                self.gate.touch()
        if sc.turn_complete:
            self._turn_done.set()
            if self._interrupted:
                self._interrupted = False
                self.turns.discard()
                if self.visemes:
                    self.visemes.reset()
                return
            user, bot = self.turns.flush()
            name = self.cfg.get("assistant_name")
            if user:
                self.ui.write_log(f"You: {user}")
                self.history.append(f"User: {user}")
            if bot:
                self.ui.write_log(f"{name}: {bot}")
                self.history.append(f"{name}: {bot}")

    async def _goodbye(self) -> None:
        self._say("Say a brief natural goodbye to the user.")
        await asyncio.sleep(2.5)

    # ── background ───────────────────────────────────────────────────────────────
    async def _relay(self) -> None:
        while True:
            msg = await self._out.get()
            from google.genai import types
            await self.session.send_realtime_input(
                audio=types.Blob(data=msg["data"], mime_type=msg.get("mime_type", "audio/pcm")))

    async def _watch_reconnect(self) -> None:
        await self._reconnect.wait()
        self._reconnect.clear()
        self.ui.write_log(f"SYS: Applying {getattr(self, '_reconnect_reason', '') or 'settings'} - reconnecting...")
        raise ReconnectSignal(self._reconnect_keep)

    async def _watch_sleep(self) -> None:
        while True:
            await asyncio.sleep(5)
            if self.gate.should_autosleep() and self.gate.sleep():
                self.ui.set_state("SLEEPING")
                self.ui.write_log("SYS: Sleeping - say 'Hey Jarvis' to wake me.")

    def wake(self, reason: str = "wake word") -> None:
        if self.gate.wake():
            self.ui.set_state("LISTENING")
            self.ui.write_log(f"SYS: Awake - {reason}.")

    async def _briefing(self) -> None:
        mem = self.ctx.memory
        name = (mem.recall("name") or [("", "")])[0][1]
        await asyncio.sleep(0.3)
        self._say("Greet the user warmly in one or two short sentences and mention the time."
                  + (f" Address them as {name}." if name else "") + " Do not call tools.")

    # ── lifecycle ────────────────────────────────────────────────────────────────
    async def run(self) -> None:
        from google import genai
        self._loop = asyncio.get_running_loop()
        self._reconnect = asyncio.Event()
        briefed = False
        while not self._quit:
            model, resumed = self.ladder.current(), self._resume is not None
            try:
                self.ui.set_state("THINKING")
                client = genai.Client(api_key=self.cfg.api_key,
                                      http_options={"api_version": "v1alpha" if self._enhanced else "v1beta"})
                async with client.aio.live.connect(model=model, config=self.build_config()) as session, \
                        asyncio.TaskGroup() as tg:
                    self._open(session)
                    if resumed:
                        self.ui.write_log("SYS: Reconnected - conversation restored.")
                    self._backoff = 3.0
                    tg.create_task(self._watch_reconnect())
                    tg.create_task(self._relay())
                    tg.create_task(audio.listen(self.gate, self.echo, self.ui, self._out,
                                                self._feed_wake, self.cfg.get("input_device")))
                    tg.create_task(self._receive())
                    tg.create_task(audio.play(self.gate, self.echo, self.ui, self.visemes, self._audio_in,
                                              self._turn_done, self.cfg.get("output_device"), self._cursor))
                    tg.create_task(self._watch_sleep())
                    if not briefed and self.cfg.get("briefing") and self.gate.awake:
                        briefed = True
                        tg.create_task(self._briefing())
                if self._quit:
                    return
            except (KeyboardInterrupt, SystemExit):
                raise
            except BaseException as e:  # noqa: BLE001 - TaskGroup raises BaseExceptionGroup
                if not await self._recover(e, model, resumed):
                    return
            finally:
                self.session = None
        self.ui.write_log("SYS: Goodbye.")

    def _open(self, session) -> None:
        self.session = session
        self._audio_in = asyncio.Queue()
        self._out = asyncio.Queue(maxsize=200)
        self._turn_done = asyncio.Event()
        self._reconnect.clear()
        self._pending_media.clear()
        self._interrupted = False
        if self.gate.wake_enabled:
            self.gate.awake = False
            self.ui.set_state("SLEEPING")
            self.ui.write_log("SYS: Online - sleeping. Say 'Hey Jarvis' to wake me.")
        else:
            self.gate.awake = True
            self.ui.set_state("LISTENING")
            self.ui.write_log("SYS: Online.")

    def _feed_wake(self, block) -> None:
        if self.wake_detector is not None:
            self.wake_detector.feed(block)

    async def _recover(self, exc: BaseException, model: str, resumed: bool) -> bool:
        """Apply policy.decide(). Returns False when the loop should stop."""
        if self._quit:
            return False
        d = decide(exc, resumed=resumed, tuned=self._tuned, enhanced=self._enhanced, backoff=self._backoff)
        if d.act is not Act.RECONNECT:
            self.ctx.log(traceback.format_exc())
            self.ui.write_log(f"ERR: {error_text(exc)[:200]}")
        if d.message:
            self.ui.write_log(f"SYS: {d.message}")
        if d.act is Act.RECONNECT and not d.keep_context:
            self._resume = None
        elif d.act is Act.FRESH:
            self._resume = None
        elif d.act is Act.STEP_MODEL:
            self.ladder.note_failure(model, error_text(exc))
            nxt = self.ladder.current()
            self.ui.write_log(f"SYS: Switching to {nxt.split('/')[-1]}." if nxt != model
                              else "SYS: Every live model is resting - retrying.")
            d.delay = 0 if nxt != model else 15
        elif d.act is Act.DROP_TUNING:
            self._tuned = False
        elif d.act is Act.DROP_PROACTIVE:
            self._enhanced = False
        self._backoff = d.delay or 3.0
        self.gate.set_speaking(False)
        if d.act not in (Act.RECONNECT, Act.FRESH, Act.DROP_TUNING, Act.DROP_PROACTIVE):
            self.ui.set_state("SLEEPING")
        if d.delay:
            await asyncio.sleep(d.delay)
        return True
