"""remember / recall_memory / forget / undo — the model's handles on memory and the undo stack."""

CATS = "identity | preferences | projects | relationships | wishes | notes"


def remember(p, ctx):
    return ctx.memory.remember(p["key"], p["value"], p.get("category", "notes"))


def recall(p, ctx):
    hits = ctx.memory.recall(p.get("query", ""), 8) if p.get("query") else \
        [(k, e["value"]) for k, e in ctx.memory.data.items()][:30]
    return "\n".join(f"{k}: {v}" for k, v in hits) or "Nothing stored about that."


def forget(p, ctx):
    return ctx.memory.forget(p["key"])


def undo(p, ctx):
    if str(p.get("action", "")).lower() == "list":
        return f"Next undo: {ctx.undo.peek()} ({len(ctx.undo)} stored)" if len(ctx.undo) else "Nothing to undo."
    return ctx.undo.undo()


def _s(props, req):
    return {"type": "object", "properties": props, "required": req}


S = {"type": "string"}
TOOLS = [
    ({"name": "remember", "description": "Silently save a durable fact about the user (name, city, preferences, projects, relationships). Not for one-time commands. Category: " + CATS,
      "parameters": _s({"key": S, "value": S, "category": S}, ["key", "value"])}, remember),
    ({"name": "recall_memory", "description": "Look up stored facts, especially keys listed under 'More stored' in your prompt. Empty query lists everything.",
      "parameters": _s({"query": S}, [])}, recall),
    ({"name": "forget", "description": "Delete one stored fact by key.", "parameters": _s({"key": S}, ["key"])}, forget),
    ({"name": "undo", "description": "Reverse YOUR last file or setting change. Use when the user says undo/revert/take it back, in any language. action='list' shows what can be undone.",
      "parameters": _s({"action": S}, [])}, undo),
]
