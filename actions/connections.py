"""Your own sites, folders/files and apps. Social accounts are not supported yet (they need per-platform OAuth)."""
import os
import shlex
import subprocess

from core import store

FILE = "connections.json"
TOOL = {
    "name": "connections",
    "description": "The user's saved sites, files/folders and apps. action: list | add_site (url) | remove_site (url) | read_site (url) | add_file (path; indexed for doc_search) | remove_file (path) | add_app (name, alias, command optional) | remove_app (name).",
    "parameters": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["list", "add_site", "remove_site", "read_site", "add_file", "remove_file", "add_app", "remove_app"]},
        "url": {"type": "string"}, "path": {"type": "string"}, "name": {"type": "string"},
        "alias": {"type": "string"}, "command": {"type": "string"}, "watch": {"type": "boolean"}}, "required": ["action"]},
}


def _load():
    d = store.load(FILE, {})
    return {"sites": d.get("sites", []), "files": d.get("files", []), "apps": d.get("apps", [])}


def _undo(ctx, label, before):
    ctx.undo.push(label, lambda: (store.save(FILE, before), "Restored.")[1])


def run(p, ctx):
    d, a = _load(), p["action"]
    before = {k: list(v) for k, v in d.items()}
    if a == "list":
        out = []
        out += [f"site: {s['url']}{' (izleniyor)' if s.get('watch') else ''}" for s in d["sites"]]
        out += [f"dosya: {f['path']} - {f.get('note', '')}" for f in d["files"]]
        out += [f"uygulama: {x['name']} (takma ad: {x.get('alias') or x['name'].lower()})" for x in d["apps"]]
        return "\n".join(out) or "Henüz bir şey eklenmedi."
    if a == "add_site":
        url = (p.get("url") or "").strip()
        if not url:
            return "url is required"
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        if any(s["url"] == url for s in d["sites"]):
            return "Bu site zaten ekli."
        d["sites"].append({"url": url, "watch": bool(p.get("watch"))})
        store.save(FILE, d)
        _undo(ctx, f"add site {url}", before)
        return f"Eklendi: {url}"
    if a == "remove_site":
        d["sites"] = [s for s in d["sites"] if s["url"] != p.get("url")]
        if d["sites"] == before["sites"]:
            return "Böyle bir site yok."
        store.save(FILE, d)
        _undo(ctx, "remove site", before)
        return "Kaldırıldı."
    if a == "read_site":
        url = p.get("url") or (d["sites"][0]["url"] if d["sites"] else "")
        if not any(s["url"] == url for s in d["sites"]):
            return "Bu site eklenmemiş; önce ekleyin."   # only saved sites are fetched through this tool
        return ctx.call("fetch_page", url=url)
    if a == "add_file":
        path = os.path.abspath(os.path.expanduser(p.get("path", "")))
        if not os.path.exists(path):
            return f"Yol bulunamadı: {path}"
        res = ctx.call("doc_search", action="index", path=path)
        d["files"] = [f for f in d["files"] if f["path"] != path] + [{"path": path, "note": res[:80]}]
        store.save(FILE, d)
        _undo(ctx, f"add {os.path.basename(path)}", before)
        return res
    if a == "remove_file":
        path = os.path.abspath(os.path.expanduser(p.get("path", "")))
        d["files"] = [f for f in d["files"] if f["path"] != path]
        if d["files"] == before["files"]:
            return "Böyle bir kayıt yok."
        store.save(FILE, d)
        ctx.call("doc_search", action="forget", path=path)
        return "Kaldırıldı ve indeksten çıkarıldı."
    if a == "add_app":
        name = (p.get("name") or "").strip()
        if not name:
            return "name is required"
        d["apps"] = [x for x in d["apps"] if x["name"].lower() != name.lower()] + [
            {"name": name, "alias": (p.get("alias") or name).lower(), "command": (p.get("command") or "").strip()}]
        store.save(FILE, d)
        _undo(ctx, f"add app {name}", before)
        return f"Eklendi: {name}. 'Aç {name}' demen yeterli."
    if a == "remove_app":
        d["apps"] = [x for x in d["apps"] if x["name"].lower() != (p.get("name") or "").lower()]
        if d["apps"] == before["apps"]:
            return "Böyle bir uygulama yok."
        store.save(FILE, d)
        _undo(ctx, "remove app", before)
        return "Kaldırıldı."
    return "Unknown action"
