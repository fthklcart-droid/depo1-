"""Turn transcripts: cleaning and de-duplication of the chunks the API re-sends."""
from __future__ import annotations

import re

_CTRL = re.compile(r"<ctrl\d+>", re.I)
REPEAT_MIN = 12  # shorter chunks may legitimately repeat ("evet, evet")


def clean(text: str) -> str:
    return re.sub(r"[\x00-\x08\x0b-\x1f]", "", _CTRL.sub("", text)).strip()


def is_repeat(chunk: str, seen: list[str]) -> bool:
    if len(chunk) < REPEAT_MIN:
        return bool(seen) and chunk == seen[-1]
    return chunk in " ".join(seen)


class TurnBuffer:
    """Collects both sides of a turn; flush() returns what is worth logging, once."""

    def __init__(self):
        self.user: list[str] = []
        self.assistant: list[str] = []
        self._last_out = ""

    def add_user(self, raw: str) -> str:
        t = clean(raw)
        if t:
            self.user.append(t)
        return t

    def add_assistant(self, raw: str) -> str:
        """Returns the chunk if new (so the caller can feed the mouth), else ''."""
        t = clean(raw)
        if t and not is_repeat(t, self.assistant):
            self.assistant.append(t)
            return t
        return ""

    def discard(self) -> None:
        self.user, self.assistant = [], []

    def flush(self) -> tuple[str, str]:
        u, a = " ".join(self.user).strip(), " ".join(self.assistant).strip()
        self.user, self.assistant = [], []
        if u:
            self._last_out = ""  # new exchange
        if a and len(a) >= REPEAT_MIN and a in self._last_out:
            a = ""  # a tail of the previous answer re-sent after a flush
        if a:
            self._last_out = a
        return u, a
