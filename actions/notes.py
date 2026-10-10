"""Notes and to-dos stored locally in memory/notes.json."""
import json
import time
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "memory" / "notes.json"

TOOL = {
    "name": "notes",
    "description": "Notes and to-do list. add (kind=note|todo), list, search, done (todo id), delete (id).",
    "parameters": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["add", "list", "search", "done", "delete"]},
        "text": {"type": "string"}, "kind": {"type": "string", "enum": ["note", "todo"]},
        "id": {"type": "integer"}}, "required": ["action"]},
}


def _load():
    try:
        return json.loads(FILE.read_text("utf-8"))
    except (OSError, ValueError):
        return []


def _save(items):
    FILE.parent.mkdir(exist_ok=True)
    FILE.write_text(json.dumps(items, ensure_ascii=False, indent=1), "utf-8")


def _fmt(i):
    box = "" if i["kind"] == "note" else ("[x] " if i["done"] else "[ ] ")
    return f"#{i['id']} {box}{i['text']}"


def run(p, ctx):
    items, a = _load(), p["action"]
    if a == "add":
        if not p.get("text"):
            return "text is required"
        item = {"id": max([i["id"] for i in items], default=0) + 1, "text": p["text"],
                "kind": p.get("kind", "note"), "done": False, "created": time.time()}
        _save(items + [item])
        ctx.undo.push(f"add {item['kind']} #{item['id']}",
                      lambda: (_save([i for i in _load() if i["id"] != item["id"]]), "Removed.")[1])
        return f"Saved {_fmt(item)}"
    if a == "list":
        return "\n".join(_fmt(i) for i in items if p.get("kind") in (None, i["kind"])) or "Empty."
    if a == "search":
        q = p.get("text", "").lower()
        return "\n".join(_fmt(i) for i in items if q in i["text"].lower()) or "No matches."
    hit = next((i for i in items if i["id"] == p.get("id")), None)
    if not hit:
        return "No item with that id."
    if a == "done":
        hit["done"] = True
        _save(items)
        return f"Done: {_fmt(hit)}"
    _save([i for i in items if i is not hit])
    ctx.undo.push(f"delete note #{hit['id']}", lambda: (_save(_load() + [hit]), "Restored.")[1])
    return f"Deleted #{hit['id']}"
