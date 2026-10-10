"""Microphone and speaker streams. sounddevice is imported lazily so the rest runs without it."""
from __future__ import annotations

import asyncio
import time

from core.audio_math import VIS_HOP, pcm_level, pcm_visemes
from core.live.state import EchoGuard, MicGate

SEND_RATE, RECV_RATE, CHUNK = 16000, 24000, 1024
FIRST_SOUND = CHUNK / RECV_RATE   # one callback period before the first bytes are audible
CURSOR_SLACK = 0.15
BATCH_BYTES = 9600                # ~200 ms of 24 kHz int16, so interrupt() still lands within ~200 ms


def resolve_device(name: str | None, kind: str):
    """Saved device name -> index, or None for 'system default' (also when it was unplugged)."""
    if not name:
        return None
    import sounddevice as sd
    key = "max_input_channels" if kind == "input" else "max_output_channels"
    for i, d in enumerate(sd.query_devices()):
        if d[key] > 0 and name.lower() in d["name"].lower():
            return i
    return None


def _open(factory, dev, name, ui, what):
    """Chosen hardware failing must never mean the assistant cannot hear or speak at all."""
    try:
        return factory(dev)
    except Exception as e:  # noqa: BLE001
        if dev is None:
            raise
        ui.write_log(f"SYS: {what} '{name}' unavailable ({e}) - using system default.")
        return factory(None)


async def listen(gate: MicGate, echo: EchoGuard, ui, out_queue: asyncio.Queue, wake_feed, device_name):
    import sounddevice as sd
    loop = asyncio.get_running_loop()

    def callback(indata, frames, t, status):
        level = pcm_level(indata)
        verdict = gate.route(lambda: echo.is_user_speech(level))
        if verdict == "detector":
            wake_feed(indata)
        elif verdict == "send":
            loop.call_soon_threadsafe(_put, out_queue, {"data": indata.tobytes(), "mime_type": "audio/pcm"})
            ui.set_audio_level(level)

    def factory(dev):
        return sd.InputStream(samplerate=SEND_RATE, channels=1, dtype="int16", blocksize=CHUNK,
                              device=dev, callback=callback)

    stream = _open(factory, resolve_device(device_name, "input"), device_name, ui, "Microphone")
    with stream:
        while True:
            await asyncio.sleep(0.1)


def _put(q: asyncio.Queue, item) -> None:
    try:
        q.put_nowait(item)
    except asyncio.QueueFull:
        pass  # dropping a mic block beats stalling the audio thread


async def play(gate: MicGate, echo: EchoGuard, ui, visemes, in_queue: asyncio.Queue, turn_done: asyncio.Event,
               device_name, cursor: dict):
    import numpy as np
    import sounddevice as sd

    def factory(dev):
        st = sd.RawOutputStream(samplerate=RECV_RATE, channels=1, dtype="int16", blocksize=CHUNK, device=dev)
        st.start()
        return st

    stream = _open(factory, resolve_device(device_name, "output"), device_name, ui, "Speaker")
    lat = float(getattr(stream, "latency", 0.0) or 0.0)
    if 0.0 < lat < 1.0:
        gate.out_latency = lat  # the echo tail is sized from the real device, not a guess
    try:
        while True:
            try:
                chunk = await asyncio.wait_for(in_queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                if turn_done.is_set() and in_queue.empty():
                    gate.set_speaking(False)
                    turn_done.clear()
                continue
            gate.set_speaking(True)
            ui.set_state("SPEAKING")
            batch = bytearray(chunk)
            while len(batch) < BATCH_BYTES:
                try:
                    batch.extend(in_queue.get_nowait())
                except asyncio.QueueEmpty:
                    break
            pcm = np.frombuffer(bytes(batch), dtype=np.int16)
            _drive_avatar(pcm, gate, echo, ui, visemes, cursor)
            try:
                await asyncio.to_thread(stream.write, bytes(batch))
            except (RuntimeError, asyncio.CancelledError):
                break
    finally:
        gate.set_speaking(False)
        stream.stop()
        stream.close()


def _drive_avatar(pcm, gate, echo, ui, visemes, cursor):
    """Schedule 20 ms mouth frames against when the batch will be audible - never against 'now'."""
    try:
        hop = VIS_HOP / RECV_RATE
        frames = pcm_visemes(pcm, RECV_RATE)
        now = time.time()
        if not (now <= cursor["at"] <= now + gate.out_latency + CURSOR_SLACK):
            cursor["at"] = now + FIRST_SOUND  # device drained, or drifted past what the buffer can hold
        at = cursor["at"]
        cursor["at"] += pcm.size / RECV_RATE  # advance by the batch's duration whether or not it analysed
        if frames:
            frames = visemes.frames(frames, hop) if visemes else frames
            ui.push_visemes(frames, hop, at)
            level = max(f[0] for f in frames)
        else:
            level = pcm_level(pcm)
            ui.set_audio_level(level)
        echo.note_output(level)
    except Exception:  # noqa: BLE001 - cosmetic; must never disturb playback
        pass
