"""config/api_keys.json with typed getters. One reader instead of a dozen get_* functions."""
from __future__ import annotations

import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"

DEFAULTS = {
    "assistant_name": "SIRIUS", "user_name": "", "voice": "Charon",
    "wake_word": False, "push_to_talk": False, "proactive_audio": True, "briefing": True,
    "input_device": None, "output_device": None, "sleep_after_s": 120,
    "live_models": ["models/gemini-3.1-flash-live-preview", "models/gemini-2.5-flash-native-audio-preview-12-2025"],
}


class Config:
    def __init__(self, path: Path | str = PATH):
        self.path = Path(path)
        self.data: dict = {}
        self.reload()

    def reload(self) -> None:
        try:
            self.data = json.loads(self.path.read_text("utf-8"))
        except (OSError, ValueError):
            self.data = {}

    def get(self, key: str):
        return self.data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value) -> None:
        self.data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=1, ensure_ascii=False), "utf-8")

    @property
    def api_key(self) -> str | None:
        import os
        return os.environ.get("GEMINI_API_KEY") or self.data.get("gemini_api_key")
