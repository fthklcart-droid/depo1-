"""Tiny JSON file store shared by the skills that keep data (calendar, expenses...)."""
from __future__ import annotations

import json
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent / "memory"


def load(name: str, default):
    try:
        return json.loads((DIR / name).read_text("utf-8"))
    except (OSError, ValueError):
        return default


def save(name: str, data) -> None:
    DIR.mkdir(exist_ok=True)
    tmp = DIR / (name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(DIR / name)  # atomic: a crash mid-write cannot corrupt the store
