"""Feeds the HOLO hand-gesture deck: your SIRIUS notes and the folders you added in Bağlantılar become orbs and cards."""
from __future__ import annotations

import os
from pathlib import Path

from core import store

EXT = (".md", ".txt")
HOLO_DIR = Path(__file__).resolve().parent.parent / "holo"


def card(name: str, text: str) -> dict:
    lines = [l for l in text.splitlines() if l.strip()]
    title = (lines[0].lstrip("# ").strip() if lines else name)[:48] or name
    rest = [l for l in lines[1:] if not l.startswith("#")]
    return {"name": name, "title": title, "body": "\n".join(rest)[:420], "full": "\n".join(lines[1:])[:4000]}


def _files(d: Path, limit: int = 14) -> list[dict]:
    out = []
    try:
        for p in sorted(x for x in d.iterdir() if x.is_file() and x.suffix.lower() in EXT)[:limit]:
            if p.stat().st_size <= 400_000:
                out.append(card(p.name, p.read_text("utf-8", errors="ignore")))
    except OSError:
        pass
    return out


def folder_orbs(d: Path) -> list[dict]:
    """Subfolders become orbs; loose files in the folder gather under the folder's own name."""
    orbs = []
    try:
        for sub in sorted(x for x in d.iterdir() if x.is_dir() and not x.name.startswith("."))[:10]:
            files = _files(sub)
            if files:
                orbs.append({"kind": "folder", "name": sub.name.upper()[:22], "files": files})
    except OSError:
        pass
    loose = _files(d)
    if loose:
        orbs.insert(0, {"kind": "folder", "name": d.name.upper()[:22] or "NOTLAR", "files": loose})
    return orbs


def tree() -> list[dict]:
    orbs = []
    notes = store.load("notes.json", [])
    if notes:
        cards = []
        for n in notes[-14:]:
            mark = "" if n.get("kind") == "note" else ("[x] " if n.get("done") else "[ ] ")
            cards.append(card(f"not-{n['id']}.md", f"{mark}{n['text']}\n{'yapılacak' if n.get('kind') == 'todo' else 'not'}"))
        orbs.append({"kind": "folder", "name": "NOTLARIM", "files": cards})
    for f in store.load("connections.json", {}).get("files", [])[:6]:
        p = Path(f.get("path", ""))
        if p.is_dir():
            orbs += folder_orbs(p)
        elif p.is_file() and p.suffix.lower() in EXT:
            orbs.append({"kind": "folder", "name": p.stem.upper()[:22], "files": [card(p.name, p.read_text("utf-8", errors="ignore")[:4000])]})
    if not orbs:
        orbs.append({"kind": "folder", "name": "SIRIUS", "files": [
            card("hosgeldin.md", "Hoş geldin\nHenüz notun yok. Asistana 'not al: …' de ya da Bağlantılar'dan bir not klasörü ekle; burada küreler olarak belirir."),
            card("hareketler.md", "Hareketler\nTutma: başparmak ve işaret parmağını birleştir. Fırlatma: tutup bırak. Büyütme: iki elle aç. Sıfırlama: ✌ işareti.")]})
    return orbs[:10]


def props() -> list[str]:
    try:
        return sorted(x.name for x in (HOLO_DIR / "props").iterdir() if x.suffix == ".glb")[:6]
    except OSError:
        return []
