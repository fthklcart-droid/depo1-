"""One shared undo stack. Actions register how to reverse themselves."""
from __future__ import annotations

from typing import Callable


class UndoStack:
    def __init__(self, limit: int = 100):
        self._items: list[tuple[str, Callable[[], str]]] = []
        self._limit = limit

    def push(self, label: str, reverse: Callable[[], str | None]) -> None:
        self._items.append((label, reverse))
        del self._items[: -self._limit]

    def __len__(self) -> int:
        return len(self._items)

    def peek(self) -> str | None:
        return self._items[-1][0] if self._items else None

    def undo(self) -> str:
        if not self._items:
            return "Nothing to undo."
        label, reverse = self._items.pop()
        try:
            return f"Undone: {label}. {reverse() or ''}".strip()
        except Exception as e:  # reversing must never crash the session
            return f"Could not undo '{label}': {e}"
