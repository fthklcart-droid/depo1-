"""Tools that act on the assistant itself."""

TOOL = {
    "name": "shutdown_assistant",
    "description": "Shut the assistant down. Call when the user says goodbye or asks you to quit, in any language.",
    "parameters": {"type": "object", "properties": {}},
}


def run(params, ctx):
    ctx.shutdown()
    return "Shutting down after this reply."


def audit_run(params, ctx):
    import json
    from core.action_loader import AUDIT
    try:
        lines = AUDIT.read_text("utf-8").splitlines()[-int(params.get("count", 15)):]
    except OSError:
        return "No actions logged yet."
    import datetime as dt
    out = []
    for l in lines:
        r = json.loads(l)
        out.append(f"{dt.datetime.fromtimestamp(r['t']):%m-%d %H:%M:%S} {'ok ' if r['ok'] else 'ERR'} {r['tool']} {r['args']}")
    return "\n".join(out)


TOOLS = [
    (TOOL, run),
    ({"name": "audit_log", "description": "Show what the assistant did recently on this computer (tool calls with arguments). Use when asked 'what did you do?'.",
      "parameters": {"type": "object", "properties": {"count": {"type": "integer"}}}}, audit_run),
]
