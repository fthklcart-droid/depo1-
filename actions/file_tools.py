"""Housekeeping: organize a folder, find duplicates and space hogs, make a zip. Moves are undoable."""
import hashlib
import os
import shutil
import zipfile
from pathlib import Path

CATS = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".heic"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".odt", ".rtf", ".pptx", ".ppt"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a", ".ogg"},
    "Video": {".mp4", ".mkv", ".mov", ".avi", ".webm"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".sh", ".c", ".cpp", ".java", ".go", ".rs"},
    "Installers": {".exe", ".msi", ".dmg", ".deb", ".apk"},
}
TOOLS = []


def _dir(p):
    d = Path(os.path.expanduser(p["path"])).resolve()
    return d if d.is_dir() else None


def organize(p, ctx):
    d = _dir(p)
    if not d:
        return "Not a folder."
    plan = []
    for f in sorted(d.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            cat = next((c for c, exts in CATS.items() if f.suffix.lower() in exts), None)
            if cat:
                plan.append((f, d / cat / f.name))
    if p.get("dry_run", True):
        return ("Would move:\n" + "\n".join(f"{a.name} -> {b.parent.name}/" for a, b in plan[:60]) +
                "\nCall again with dry_run=false to do it (undoable).") if plan else "Nothing to organize."
    moved, made = [], []
    for src, dst in plan:
        if dst.exists():
            continue
        if not dst.parent.exists():
            dst.parent.mkdir()
            made.append(dst.parent)
        shutil.move(str(src), str(dst))
        moved.append((src, dst))

    def undo():
        for src, dst in reversed(moved):
            if dst.exists() and not src.exists():
                shutil.move(str(dst), str(src))
        for m in made:
            if m.exists() and not any(m.iterdir()):
                m.rmdir()
        return f"Put {len(moved)} files back."
    if moved:
        ctx.undo.push(f"organize {d.name} ({len(moved)} files)", undo)
    return f"Moved {len(moved)} files into {len(made)} new folders. Say 'undo' to put them all back."


def duplicates(p, ctx):
    d = _dir(p)
    if not d:
        return "Not a folder."
    by_size: dict[int, list[Path]] = {}
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if not x.startswith(".")]
        for f in files:
            fp = Path(root) / f
            try:
                by_size.setdefault(fp.stat().st_size, []).append(fp)
            except OSError:
                pass
    groups = []
    for size, paths in by_size.items():
        if size == 0 or len(paths) < 2:
            continue
        by_hash: dict[str, list[Path]] = {}
        for fp in paths:
            h = hashlib.sha256()
            try:
                with open(fp, "rb") as fh:
                    for blk in iter(lambda: fh.read(1 << 20), b""):
                        h.update(blk)
            except OSError:
                continue
            by_hash.setdefault(h.hexdigest(), []).append(fp)
        groups += [(size, g) for g in by_hash.values() if len(g) > 1]
    if not groups:
        return "No duplicates."
    groups.sort(key=lambda x: -x[0] * (len(x[1]) - 1))
    waste = sum(s * (len(g) - 1) for s, g in groups)
    lines = [f"{len(groups)} duplicate groups, {waste / 1e6:.1f} MB reclaimable:"]
    for size, g in groups[:15]:
        lines.append(f"- {size / 1e6:.2f} MB x{len(g)}: " + " | ".join(str(x) for x in g))
    return "\n".join(lines)


def largest(p, ctx):
    d = _dir(p)
    if not d:
        return "Not a folder."
    rows = []
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if not x.startswith(".")]
        for f in files:
            fp = os.path.join(root, f)
            try:
                rows.append((os.path.getsize(fp), fp))
            except OSError:
                pass
    rows.sort(reverse=True)
    return "\n".join(f"{s / 1e6:9.1f} MB  {fp}" for s, fp in rows[:int(p.get("count", 10))]) or "No files."


def make_zip(p, ctx):
    src = Path(os.path.expanduser(p["path"])).resolve()
    if not src.exists():
        return "No such path."
    out = Path(os.path.expanduser(p["output"])).resolve() if p.get("output") else src.with_suffix(".zip") if src.is_file() else src.parent / (src.name + ".zip")
    if out.exists():
        return f"Refusing to overwrite {out}"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        if src.is_file():
            z.write(src, src.name)
        else:
            for root, _, files in os.walk(src):
                for f in files:
                    fp = Path(root) / f
                    if fp != out:
                        z.write(fp, fp.relative_to(src.parent))
    ctx.undo.push(f"zip {src.name}", lambda: (out.unlink(missing_ok=True), "Removed the zip.")[1])
    return f"Created {out} ({out.stat().st_size / 1e6:.1f} MB)"


_P = lambda extra=None, req=("path",): {"type": "object", "properties": {"path": {"type": "string"}, **(extra or {})}, "required": list(req)}  # noqa: E731
TOOLS = [
    ({"name": "organize_folder", "description": "Sort loose files in a folder into Images/Documents/Audio/... subfolders. Defaults to a dry run; set dry_run=false to apply (undoable).",
      "parameters": _P({"dry_run": {"type": "boolean"}})}, organize),
    ({"name": "find_duplicates", "description": "Find byte-identical duplicate files in a folder tree and how much space they waste.", "parameters": _P()}, duplicates),
    ({"name": "largest_files", "description": "List the biggest files under a folder.", "parameters": _P({"count": {"type": "integer"}})}, largest),
    ({"name": "make_zip", "description": "Zip a file or folder (output optional). Undoable.", "parameters": _P({"output": {"type": "string"}})}, make_zip),
]
