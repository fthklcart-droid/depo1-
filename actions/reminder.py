"""Reminders and timers. A background thread fires them through ctx.notify; they survive restarts."""
import datetime as dt
import json
import threading
import time
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "memory" / "reminders.json"
_lock = threading.Lock()
_thread = None

EVERY = {"hourly": 3600, "daily": 86400, "weekly": 7 * 86400}

TOOL = {
    "name": "reminder",
    "description": "Set, list or cancel reminders. For 'set' give message plus EITHER in_minutes OR at (ISO local time like 2026-10-11T09:30).",
    "parameters": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["set", "list", "cancel"]},
        "message": {"type": "string"}, "in_minutes": {"type": "number"},
        "at": {"type": "string"}, "id": {"type": "integer"},
        "repeat": {"type": "string", "enum": ["hourly", "daily", "weekly"], "description": "Recur on this schedule"}}, "required": ["action"]},
}


def _load():
    try:
        return json.loads(FILE.read_text("utf-8"))
    except (OSError, ValueError):
        return []


def _save(items):
    FILE.parent.mkdir(exist_ok=True)
    FILE.write_text(json.dumps(items), "utf-8")


def _loop(ctx):
    while True:
        time.sleep(1)
        with _lock:
            items = _load()
            due = [i for i in items if i["due"] <= time.time()]
            if due:
                keep = [i for i in items if i not in due]
                for i in due:
                    step = EVERY.get(i.get("repeat"))
                    if step:   # recurring: roll forward past now, never fire a backlog
                        n = int((time.time() - i["due"]) // step) + 1
                        keep.append({**i, "due": i["due"] + n * step})
                _save(keep)
        for i in due:
            ctx.notify(f"⏰ Hatırlatma: {i['message']}")


def _ensure(ctx):
    global _thread
    if _thread is None or not _thread.is_alive():
        _thread = threading.Thread(target=_loop, args=(ctx,), daemon=True)
        _thread.start()


def run(p, ctx):
    _ensure(ctx)
    a = p["action"]
    with _lock:
        items = _load()
        if a == "set":
            if not p.get("message"):
                return "message is required"
            if p.get("in_minutes") is not None:
                due = time.time() + float(p["in_minutes"]) * 60
            elif p.get("at"):
                try:
                    due = dt.datetime.fromisoformat(p["at"]).timestamp()
                except ValueError:
                    return "Could not read 'at'; use ISO format like 2026-10-11T09:30."
            else:
                return "Give in_minutes or at."
            if due <= time.time():
                return "That time is already in the past."
            rid = max([i["id"] for i in items], default=0) + 1
            _save(items + [{"id": rid, "message": p["message"], "due": due, "repeat": p.get("repeat")}])
            return f"Reminder #{rid} set for {dt.datetime.fromtimestamp(due):%Y-%m-%d %H:%M:%S}" + (f", repeating {p['repeat']}." if p.get("repeat") else ".")
        if a == "list":
            return "\n".join(f"#{i['id']} {dt.datetime.fromtimestamp(i['due']):%m-%d %H:%M} {i['message']}{' (' + i['repeat'] + ')' if i.get('repeat') else ''}"
                             for i in sorted(items, key=lambda x: x["due"])) or "No reminders."
        left = [i for i in items if i["id"] != p.get("id")]
        _save(left)
        return "Cancelled." if len(left) != len(items) else "No reminder with that id."
