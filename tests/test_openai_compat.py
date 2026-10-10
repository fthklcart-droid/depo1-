import json
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from core import llm
from core.action_loader import discover
from core.agent import Agent
from core.backends import OpenAICompatBackend, check_base_url, make_backend
from core.config import Config
from core.context import Context
from memory.memory_manager import Memory

KEY = "sk-test-SECRET"


def chunk(delta=None, finish=None, extra=None, **kw):
    c = {"id": "x", "object": "chat.completion.chunk", "model": "m", "choices": [{"index": 0, "delta": delta or {}, "finish_reason": finish}]}
    c.update(extra or {})
    return c


def sse(*chunks, tail="data: [DONE]\n\n", crlf=False):
    body = "".join(f"data: {json.dumps(c)}\n\n" if not isinstance(c, str) else c for c in chunks) + tail
    return body.replace("\n", "\r\n") if crlf else body


class Fake:
    """An OpenAI-compatible server: replies from a queue and records every request."""
    def __init__(self):
        self.replies, self.seen = [], []
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_POST(self):
                n = int(self.headers["Content-Length"]); body = json.loads(self.rfile.read(n))
                outer.seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "accept": self.headers.get("Accept"), "body": body})
                kind, payload = outer.replies.pop(0)
                if kind == "status":
                    data = payload[1].encode(); self.send_response(payload[0])
                    self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); return
                ctype = "application/json" if kind == "json" else "text/event-stream"
                data = (json.dumps(payload) if kind == "json" else payload).encode()
                self.send_response(200); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H); self.httpd.daemon_threads = True
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}/v1"

    def stop(self): self.httpd.shutdown()


@pytest.fixture
def fake():
    f = Fake(); yield f; f.stop()


def backend(fake, models=("m1",)):
    return OpenAICompatBackend(fake.base, KEY, list(models), timeout=5)


# ── the exact stream the user pasted ────────────────────────────────────────
def test_streams_text_chunks_in_order_and_sends_correct_request(fake):
    fake.replies.append(("sse", sse(chunk({"role": "assistant", "content": ""}), chunk({"content": "Hello"}), chunk({"content": " there"}), chunk({}, "stop"),
                                    {"id": "u", "choices": [], "usage": {"total_tokens": 9}})))
    got = []
    out = backend(fake).generate("SİSTEM", [{"role": "user", "text": "selam"}], [{"name": "calculate", "description": "d", "parameters": {"type": "object", "additionalProperties": False, "properties": {}}}], on_token=got.append)
    assert got == ["Hello", " there"] and out["text"] == "Hello there" and out["calls"] == []
    r = fake.seen[0]
    assert r["path"] == "/v1/chat/completions" and r["auth"] == f"Bearer {KEY}" and r["accept"] == "text/event-stream"
    b = r["body"]
    assert b["stream"] is True and b["model"] == "m1" and b["messages"][0] == {"role": "system", "content": "SİSTEM"} and b["messages"][1] == {"role": "user", "content": "selam"}
    assert b["tools"][0] == {"type": "function", "function": {"name": "calculate", "description": "d", "parameters": {"type": "object", "properties": {}}}}   # unsupported schema key removed


def test_parser_is_robust_to_comments_crlf_garbage_and_usage_chunks(fake):
    fake.replies.append(("sse", sse(": keepalive\n\n", chunk({"content": "A"}), "data: {not json}\n\n", "event: ping\n\n", chunk({"content": "B"}), chunk({}, "stop", extra={"usage": {}}), crlf=True)))
    assert backend(fake).generate("s", [{"role": "user", "text": "x"}], [])["text"] == "AB"
    fake.replies.append(("sse", sse(chunk({"content": "tamam"}), tail="")))                       # a server that ends without [DONE]
    assert backend(fake).generate("s", [{"role": "user", "text": "x"}], [])["text"] == "tamam"


def test_tool_calls_arrive_in_fragments_and_in_parallel(fake):
    tc = lambda i, **f: {"tool_calls": [{"index": i, **f}]}   # noqa: E731
    fake.replies.append(("sse", sse(
        chunk(tc(0, id="call_a", type="function", function={"name": "calculate", "arguments": ""})),
        chunk(tc(1, id="call_b", type="function", function={"name": "datetime_info", "arguments": "{}"})),
        chunk(tc(0, function={"arguments": '{"expres'})), chunk(tc(0, function={"arguments": 'sion":"6*7"}'})), chunk({}, "tool_calls"))))
    out = backend(fake).generate("s", [{"role": "user", "text": "x"}], [])
    assert out["calls"] == [{"id": "call_a", "name": "calculate", "args": {"expression": "6*7"}}, {"id": "call_b", "name": "datetime_info", "args": {}}]
    fake.replies.append(("sse", sse(chunk({"tool_calls": [{"index": 0, "id": "c", "function": {"name": "calculate", "arguments": '{"broken'}}]}), chunk({}, "tool_calls"))))
    assert backend(fake).generate("s", [{"role": "user", "text": "x"}], [])["calls"] == [{"id": "c", "name": "calculate", "args": {}}]    # bad JSON never crashes the loop


def test_plain_json_reply_is_accepted_too(fake):
    fake.replies.append(("json", {"choices": [{"message": {"role": "assistant", "content": "düz cevap", "tool_calls": [
        {"id": "t1", "type": "function", "function": {"name": "undo", "arguments": "{}"}}]}}]}))
    got = []
    out = backend(fake).generate("s", [{"role": "user", "text": "x"}], [], on_token=got.append)
    assert out["text"] == "düz cevap" and got == ["düz cevap"] and out["calls"][0]["name"] == "undo"


# ── the agent loop over the real protocol ───────────────────────────────────
def test_agent_round_trip_sends_tool_results_back_with_matching_ids(fake, tmp_path):
    ctx = Context(memory=Memory(tmp_path / "m.json")); reg = discover()
    fake.replies.append(("sse", sse(chunk({"tool_calls": [{"index": 0, "id": "call_9", "function": {"name": "calculate", "arguments": '{"expression":"6*7"}'}}]}), chunk({}, "tool_calls"))))
    fake.replies.append(("sse", sse(chunk({"content": "Sonuç "}), chunk({"content": "42"}), chunk({}, "stop"))))
    tokens = []
    answer = Agent(backend(fake), reg, ctx).ask("6 ile 7'yi çarpar mısın", on_token=tokens.append)
    assert answer == "Sonuç 42" and tokens == ["Sonuç ", "42"]
    second = fake.seen[1]["body"]["messages"]
    asst = [m for m in second if m["role"] == "assistant"][0]
    assert asst["tool_calls"][0]["id"] == "call_9" and json.loads(asst["tool_calls"][0]["function"]["arguments"]) == {"expression": "6*7"}
    tool = [m for m in second if m["role"] == "tool"][0]
    assert tool["tool_call_id"] == "call_9" and tool["content"] == "42"


# ── failures ────────────────────────────────────────────────────────────────
def test_quota_steps_to_the_next_model_and_real_errors_do_not(fake):
    fake.replies += [("status", (429, "rate limit")), ("sse", sse(chunk({"content": "B modeli"}), chunk({}, "stop")))]
    b = backend(fake, ("m-a", "m-b"))
    assert b.generate("s", [{"role": "user", "text": "x"}], [])["text"] == "B modeli"
    assert [r["body"]["model"] for r in fake.seen] == ["m-a", "m-b"]
    fake.replies.append(("sse", sse(chunk({"content": "hâlâ B"}), chunk({}, "stop"))))
    b.generate("s", [{"role": "user", "text": "x"}], [])
    assert fake.seen[-1]["body"]["model"] == "m-b"                       # m-a is resting, not retried on every call
    fake.replies.append(("status", (400, "bad request")))
    with pytest.raises(RuntimeError, match="HTTP 400"):
        b.generate("s", [{"role": "user", "text": "x"}], [])


def test_api_key_never_leaks_into_errors(fake):
    fake.replies.append(("status", (401, f"Incorrect API key provided: {KEY}. You can find yours at ...")))
    with pytest.raises(RuntimeError) as e:
        backend(fake).generate("s", [{"role": "user", "text": "x"}], [])
    assert KEY not in str(e.value) and "***" in str(e.value)
    dead = OpenAICompatBackend("http://127.0.0.1:1/v1", KEY, ["m"], timeout=2)
    with pytest.raises(Exception) as e2:
        dead.generate("s", [{"role": "user", "text": "x"}], [])
    assert KEY not in str(e2.value)


def test_base_url_rules():
    assert check_base_url("https://openrouter.ai/api/v1/") == "https://openrouter.ai/api/v1"
    assert check_base_url("http://localhost:11434/v1") and check_base_url("http://127.0.0.1:1234/v1")
    for bad in ("http://api.example.com/v1", "ftp://x/v1", "https://user:pw@api.example.com/v1", "api.openai.com/v1", ""):
        with pytest.raises(ValueError):
            check_base_url(bad)
    with pytest.raises(ValueError):
        OpenAICompatBackend("https://x.example/v1", "k", [])


# ── configuration ───────────────────────────────────────────────────────────
def cfg(tmp_path, data, monkeypatch):
    for k in ("GEMINI_API_KEY", "OPENAI_API_KEY", "SIRIUS_LLM_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    c = Config(tmp_path / "c.json"); c.data = data; return c


def test_backend_selection(tmp_path, monkeypatch):
    mk = lambda d: make_backend(cfg(tmp_path, d, monkeypatch))   # noqa: E731
    assert mk({}) is None and mk({"llm": {"provider": "gemini"}}) is None
    assert type(mk({"gemini_api_key": "g"})).__name__ == "GeminiBackend"
    b = mk({"llm": {"provider": "openai", "api_key": "k", "model": "gpt-x"}})
    assert isinstance(b, OpenAICompatBackend) and b.base == "https://api.openai.com/v1" and b.ladder.models == ["gpt-x"]
    assert mk({"llm": {"provider": "openai", "model": "gpt-x"}}) is None                         # remote server without a key: not usable
    assert mk({"llm": {"provider": "openai", "api_key": "k"}}) is None                           # no model
    o = mk({"llm": {"provider": "ollama", "model": "llama3"}})                                   # local server: no key needed
    assert o.base == "http://localhost:11434/v1" and o.key is None
    assert mk({"llm": {"provider": "lmstudio", "model": "m"}}).base == "http://localhost:1234/v1"
    assert mk({"llm": {"provider": "openrouter", "base_url": "https://openrouter.ai/api/v1", "api_key": "k", "models": ["a", "b"]}}).ladder.models == ["a", "b"]
    c = cfg(tmp_path, {"llm": {"provider": "openai", "model": "m"}}, monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")                  # set after cfg(), which clears the environment
    assert make_backend(c).key == "from-env"
    with pytest.raises(ValueError):
        mk({"llm": {"provider": "openai", "base_url": "http://evil.example/v1", "api_key": "k", "model": "m"}})   # a key never goes over plain http


def test_plugins_use_the_configured_model(fake, monkeypatch):
    fake.replies.append(("sse", sse(chunk({"content": "teklif metni"}), chunk({}, "stop"))))
    monkeypatch.setattr(llm, "_backend", backend(fake))
    assert llm.text("bir teklif yaz") == "teklif metni"
    assert fake.seen[0]["body"]["messages"] == [{"role": "user", "content": "bir teklif yaz"}] and "tools" not in fake.seen[0]["body"]


def test_web_page_receives_tokens_as_they_arrive(fake, tmp_path, monkeypatch):
    from core.web import server as srv
    monkeypatch.setattr(srv.time, "sleep", lambda s: None)
    fake.replies.append(("sse", sse(chunk({"content": "Hello"}), chunk({"content": " there"}), chunk({}, "stop"))))
    ui = srv.WebUI(); ui.registry, ui.ctx = discover(), Context(memory=Memory(tmp_path / "m.json"))
    ui.ask = Agent(backend(fake), ui.registry, ui.ctx).ask
    q = queue.Queue(); ui._clients.append(q)
    ui._run_say("merhaba de bakalım")
    ev = []
    while not q.empty(): ev.append(q.get())
    kinds = [(e["type"], e.get("text") or e.get("state")) for e in ev if e["type"] in ("delta", "say", "state")]
    assert kinds == [("state", "THINKING"), ("delta", "Hello"), ("delta", " there"), ("say", "Hello there"), ("state", "SPEAKING"), ("state", "LISTENING")]
