"""Smart home through Home Assistant's REST API. Config: "home_assistant": {"url": "...", "token": "..."}.
Locks, alarms, garage doors and covers need the human's confirmation."""
import json
import urllib.request

from core.config import Config

SENSITIVE = {"lock", "alarm_control_panel", "cover", "siren", "camera"}
TOOL = {
    "name": "home_assistant",
    "description": "Smart home. action=states (optional domain filter like light/sensor/switch), state (entity_id), call (domain, service, entity_id, optional data). Turn lights on: domain=light service=turn_on.",
    "parameters": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["states", "state", "call"]}, "domain": {"type": "string"},
        "service": {"type": "string"}, "entity_id": {"type": "string"}, "data": {"type": "object"}}, "required": ["action"]},
}


def _req(c, path, body=None):
    req = urllib.request.Request(c["url"].rstrip("/") + "/api" + path, method="POST" if body is not None else "GET",
                                 headers={"Authorization": f"Bearer {c['token']}", "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def run(p, ctx):
    c = Config().get("home_assistant")
    if not c or not c.get("url") or not c.get("token"):
        return 'Home Assistant is not configured. Add "home_assistant": {"url","token"} to config/api_keys.json.'
    a = p["action"]
    if a == "states":
        rows = [s for s in _req(c, "/states") if not p.get("domain") or s["entity_id"].startswith(p["domain"] + ".")]
        return "\n".join(f"{s['entity_id']}: {s['state']}" for s in rows[:80]) or "No entities."
    if a == "state":
        s = _req(c, f"/states/{p['entity_id']}")
        return f"{s['entity_id']}: {s['state']} {json.dumps(s.get('attributes', {}), ensure_ascii=False)[:400]}"
    dom, svc, ent = p.get("domain"), p.get("service"), p.get("entity_id")
    if not (dom and svc):
        return "domain and service are required"
    if dom in SENSITIVE and not ctx.confirm(f"Akıllı ev işlemi onaylansın mı?\n{dom}.{svc} -> {ent}"):
        return "The user declined, nothing was changed."
    _req(c, f"/services/{dom}/{svc}", {**(p.get("data") or {}), **({"entity_id": ent} if ent else {})})
    return f"Called {dom}.{svc} on {ent or 'all'}."
