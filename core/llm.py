"""One-shot text completion for skills (summarize, translate, generators). Uses the configured backend."""
from __future__ import annotations

_backend = None


def text(prompt: str) -> str:
    global _backend
    if _backend is None:
        from core.backends import make_backend
        from core.config import Config
        _backend = make_backend(Config())
        if _backend is None:
            raise RuntimeError("Yapay zekâ modeli ayarlı değil (config/api_keys.json -> llm ya da gemini_api_key).")
    return _backend.text(prompt)
