"""What to do when a Live session ends. The original 100-line except-chain, as a pure function."""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum, auto


class ReconnectSignal(Exception):
    """Raised inside the session TaskGroup to rebuild it on purpose (voice or device change)."""

    def __init__(self, keep_context: bool = True):
        super().__init__()
        self.keep_context = keep_context


def leaves(exc: BaseException):
    """Yield the real exceptions inside any (nested) ExceptionGroup."""
    if isinstance(exc, BaseExceptionGroup):
        for sub in exc.exceptions:
            yield from leaves(sub)
    else:
        yield exc


def error_text(exc: BaseException) -> str:
    """A TaskGroup's own message is just '1 sub-exception' - the cause lives in the leaves."""
    return " | ".join(f"{type(e).__name__}: {e}" for e in leaves(exc))


class Act(Enum):
    RECONNECT = auto()        # voluntary, no backoff
    FRESH = auto()            # drop the resumption handle and retry
    STEP_MODEL = auto()       # quota / no access: next rung
    DROP_TUNING = auto()
    DROP_PROACTIVE = auto()
    REKEY = auto()            # API key rejected: ask the user
    RETRY = auto()


@dataclass
class Decision:
    act: Act
    delay: float = 0.0
    keep_context: bool = True
    message: str = ""


QUOTA = ("429", "RESOURCE_EXHAUSTED", "quota")
MISSING = ("404", "NOT_FOUND", "403", "PERMISSION_DENIED")
NETWORK = ("TimeoutError", "timed out", "getaddrinfo", "ConnectionRefusedError", "OSError", "Cannot connect", "CancelledError")
SCHEMA = ("INVALID_ARGUMENT", "Unknown name", "unexpected keyword")


def decide(exc: BaseException, *, resumed: bool, tuned: bool, enhanced: bool, backoff: float) -> Decision:
    for e in leaves(exc):
        if isinstance(e, ReconnectSignal):
            return Decision(Act.RECONNECT, keep_context=e.keep_context)
    text = error_text(exc)
    low = text.lower()

    # A dead handle replayed on every retry would prevent the very reconnect it exists to protect.
    if resumed and (any(k in low for k in ("resum", "handle")) or any(k in text for k in ("INVALID_ARGUMENT", "NOT_FOUND"))):
        return Decision(Act.FRESH, message="Could not restore the conversation - starting fresh.")
    if any(k.lower() in low for k in QUOTA) or any(k in text for k in MISSING):
        return Decision(Act.STEP_MODEL)
    if tuned and (any(k in text for k in SCHEMA) or any(k in low for k in ("realtime_input", "media_resolution", "thinking"))):
        return Decision(Act.DROP_TUNING, message="Live tuning rejected - reconnecting without it.")
    if enhanced and (any(k in text for k in SCHEMA) or "proactiv" in low):
        return Decision(Act.DROP_PROACTIVE, message="Proactive audio unavailable - reconnecting without it.")
    if "API key not valid" in text or "1007" in text:
        return Decision(Act.REKEY, delay=3, message="API key invalid - please re-enter it.")
    if any(k in text for k in NETWORK):
        d = min(max(backoff, 3) * 2, 60)
        return Decision(Act.RETRY, delay=d, message=f"Connection failed - retrying in {d:.0f}s (a VPN may be required).")
    return Decision(Act.RETRY, delay=3)


class LiveLadder:
    """Live models are not drop-in replacements, so there are only a few rungs and they step on
    quota or lost access only - never on a network blip, which would walk the list into the same wall."""

    COOL = {"quota": 300, "missing": 6 * 3600}

    def __init__(self, models: list[str], clock=time.monotonic):
        self.models, self._cool, self._clock = list(models), {}, clock

    def current(self) -> str:
        now = self._clock()
        for m in self.models:
            if self._cool.get(m, 0) <= now:
                return m
        return min(self.models, key=lambda m: self._cool.get(m, 0))  # all resting: soonest to recover

    def note_failure(self, model: str, text: str) -> bool:
        kind = "quota" if any(k.lower() in text.lower() for k in QUOTA) else \
               "missing" if any(k in text for k in MISSING) else None
        if kind:
            self._cool[model] = self._clock() + self.COOL[kind]
        return kind is not None
