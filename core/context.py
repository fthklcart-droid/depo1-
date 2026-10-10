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
