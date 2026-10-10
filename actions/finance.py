"""Expense tracker and currency conversion."""
import datetime as dt
import json
import urllib.parse
import urllib.request

from core import store

FILE = "expenses.json"
TOOLS = []


def expenses(p, ctx):
    items, a = store.load(FILE, []), p["action"]
    if a == "add":
        try:
            amt = float(p["amount"])
        except (KeyError, ValueError):
            return "amount must be a number"
        it = {"id": max([i["id"] for i in items], default=0) + 1, "amount": amt, "category": p.get("category", "other").lower(),
              "note": p.get("note", ""), "currency": p.get("currency", "TRY").upper(),
              "date": p.get("date") or dt.date.today().isoformat()}
        store.save(FILE, items + [it])
        ctx.undo.push(f"expense #{it['id']}", lambda: (store.save(FILE, [x for x in store.load(FILE, []) if x["id"] != it["id"]]), "Removed.")[1])
        return f"Logged #{it['id']}: {amt:g} {it['currency']} {it['category']} {it['note']}".strip()
    month = p.get("month") or dt.date.today().strftime("%Y-%m")
    sel = [i for i in items if i["date"].startswith(month)]
    if a == "list":
        return "\n".join(f"#{i['id']} {i['date']} {i['amount']:g} {i['currency']} {i['category']} {i['note']}" for i in sel) or "No expenses."
    if a == "summary":
        if not sel:
            return f"No expenses in {month}."
        tot: dict = {}
        for i in sel:
            tot.setdefault(i["currency"], {}).setdefault(i["category"], 0.0)
            tot[i["currency"]][i["category"]] += i["amount"]
        lines = [f"{month}:"]
        for cur, cats in tot.items():
            lines.append(f"  {cur} total {sum(cats.values()):g}")
            lines += [f"    {c}: {v:g}" for c, v in sorted(cats.items(), key=lambda kv: -kv[1])]
        return "\n".join(lines)
    hit = next((i for i in items if i["id"] == p.get("id")), None)
    if not hit:
        return "No expense with that id."
    store.save(FILE, [i for i in items if i is not hit])
    ctx.undo.push(f"delete expense #{hit['id']}", lambda: (store.save(FILE, store.load(FILE, []) + [hit]), "Restored.")[1])
    return f"Deleted #{hit['id']}"


def currency(p, ctx):
    amt, f, t = float(p.get("amount", 1)), p["from_currency"].upper(), p["to_currency"].upper()
    url = "https://api.frankfurter.app/latest?" + urllib.parse.urlencode({"amount": amt, "from": f, "to": t})
    with urllib.request.urlopen(url, timeout=10) as r:
        d = json.load(r)
    return f"{amt:g} {f} = {d['rates'][t]:g} {t} (rate date {d['date']})"


_S = {"type": "string"}
TOOLS = [
    ({"name": "expenses", "description": "Track spending. add (amount, category, note, currency default TRY), list/summary (month YYYY-MM, default this month), delete (id).",
      "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["add", "list", "summary", "delete"]},
                     "amount": {"type": "number"}, "category": _S, "note": _S, "currency": _S, "month": _S, "date": _S,
                     "id": {"type": "integer"}}, "required": ["action"]}}, expenses),
    ({"name": "currency_convert", "description": "Convert money between currencies at the latest ECB rate (e.g. USD to TRY).",
      "parameters": {"type": "object", "properties": {"amount": {"type": "number"}, "from_currency": _S, "to_currency": _S},
                     "required": ["from_currency", "to_currency"]}}, currency),
]
