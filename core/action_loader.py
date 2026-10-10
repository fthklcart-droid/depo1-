"""Discovers self-describing skills: any module in actions/ or plugins/ with TOOL + run()."""
from __future__ import annotations

import importlib.util
import json
import os
import time
import sys
import traceback
from pathlib import Path

from core.result import ToolResult, as_result

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "memory" / "audit.jsonl"
AUDIT_MAX = 1_000_000


def audit(tool: str, params: dict, ok: bool) -> None:
    """One line per tool call, so you can always see what the assistant did on your machine."""
    if os.environ.get("JARVIS_NO_AUDIT"):
        return
    try:
        AUDIT.parent.mkdir(exist_ok=True)
        if AUDIT.exists() and AUDIT.stat().st_size > AUDIT_MAX:
            AUDIT.replace(AUDIT.with_suffix(".old"))
        short = {k: (str(v)[:120]) for k, v in (params or {}).items() if k not in ("content", "password", "body")}
        with open(AUDIT, "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": int(time.time()), "tool": tool, "args": short, "ok": ok}, ensure_ascii=False) + "\n")
    except OSError:
        pass  # auditing must never break a tool


class Registry:
    def __init__(self):
        self.tools: dict[str, dict] = {}
        self.handlers: dict = {}
        self.errors: dict[str, str] = {}

    def declarations(self) -> list[dict]:
        return list(self.tools.values())

    def call(self, name: str, params: dict, ctx) -> ToolResult:
        h = self.handlers.get(name)
        if h is None:
            return ToolResult(f"Unknown tool '{name}'. Available: {', '.join(sorted(self.tools))}")
        ctx.registry = self
        try:
            out = as_result(h(params or {}, ctx))
            audit(name, params, True)
            return out
        except Exception as e:  # a crashing skill must never take the session down
            ctx.log(traceback.format_exc())
            audit(name, params, False)
            return ToolResult(f"Tool '{name}' failed: {type(e).__name__}: {e}")


def _load_file(path: Path, reg: Registry) -> None:
    mod_name = f"_jarvis_{path.parent.name}_{path.stem}"
    try:
        spec = importlib.util.spec_from_file_location(mod_name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
        tools = getattr(mod, "TOOLS", None) or [(mod.TOOL, mod.run)]
        for tool, handler in tools:
            if not {"name", "description", "parameters"} <= tool.keys():
                raise ValueError(f"TOOL for {tool.get('name')} missing keys")
            if tool["name"] in reg.tools:
                raise ValueError(f"duplicate tool name {tool['name']}")
            reg.tools[tool["name"]] = tool
            reg.handlers[tool["name"]] = handler
    except Exception as e:  # noqa: BLE001
        reg.errors[path.name] = f"{type(e).__name__}: {e}"


def discover(dirs: list[Path] | None = None) -> Registry:
    reg = Registry()
    for d in dirs or [ROOT / "actions", ROOT / "plugins"]:
        for path in sorted(d.glob("*.py")):
            if not path.name.startswith("_"):
                _load_file(path, reg)
    return reg
