"""Current time anywhere, and date arithmetic."""
import datetime as dt
from zoneinfo import ZoneInfo

TOOL = {
    "name": "datetime_info",
    "description": "Current date/time (optionally in an IANA timezone like Europe/Istanbul), or days between two ISO dates (date_a, date_b).",
    "parameters": {"type": "object", "properties": {"timezone": {"type": "string"}, "date_a": {"type": "string"},
                                                      "date_b": {"type": "string"}}},
}


def run(p, ctx):
    if p.get("date_a"):
        a = dt.date.fromisoformat(p["date_a"])
        b = dt.date.fromisoformat(p["date_b"]) if p.get("date_b") else dt.date.today()
        return f"{(b - a).days} days from {a} to {b}"
    try:
        now = dt.datetime.now(ZoneInfo(p["timezone"])) if p.get("timezone") else dt.datetime.now().astimezone()
    except Exception:  # noqa: BLE001
        return f"Unknown timezone {p.get('timezone')}"
    return now.strftime("%A, %d %B %Y, %H:%M:%S %Z")
