"""Persistent memory: unlimited storage, bounded prompt, searchable on demand."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

DEFAULT_PATH = Path(__file__).with_name("long_term.json")
MAX_ENTRIES = 5000  # runaway guard, normal use never reaches it


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"\W+", text.lower()) if len(t) > 1}


class Memory:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else DEFAULT_PATH
        self.data: dict[str, dict] = {}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text("utf-8"))
            except (OSError, ValueError):
                self.data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), "utf-8")

    def remember(self, key: str, value: str, category: str = "general") -> str:
        key = re.sub(r"\s+", "_", key.strip().lower())
        if key not in self.data and len(self.data) >= MAX_ENTRIES:
            return f"Memory is full ({MAX_ENTRIES} entries); forget something first."
        self.data[key] = {"value": value, "category": category, "updated": time.time()}
        self._save()
        return f"Remembered {key}."

    def forget(self, key: str) -> str:
        key = re.sub(r"\s+", "_", key.strip().lower())
        if self.data.pop(key, None) is None:
            return f"No memory named {key}."
        self._save()
        return f"Forgot {key}."

    def recall(self, query: str, limit: int = 8) -> list[tuple[str, str]]:
        q = _tokens(query)
        scored = []
        for key, e in self.data.items():
            hay = _tokens(f"{key} {e['value']} {e['category']}")
            score = len(q & hay) + (2 if query.lower().strip() in key else 0)
            if score:
                scored.append((score, e["updated"], key, e["value"]))
        scored.sort(reverse=True)
        return [(k, v) for _, _, k, v in scored[:limit]]

    def prompt_block(self, budget: int = 1200) -> str:
        """Core facts that fit the budget + an index of keys that did not fit."""
        ordered = sorted(self.data.items(), key=lambda kv: -kv[1]["updated"])
        identity = [(k, e) for k, e in ordered if e["category"] == "identity"]
        rest = [(k, e) for k, e in ordered if e["category"] != "identity"]
        lines, used, overflow = [], 0, []
        for k, e in identity + rest:
            line = f"- {k}: {e['value']}"
            if used + len(line) <= budget:
                lines.append(line)
                used += len(line) + 1
            else:
                overflow.append((k, e["category"]))
        out = "\n".join(lines)
        if overflow:
            # interleave categories so one big category cannot crowd out the rest
            by_cat: dict[str, list[str]] = {}
            for k, c in overflow:
                by_cat.setdefault(c, []).append(k)
            keys, i = [], 0
            while len(keys) < 60 and any(by_cat.values()):
                for c in list(by_cat):
                    if by_cat[c]:
                        keys.append(by_cat[c].pop(0))
            out += "\nMore stored (use recall_memory): " + ", ".join(keys[:60])
        return out
