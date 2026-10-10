"""What a tool hands back: text for the model, optionally an image for it to look at."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ToolResult:
    text: str
    image: tuple[bytes, str] | None = None   # (bytes, mime)
    source: str = ""                         # label shown to the model, e.g. "SCREEN CAPTURE"

    def __str__(self) -> str:
        return self.text


def as_result(value) -> ToolResult:
    return value if isinstance(value, ToolResult) else ToolResult(str(value if value is not None else "Done."))
