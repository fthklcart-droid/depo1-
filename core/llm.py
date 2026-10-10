"""One-shot text completion for skills (summarize, translate). Goes through the model ladder."""
from __future__ import annotations

_backend = None


def text(prompt: str) -> str:
    global _backend
    from core.backends import GeminiBackend, load_api_key
    if _backend is None:
        key = load_api_key()
        if not key:
            raise RuntimeError("No Gemini API key configured.")
        _backend = GeminiBackend(key)
    return _backend.text(prompt)
