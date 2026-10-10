"""File operations. Deletes go to a trash folder, and everything is undoable."""
import fnmatch
import os
import shutil
import time
from pathlib import Path

TRASH = Path.home() / ".jarvis_trash"
MAX_READ = 20000
MAX_UNDO_BYTES = 1_000_000

TOOL = {
    "name": "file_controller",
    "description": "Work with files and folders: list, read, write, append, create_dir, move, copy, rename, delete (to trash), search (glob pattern), info.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list", "read", "write", "append", "create_dir", "move", "copy",
                                                    "rename", "delete", "search", "info"]},
            "path": {"type": "string", "description": "File or folder. ~ is expanded."},
            "destination": {"type": "string", "description": "Target for move/copy/rename"},
            "content": {"type": "string", "description": "Text for write/append"},
            "pattern": {"type": "string", "description": "Glob for search, e.g. *.pdf"},
        },
        "required": ["action", "path"],
    },
}


def _p(s):
    return Path(os.path.expanduser(s)).resolve()


def run(params, ctx):
    a, path = params["action"], _p(params["path"])
    dest = _p(params["destination"]) if params.get("destination") else None

    if a == "list":
        if not path.is_dir():
            return f"Not a folder: {path}"
        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        return "\n".join(f"{'[D]' if i.is_dir() else '   '} {i.name}" for i in items[:200]) or "(empty)"
    if a == "read":
        if not path.is_file():
            return f"No such file: {path}"
        return path.read_text("utf-8", errors="replace")[:MAX_READ]
    if a == "info":
        if not path.exists():
            return f"No such path: {path}"
        s = path.stat()
        return f"{path} | {'folder' if path.is_dir() else 'file'} | {s.st_size} bytes | modified {time.ctime(s.st_mtime)}"
    if a == "search":
        pat = params.get("pattern") or "*"
        hits = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            hits += [os.path.join(root, f) for f in files if fnmatch.fnmatch(f.lower(), pat.lower())]
            if len(hits) >= 100:
                break
        return "\n".join(hits[:100]) or "No matches."

    if a in ("write", "append"):
        text = params.get("content", "")
        existed = path.exists()
        old = None
        if existed:
            if path.stat().st_size > MAX_UNDO_BYTES:
                ctx.log("file too large to keep for undo")
            else:
                old = path.read_bytes()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a" if a == "append" else "w", encoding="utf-8") as f:
            f.write(text)
        if existed and old is None:
            pass  # not undoable, said so in the log
        elif existed:
            ctx.undo.push(f"{a} {path.name}", lambda: (path.write_bytes(old), "Restored old contents.")[1])
        else:
            ctx.undo.push(f"create {path.name}", lambda: (path.unlink(missing_ok=True), "Removed new file.")[1])
        return f"{'Appended to' if a == 'append' else 'Wrote'} {path} ({len(text)} chars)."

    if a == "create_dir":
        if path.exists():
            return f"Already exists: {path}"
        path.mkdir(parents=True)
        ctx.undo.push(f"create folder {path.name}",
                      lambda: (path.rmdir(), "Removed folder.")[1] if not any(path.iterdir())
                      else "Folder is no longer empty; left it alone.")
        return f"Created {path}"

    if a in ("move", "copy", "rename"):
        if not path.exists():
            return f"No such path: {path}"
        if dest is None:
            return "destination is required"
        if a == "rename" and dest.parent != path.parent and "/" not in params["destination"]:
            dest = path.parent / params["destination"]
        if dest.is_dir():
            dest = dest / path.name
        if dest.exists():
            return f"Refusing to overwrite {dest}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if a == "copy":
            shutil.copytree(path, dest) if path.is_dir() else shutil.copy2(path, dest)
            ctx.undo.push(f"copy {path.name}", lambda: (shutil.rmtree(dest) if dest.is_dir() else dest.unlink(),
                                                         "Removed the copy.")[1])
        else:
            shutil.move(str(path), str(dest))
            ctx.undo.push(f"{a} {path.name}", lambda: (shutil.move(str(dest), str(path)), "Moved back.")[1])
        return f"{a.capitalize()}d {path} -> {dest}"

    if a == "delete":
        if not path.exists():
            return f"No such path: {path}"
        TRASH.mkdir(exist_ok=True)
        target = TRASH / f"{int(time.time())}_{path.name}"
        shutil.move(str(path), str(target))
        ctx.undo.push(f"delete {path.name}", lambda: (shutil.move(str(target), str(path)), "Restored from trash.")[1])
        return f"Moved {path} to trash (say 'undo' to restore)."
    return f"Unknown action {a}"
