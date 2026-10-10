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
            elif h["role"] == "model" and h.get("raw") is not None:
                out.append(h["raw"])  # original Content: carries thought signatures Gemini 3 requires back
            elif h["role"] == "model":
                parts = [t.Part.from_text(text=h["text"])] if h.get("text") else []
                parts += [t.Part.from_function_call(name=c["name"], args=c["args"]) for c in h["calls"]]
                out.append(t.Content(role="model", parts=parts))
            else:
                out.append(t.Content(role="user", parts=[
                    t.Part.from_function_response(name=r["name"], response={"result": r["response"]})
                    for r in h["results"]]))
        return out

    def generate(self, system, history, tools, on_token=None):
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
        raw = resp.candidates[0].content if resp.candidates else None
        for p in (raw.parts if raw is not None else []) or []:
            if getattr(p, "text", None):
                text += p.text
            if getattr(p, "function_call", None):
                calls.append({"name": p.function_call.name, "args": dict(p.function_call.args or {})})
        if on_token and text:
            on_token(text)                    # Gemini is not streamed here: one chunk, same contract
        return {"text": text, "calls": calls, "raw": raw}

    def text(self, prompt: str) -> str:
        """One-shot completion through the ladder (summaries and similar)."""
        t = self._types
        cfg = t.GenerateContentConfig(http_options=t.HttpOptions(timeout=int(TIMEOUT_S * 1000)))
        r = self.ladder.call(lambda m: self.client.models.generate_content(model=m, contents=prompt, config=cfg))
        return (r.text or "").strip()


LOOPBACK = ("localhost", "127.0.0.1", "::1")


def check_base_url(url: str) -> str:
    """https anywhere; plain http only for a server on this machine (Ollama, LM Studio, vLLM). No credentials in the URL."""
    import urllib.parse
    u = urllib.parse.urlparse((url or "").strip())
    if u.username or u.password:
        raise ValueError("base_url içinde kullanıcı adı/parola olamaz; anahtarı api_key alanına yaz.")
    if u.scheme == "https" and u.hostname:
        return url.strip().rstrip("/")
    if u.scheme == "http" and u.hostname in LOOPBACK:
        return url.strip().rstrip("/")
    raise ValueError("base_url https:// ile başlamalı (http yalnızca localhost için).")


class OpenAICompatBackend:
    """Any server that speaks the OpenAI chat-completions protocol, streamed as Server-Sent Events
    (`data: {"object":"chat.completion.chunk",...}` ... `data: [DONE]`): OpenAI, OpenRouter, Ollama, LM Studio, vLLM...
    Standard library only. The API key is sent to the configured base_url and nowhere else."""

    def __init__(self, base_url: str, api_key: str | None, models: list[str], timeout: float = 60.0):
        if not models:
            raise ValueError("llm.model gerekli.")
        self.base = check_base_url(base_url)
        self.key, self.timeout = api_key, timeout
        self.ladder = Ladder(models)

    # -- message conversion --------------------------------------------------------------
    @staticmethod
    def _messages(system, history):
        import json as _j
        msgs = [{"role": "system", "content": system}]
        for h in history:
            if h["role"] == "user":
                msgs.append({"role": "user", "content": h["text"]})
            elif h["role"] == "model":
                m = {"role": "assistant", "content": h.get("text") or None}
                if h.get("calls"):
                    m["tool_calls"] = [{"id": c.get("id") or f"call_{i}", "type": "function",
                                        "function": {"name": c["name"], "arguments": _j.dumps(c["args"], ensure_ascii=False)}}
                                       for i, c in enumerate(h["calls"])]
                msgs.append(m)
            else:
                for i, r in enumerate(h["results"]):
                    msgs.append({"role": "tool", "tool_call_id": r.get("id") or f"call_{i}", "content": str(r["response"])})
        return msgs

    # -- one request ----------------------------------------------------------------------
    def _request(self, model, messages, tools, on_token):
        import urllib.error
        import urllib.request
        body = {"model": model, "messages": messages, "stream": True}
        if tools:
            body["tools"] = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": _clean_schema(t["parameters"])}} for t in tools]
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        req = urllib.request.Request(self.base + "/chat/completions", data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            detail = e.read(300).decode("utf-8", "replace").replace(self.key or "\0", "***")
            raise RuntimeError(f"HTTP {e.code}: {detail}") from None
        except (urllib.error.URLError, OSError) as e:
            raise RuntimeError(f"timed out or unreachable: {type(e).__name__}") from None
        with resp:
            if "json" in (resp.headers.get("Content-Type") or "") and "event-stream" not in (resp.headers.get("Content-Type") or ""):
                return self._from_message(json.loads(resp.read(5_000_000))["choices"][0]["message"], on_token)
            return self._from_stream(resp, on_token)

    @staticmethod
    def _from_message(msg, on_token):
        text = msg.get("content") or ""
        if on_token and text:
            on_token(text)
        calls = [{"id": c.get("id"), "name": c["function"]["name"], "args": OpenAICompatBackend._args(c["function"].get("arguments"))} for c in msg.get("tool_calls") or []]
        return {"text": text, "calls": calls, "raw": None}

    @staticmethod
    def _args(raw):
        try:
            v = json.loads(raw) if raw else {}
            return v if isinstance(v, dict) else {}
        except ValueError:
            return {}

    @classmethod
    def _from_stream(cls, resp, on_token):
        text, calls = [], {}
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue                                   # blank separators and ": keepalive" comments
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except ValueError:
                continue
            for ch in chunk.get("choices") or []:          # a final usage chunk has no choices
                d = ch.get("delta") or {}
                if d.get("content"):
                    text.append(d["content"])
                    if on_token:
                        on_token(d["content"])
                for tc in d.get("tool_calls") or []:       # name/id arrive once, arguments arrive in fragments
                    c = calls.setdefault(tc.get("index", 0), {"id": None, "name": "", "args": ""})
                    c["id"] = tc.get("id") or c["id"]
                    f = tc.get("function") or {}
                    c["name"] += f.get("name") or ""
                    c["args"] += f.get("arguments") or ""
        out = [{"id": c["id"], "name": c["name"], "args": cls._args(c["args"])} for _, c in sorted(calls.items()) if c["name"]]
        return {"text": "".join(text), "calls": out, "raw": None}

    def generate(self, system, history, tools, on_token=None):
        messages = self._messages(system, history)
        return self.ladder.call(lambda m: self._request(m, messages, tools, on_token))

    def text(self, prompt: str) -> str:
        return self.ladder.call(lambda m: self._request(m, [{"role": "user", "content": prompt}], [], None))["text"].strip()


def make_backend(cfg):
    """Pick the model backend from config: llm.provider = gemini (default) | openai (any OpenAI-compatible server). None if not configured."""
    llm = cfg.get("llm") or {}
    provider = (llm.get("provider") or "gemini").lower()
    if provider in ("openai", "openai_compat", "ollama", "lmstudio", "openrouter", "vllm"):
        key = llm.get("api_key") or os.environ.get("SIRIUS_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        base = llm.get("base_url") or ("http://localhost:11434/v1" if provider == "ollama" else "http://localhost:1234/v1" if provider == "lmstudio" else "https://api.openai.com/v1" if provider == "openai" else "")
        models = llm.get("models") or ([llm["model"]] if llm.get("model") else [])
        local = base.startswith(("http://localhost", "http://127.0.0.1", "http://[::1]"))
        if not base or not models or (not key and not local):
            return None
        return OpenAICompatBackend(base, key, models)
    return GeminiBackend(cfg.api_key) if cfg.api_key else None


class ScriptedBackend:
    """Replays canned replies; used by tests."""

    def __init__(self, replies):
        self.replies = list(replies)

    def generate(self, system, history, tools, on_token=None):
        r = self.replies.pop(0)
        if on_token and r.get("text"):
            on_token(r["text"])
        return r
