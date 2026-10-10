"""One call that gathers the day: date, weather, calendar, to-dos, reminders and headlines."""
import datetime as dt

TOOL = {
    "name": "daily_briefing",
    "description": "Build the user's briefing for today: date, weather, calendar events, open to-dos, reminders and top headlines. Call for 'good morning', 'what's my day', 'brief me'.",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}, "news": {"type": "boolean", "description": "Include headlines (default true)"}}},
}


def _section(title, text):
    return f"## {title}\n{text.strip()}" if text and text.strip() else ""


def run(p, ctx):
    parts = [f"# Briefing — {dt.datetime.now():%A, %d %B %Y %H:%M}"]
    kw = {"city": p["city"]} if p.get("city") else {}
    for title, fn in (
        ("Weather", lambda: ctx.call("weather", **kw)),
        ("Calendar today", lambda: ctx.call("calendar", action="today")),
        ("Next 3 days", lambda: ctx.call("calendar", action="upcoming", days=3)),
        ("To-dos", lambda: "\n".join(l for l in ctx.call("notes", action="list", kind="todo").splitlines() if "[ ]" in l)),
        ("Reminders", lambda: ctx.call("reminder", action="list")),
        ("Headlines", lambda: ctx.call("rss_feed", feed="world", limit=5) if p.get("news", True) else ""),
    ):
        try:
            out = fn()
        except Exception as e:  # noqa: BLE001 - a dead network must not spoil the rest of the briefing
            out = f"(unavailable: {type(e).__name__})"
        if out.startswith("Tool '") and " failed" in out[:60]:
            out = "(unavailable right now)"
        if out and out not in ("Nothing scheduled.", "Nothing coming up.", "No reminders.", "Empty.", "Unknown tool"):
            parts.append(_section(title, out))
    return "\n\n".join(x for x in parts if x)
