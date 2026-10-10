"""The only thing the engine knows about a UI. Qt, console or web: implement these and plug in."""
from __future__ import annotations

from typing import Protocol


class UI(Protocol):
    muted: bool

    def set_state(self, state: str) -> None: ...          # LISTENING | THINKING | SPEAKING | SLEEPING
    def write_log(self, line: str) -> None: ...
    def set_audio_level(self, level: float) -> None: ...
    def push_visemes(self, frames: list, hop: float, at: float) -> None: ...
    def show_content(self, title: str, body: str) -> None: ...
    def confirm(self, prompt: str) -> bool: ...


class ConsoleUI:
    """Headless default. Works over SSH and in tests; every method is safe to call."""
    muted = False

    def __init__(self):
        self._last = ""

    def set_state(self, state):
        if state != self._last:
            self._last = state
            print(f"[{state}]")

    def write_log(self, line):
        print(line)

    def set_audio_level(self, level): pass
    def push_visemes(self, frames, hop, at): pass

    def show_content(self, title, body):
        print(f"\n── {title} ──\n{body}\n")

    def confirm(self, prompt):
        from core.confirm import cli_confirm
        return cli_confirm(prompt)
