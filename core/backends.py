"""Model backends. Gemini goes through the ladder; the rest are for tests/offline."""
from __future__ import annotations

import json
import os
from pathlib import Path

from core.gemini import TIMEOUT_S, Ladder

KEY_FILE = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"


def load_api_key() -> str | None:
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    try:
        return json.loads(KEY_FILE.read_text("utf-8")).get("gemini_api_key")
    except (OSError, ValueError):
        return None


def _clean_schema(s):
    """Gemini rejects some JSON-schema keys; keep the portable subset."""
    if isinstance(s, dict):
        return {k: _clean_schema(v) for k, v in s.items() if k not in {"additionalProperties", "default"}}
    return [_clean_schema(x) for x in s] if isinstance(s, list) else s


class GeminiBackend:
    def __init__(self, api_key: str, ladder: Ladder | None = None):
        from google import genai  # lazy: only needed when actually talking to Gemini
        from google.genai import types

        self._types = types
        self.client = genai.Client(api_key=api_key)
        self.ladder = ladder or Ladder()

    def _contents(self, history):
        t = self._types
        out = []
        for h in history:
            if h["role"] == "user":
                out.append(t.Content(role="user", parts=[t.Part.from_text(text=h["text"])]))
            elif h["role"] == "model":
                parts = [t.Part.from_text(text=h["text"])] if h.get("text") else []
                parts += [t.Part.from_function_call(name=c["name"], args=c["args"]) for c in h["calls"]]
                out.append(t.Content(role="model", parts=parts))
            else:
                out.append(t.Content(role="user", parts=[
                    t.Part.from_function_response(name=r["name"], response={"result": r["response"]})
                    for r in h["results"]]))
        return out

    def generate(self, system, history, tools):
        t = self._types
        decls = [t.FunctionDeclaration(name=x["name"], description=x["description"],
                                       parameters_json_schema=_clean_schema(x["parameters"])) for x in tools]
        cfg = t.GenerateContentConfig(
            system_instruction=system,
            tools=[t.Tool(function_declarations=decls)],
            automatic_function_calling=t.AutomaticFunctionCallingConfig(disable=True),
            http_options=t.HttpOptions(timeout=int(TIMEOUT_S * 1000)),
        )
        contents = self._contents(history)
        resp = self.ladder.call(lambda m: self.client.models.generate_content(
            model=m, contents=contents, config=cfg))
        text, calls = "", []
        for p in (resp.candidates[0].content.parts if resp.candidates else []) or []:
            if getattr(p, "text", None):
                text += p.text
            if getattr(p, "function_call", None):
                calls.append({"name": p.function_call.name, "args": dict(p.function_call.args or {})})
        return {"text": text, "calls": calls}


    def text(self, prompt: str) -> str:
        """One-shot completion through the ladder (summaries and similar)."""
        t = self._types
        cfg = t.GenerateContentConfig(http_options=t.HttpOptions(timeout=int(TIMEOUT_S * 1000)))
        r = self.ladder.call(lambda m: self.client.models.generate_content(model=m, contents=prompt, config=cfg))
        return (r.text or "").strip()


class ScriptedBackend:
    """Replays canned replies; used by tests."""

    def __init__(self, replies):
        self.replies = list(replies)

    def generate(self, system, history, tools):
        return self.replies.pop(0)
