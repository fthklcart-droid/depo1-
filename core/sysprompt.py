"""Everything the model is told about itself is derived from the live system, never hand-written."""
from __future__ import annotations

import datetime as dt
import platform
from pathlib import Path

TEMPLATE = Path(__file__).with_name("prompt.txt")


def describe_tools(declarations) -> str:
    lines = []
    for d in declarations or ():
        name = d.get("name") if isinstance(d, dict) else getattr(d, "name", None)
        desc = (d.get("description") if isinstance(d, dict) else getattr(d, "description", "")) or ""
        if name:
            desc = " ".join(str(desc).split())
            lines.append(f"- {name}: {desc[:150]}" if desc else f"- {name}")
    return "\n".join(lines)


def describe_limits(has_vision: bool, has_mic: bool) -> str:
    out = ["- Anything not listed above is outside your reach. Say so in one clause and offer the nearest thing you can do; never mime an action or report a result you did not get.",
           "- You act on this machine only, through the tools listed above.",
           "- You remember the memory block and this session; anything else is gone unless saved."]
    out.append("- You see nothing until you call a vision tool, and then only that single frame." if has_vision
               else "- You have no sight in this build.")
    if has_mic:
        out.append("- You hear nothing while the microphone is muted, and you cannot unmute it yourself.")
    return "\n".join(out)


def render(template: str, values: dict) -> str:
    """Plain replace, not str.format: a stray brace in a hand-edited prompt must not stop startup."""
    for k, v in values.items():
        template = template.replace("{" + k + "}", str(v))
    return template


def build(name: str, tools, memory_block: str, *, has_mic: bool, user_name: str = "") -> str:
    names = {t["name"] for t in tools}
    try:
        template = TEMPLATE.read_text("utf-8")
    except OSError:
        template = "You are {name}. Be concise and use your tools.\n{memory}\n{skills}"
    body = render(template, {
        "name": name, "os": f"{platform.system()} {platform.release()}".strip(),
        "date": dt.datetime.now().strftime("%A, %d %B %Y %H:%M"),
        "memory": memory_block or "(nothing yet)", "skills": ", ".join(sorted(names)),
        "capabilities": describe_tools(tools),
        "limits": describe_limits("look_at_screen" in names, has_mic),
    })
    addr = f"Always call the user '{user_name}'." if user_name else \
        "Address the user with the ordinary respectful form of the language you are speaking."
    return f"[IDENTITY]\nYour name is {name}. {addr}\n\n{body}"
