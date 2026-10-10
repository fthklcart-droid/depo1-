"""One place for every Gemini call: a model ladder with timeouts and cooldowns."""
from __future__ import annotations

import time
from typing import Callable

# Ordered by measured response time. Slow/unwell models stay at the bottom, never deleted.
LADDER = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-flash-latest",
    "gemini-3.6-flash",
]
TIMEOUT_S = 15.0

QUOTA, OUTAGE, MISSING = 300, 1800, 6 * 3600  # cooldown seconds


class AllModelsFailed(RuntimeError):
    pass


def classify(err: Exception) -> int | None:
    """Cooldown seconds for errors that mean 'try the next model'; None = real error."""
    s = f"{type(err).__name__} {err}".upper()
    if "429" in s or "RESOURCE_EXHAUSTED" in s or "QUOTA" in s:
        return QUOTA
    if any(x in s for x in ("503", "504", "UNAVAILABLE", "DEADLINE", "TIMEOUT", "TIMED OUT")):
        return OUTAGE
    if any(x in s for x in ("404", "NOT_FOUND", "403", "PERMISSION_DENIED")):
        return MISSING
    return None


class Ladder:
    def __init__(self, models: list[str] | None = None, clock: Callable[[], float] = time.monotonic):
        self.models = list(models or LADDER)
        self._cool: dict[str, float] = {}
        self._clock = clock

    def available(self) -> list[str]:
        now = self._clock()
        return [m for m in self.models if self._cool.get(m, 0) <= now]

    def call(self, fn: Callable[[str], object]):
        """fn(model) -> result. Steps down the ladder on quota/outage/missing."""
        errors = []
        for model in self.available():
            try:
                return fn(model)
            except Exception as e:  # noqa: BLE001
                cool = classify(e)
                if cool is None:
                    raise
                self._cool[model] = self._clock() + cool
                errors.append(f"{model}: {str(e)[:80]}")
        raise AllModelsFailed("No model answered. " + " | ".join(errors) if errors
                              else "Every model is cooling down.")
