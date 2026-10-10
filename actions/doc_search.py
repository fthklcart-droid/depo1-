"""Search your own documents. Pure-Python BM25 over a local index: nothing is uploaded anywhere."""
import math
import os
import re
import zipfile
from pathlib import Path

from core import store

INDEX = "doc_index.json"
EXT = {".txt", ".md", ".rst", ".py", ".js", ".ts", ".json", ".csv", ".html", ".log", ".tex", ".yaml", ".yml", ".docx", ".pdf"}
CHUNK = 800
MAX_FILE = 5_000_000
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".sirius_trash"}

TOOL = {
    "name": "doc_search",
    "description": "Search the user's own documents by meaning of keywords. action=index (path=folder, builds/refreshes the local index), search (query), list (indexed folders), forget (path).",
    "parameters": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["index", "search", "list", "forget"]},
        "path": {"type": "string"}, "query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["action"]},
}


def tokens(text):
    return re.findall(r"\w{2,}", text.lower())


def read_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".docx":
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", xml.replace("</w:p>", "\n")))
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return ""
        return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(path)).pages)
    return path.read_text("utf-8", errors="replace")


def chunks(text):
    text = re.sub(r"[ \t]+", " ", text)
    for i in range(0, len(text), CHUNK):
        c = text[i:i + CHUNK].strip()
        if c:
            yield c


def build(root: Path, idx: dict) -> tuple[int, int, int]:
    """Incremental: only files whose mtime changed are re-read. Returns (added, unchanged, removed)."""
    docs, added, same = idx["docs"], 0, 0
    seen = set()
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            p = Path(dirpath) / f
            if p.suffix.lower() not in EXT:
                continue
            try:
                st = p.stat()
                if st.st_size > MAX_FILE:
                    continue
                key = str(p)
                seen.add(key)
                if key in docs and docs[key]["mtime"] == st.st_mtime:
                    same += 1
                    continue
                docs[key] = {"mtime": st.st_mtime, "chunks": list(chunks(read_text(p)))}
                added += 1
            except Exception:  # noqa: BLE001 - one unreadable file must not stop the index
                continue
    prefix = str(root)
    gone = [k for k in docs if k.startswith(prefix) and k not in seen]
    for k in gone:
        del docs[k]
    if str(root) not in idx["roots"]:
        idx["roots"].append(str(root))
    return added, same, len(gone)


def bm25(idx: dict, query: str, limit: int):
    q = set(tokens(query))
    rows = [(path, c) for path, d in idx["docs"].items() for c in d["chunks"]]
    if not q or not rows:
        return []
    toks = [tokens(c) for _, c in rows]
    n, avg = len(rows), sum(len(t) for t in toks) / len(rows)
    df = {w: sum(1 for t in toks if w in t) for w in q}
    out = []
    for (path, c), t in zip(rows, toks):
        score = 0.0
        for w in q:
            tf = t.count(w)
            if tf:
                idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
                score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * len(t) / avg))
        if score:
            out.append((score, path, c))
    out.sort(reverse=True)
    best, seen = [], set()
    for s, p, c in out:           # one hit per file keeps the answer varied
        if p not in seen:
            seen.add(p)
            best.append((s, p, c))
        if len(best) >= limit:
            break
    return best


def run(p, ctx):
    idx = store.load(INDEX, {"roots": [], "docs": {}})
    a = p["action"]
    if a == "index":
        root = Path(os.path.expanduser(p.get("path", ""))).resolve()
        if not root.is_dir():
            return f"Not a folder: {root}"
        added, same, gone = build(root, idx)
        store.save(INDEX, idx)
        return f"Indexed {root}: {added} new/changed, {same} unchanged, {gone} removed. {len(idx['docs'])} files total."
    if a == "list":
        return "\n".join(f"{r}" for r in idx["roots"]) + f"\n{len(idx['docs'])} files indexed." if idx["roots"] else "Nothing indexed yet."
    if a == "forget":
        prefix = str(Path(os.path.expanduser(p.get("path", ""))).resolve())
        idx["docs"] = {k: v for k, v in idx["docs"].items() if not k.startswith(prefix)}
        idx["roots"] = [r for r in idx["roots"] if r != prefix]
        store.save(INDEX, idx)
        return f"Forgot {prefix}."
    if not idx["docs"]:
        return "No index yet. Call doc_search with action=index and a folder first."
    hits = bm25(idx, p.get("query", ""), int(p.get("limit", 5)))
    return "\n\n".join(f"{i}. {path}\n   …{c[:300].strip()}…" for i, (s, path, c) in enumerate(hits, 1)) or "No matches."
