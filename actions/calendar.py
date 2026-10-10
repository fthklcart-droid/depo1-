"""A local calendar with conflict detection and .ics import/export."""
import datetime as dt
import re

from core import store

FILE = "calendar.json"
TOOL = {
    "name": "calendar",
    "description": "The user's calendar. add (title, start ISO like 2026-10-12T14:00, optional end/duration_min/location), today, upcoming (days), list (date), delete (id), export_ics (path), import_ics (path). Warns about overlaps.",
    "parameters": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["add", "today", "upcoming", "list", "delete", "export_ics", "import_ics"]},
        "title": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"},
        "duration_min": {"type": "integer"}, "location": {"type": "string"}, "date": {"type": "string"},
        "days": {"type": "integer"}, "id": {"type": "integer"}, "path": {"type": "string"}}, "required": ["action"]},
}


def _p(s):
    return dt.datetime.fromisoformat(s)


def _fmt(e):
    s, en = _p(e["start"]), _p(e["end"])
    loc = f" @ {e['location']}" if e.get("location") else ""
    return f"#{e['id']} {s:%a %d %b %H:%M}–{en:%H:%M} {e['title']}{loc}"


def _between(events, a, b):
    return sorted((e for e in events if a <= _p(e["start"]) < b), key=lambda e: e["start"])


def _ics_dt(s):
    return _p(s).strftime("%Y%m%dT%H%M%S")


def _parse_ics(text):
    out = []
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text.replace("\r\n ", ""), re.S):
        f = dict(re.findall(r"^([A-Z]+)[^:\n]*:(.*)$", block, re.M))
        def conv(v):
            v = v.strip().rstrip("Z")
            return dt.datetime.strptime(v[:15], "%Y%m%dT%H%M%S") if "T" in v else dt.datetime.strptime(v[:8], "%Y%m%d")
        if "DTSTART" in f:
            s = conv(f["DTSTART"])
            e = conv(f["DTEND"]) if "DTEND" in f else s + dt.timedelta(hours=1)
            out.append({"title": f.get("SUMMARY", "(no title)").strip(), "start": s.isoformat(), "end": e.isoformat(),
                        "location": f.get("LOCATION", "").strip()})
    return out


def run(p, ctx):
    events, a = store.load(FILE, []), p["action"]
    now = dt.datetime.now()
    if a == "add":
        if not p.get("title") or not p.get("start"):
            return "title and start are required"
        try:
            s = _p(p["start"])
            e = _p(p["end"]) if p.get("end") else s + dt.timedelta(minutes=int(p.get("duration_min", 60)))
        except ValueError:
            return "Could not read the time; use ISO format like 2026-10-12T14:00."
        if e <= s:
            return "The end must be after the start."
        clash = [x for x in events if _p(x["start"]) < e and s < _p(x["end"])]
        ev = {"id": max([x["id"] for x in events], default=0) + 1, "title": p["title"], "start": s.isoformat(),
              "end": e.isoformat(), "location": p.get("location", "")}
        store.save(FILE, events + [ev])
        ctx.undo.push(f"add event #{ev['id']}", lambda: (store.save(FILE, [x for x in store.load(FILE, []) if x["id"] != ev["id"]]), "Removed.")[1])
        warn = "\n⚠️ Overlaps with: " + "; ".join(_fmt(x) for x in clash) if clash else ""
        return f"Added {_fmt(ev)}{warn}"
    if a in ("today", "list"):
        day = dt.datetime.combine(dt.date.fromisoformat(p["date"]) if p.get("date") else dt.date.today(), dt.time())
        return "\n".join(_fmt(e) for e in _between(events, day, day + dt.timedelta(days=1))) or "Nothing scheduled."
    if a == "upcoming":
        hits = _between(events, now, now + dt.timedelta(days=int(p.get("days", 7))))
        return "\n".join(_fmt(e) for e in hits) or "Nothing coming up."
    if a == "delete":
        hit = next((e for e in events if e["id"] == p.get("id")), None)
        if not hit:
            return "No event with that id."
        store.save(FILE, [e for e in events if e is not hit])
        ctx.undo.push(f"delete event #{hit['id']}", lambda: (store.save(FILE, store.load(FILE, []) + [hit]), "Restored.")[1])
        return f"Deleted {_fmt(hit)}"
    if a == "export_ics":
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//sirius//EN"]
        for e in events:
            lines += ["BEGIN:VEVENT", f"UID:{e['id']}@sirius", f"DTSTART:{_ics_dt(e['start'])}", f"DTEND:{_ics_dt(e['end'])}",
                      f"SUMMARY:{e['title']}"] + ([f"LOCATION:{e['location']}"] if e.get("location") else []) + ["END:VEVENT"]
        lines.append("END:VCALENDAR")
        import os
        path = os.path.expanduser(p.get("path") or "~/sirius_calendar.ics")
        open(path, "w", encoding="utf-8", newline="").write("\r\n".join(lines) + "\r\n")
        return f"Exported {len(events)} events to {path}"
    if a == "import_ics":
        import os
        try:
            new = _parse_ics(open(os.path.expanduser(p["path"]), encoding="utf-8", errors="replace").read())
        except (OSError, KeyError):
            return "Could not read that .ics file."
        base = max([x["id"] for x in events], default=0)
        for i, e in enumerate(new, 1):
            e["id"] = base + i
        store.save(FILE, events + new)
        return f"Imported {len(new)} events."
    return "Unknown action"
