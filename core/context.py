"""Shared runtime context handed to every action."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from core.undo import UndoStack
from memory.memory_manager import Memory


@dataclass
class Context:
    memory: Memory
    undo: UndoStack = field(default_factory=UndoStack)
    # Asked by the *interface*, never by the model: returns True only if the human agrees.
    confirm: Callable[[str], bool] = lambda prompt: False
    notify: Callable[[str], None] = print
    log: Callable[[str], None] = lambda msg: None
    shutdown: Callable[[], None] = lambda: None
    holo_url: str = ""      # set by the web UI: where the hand-gesture deck lives
    registry: object = None   # set by Registry.call, so one skill can compose others

    def call(self, tool: str, **params) -> str:
        """Run another skill and get its text. Lets a briefing reuse calendar, weather and notes."""
        return self.registry.call(tool, params, self).text if self.registry else "(no registry)"
