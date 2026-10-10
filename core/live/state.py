"""The mic gate and wake state machine, free of audio devices so it can be tested."""
from __future__ import annotations

import threading
import time
from typing import Callable

TAIL_MARGIN = 0.25  # extra time after the device's own latency before the mic is trusted again


class MicGate:
    """Decides, for every mic block, whether it goes to the wake detector, the model, or nowhere."""

    def __init__(self, wake_enabled=False, sleep_after=120.0, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self.wake_enabled = wake_enabled
        self.awake = not wake_enabled
        self.sleep_after = sleep_after
        self.speaking = False
        self.muted = False
        self.phone_active = False
        self.ptt_enabled = False
        self.ptt_held = False
        self.out_latency = 0.20
        self.tail_until = 0.0
        self.last_user_speech = clock()

    def set_speaking(self, value: bool) -> None:
        with self._lock:
            self.speaking = value
            # speakers are still sounding for a moment after the flag drops
            self.tail_until = 0.0 if value else self._clock() + self.out_latency + TAIL_MARGIN

    def is_speaking(self) -> bool:
        with self._lock:
            return self.speaking

    def tail_active(self) -> bool:
        return self._clock() < self.tail_until

    def wake(self) -> bool:
        if self.awake:
            return False
        self.awake, self.last_user_speech = True, self._clock()
        return True

    def sleep(self) -> bool:
        if not self.awake:
            return False
        self.awake = False
        self.set_speaking(False)
        return True

    def should_autosleep(self) -> bool:
        return (self.wake_enabled and self.awake and not self.is_speaking()
                and self._clock() - self.last_user_speech > self.sleep_after)

    def touch(self) -> None:
        self.last_user_speech = self._clock()

    def ptt(self, held: bool) -> None:
        self.ptt_held = held
        if held:
            self.wake()  # holding the key is also a way to wake it

    def route(self, is_user_voice: Callable[[], bool]) -> str:
        """'detector' | 'drop' | 'send'. is_user_voice is only evaluated while the echo tail is live."""
        if self.wake_enabled and not self.awake:
            return "detector"          # nothing leaves the machine while asleep
        if self.is_speaking():
            return "drop"
        if self.tail_active():
            try:
                if not is_user_voice():
                    return "drop"      # our own voice, still sounding in the room
            except Exception:  # noqa: BLE001
                return "drop"
            self.tail_until = 0.0      # a real voice ends the tail early
        if self.ptt_enabled and not self.ptt_held:
            return "drop"
        if self.muted or self.phone_active:
            return "drop"
        return "send"


class EchoGuard:
    """Is this mic block the user, or the speakers? Compares with what we are playing right now."""

    def __init__(self, ratio: float = 1.8, floor: float = 0.08):
        self.ratio, self.floor, self._out, self._at = ratio, floor, 0.0, 0.0

    def note_output(self, level: float) -> None:
        self._out, self._at = max(level, self._out * 0.9), time.monotonic()

    def is_user_speech(self, level: float) -> bool:
        decayed = self._out * (0.5 ** ((time.monotonic() - self._at) / 0.25))
        return level > self.floor and level > decayed * self.ratio

    def reset(self) -> None:
        self._out = 0.0
