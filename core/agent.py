"""The agent loop: model <-> tools, with a step budget and a pluggable backend."""
from __future__ import annotations

from typing import Protocol

from core.action_loader import Registry
from core import sysprompt
from core.context import Context

MAX_STEPS = 12


class Backend(Protocol):
    def generate(self, system: str, history: list[dict], tools: list[dict]) -> dict:
        """Return {'text': str, 'calls': [{'name': str, 'args': dict}]}."""


def build_system(ctx: Context, reg: Registry, name: str = "JARVIS") -> str:
    return sysprompt.build(name, reg.declarations(), ctx.memory.prompt_block(), has_mic=False)


class Agent:
    def __init__(self, backend: Backend, reg: Registry, ctx: Context, name: str = "JARVIS"):
        self.backend, self.reg, self.ctx, self.name = backend, reg, ctx, name
        self.history: list[dict] = []

    def ask(self, text: str) -> str:
        self.history.append({"role": "user", "text": text})
        for _ in range(MAX_STEPS):
            system = build_system(self.ctx, self.reg, self.name)  # memory may have changed
            reply = self.backend.generate(system, self.history, self.reg.declarations())
            calls = reply.get("calls") or []
            self.history.append({"role": "model", "text": reply.get("text", ""), "calls": calls})
            if not calls:
                return reply.get("text", "").strip() or "(no answer)"
            results = []
            for c in calls:
                self.ctx.log(f"→ {c['name']}({c['args']})")
                out = self.reg.call(c["name"], c["args"], self.ctx).text
                self.ctx.log(f"← {out[:200]}")
                results.append({"name": c["name"], "response": out[:8000]})
            self.history.append({"role": "tool", "results": results})
        return "I ran out of steps before finishing. Tell me to continue and I will pick up from here."
