"""Open an application, file, folder or URL with the OS default handler."""
import os
import platform
import shutil
import subprocess

TOOL = {
    "name": "open_app",
    "description": "Open an application by name, or a file/folder/URL (http...) with its default program.",
    "parameters": {"type": "object", "properties": {"target": {"type": "string", "description": "App name, path or URL"}},
                   "required": ["target"]},
}


def run(p, ctx):
    t, s = p["target"].strip(), platform.system()
    is_path = t.startswith(("http://", "https://", "~", "/")) or os.path.exists(os.path.expanduser(t))
    if is_path:
        t = os.path.expanduser(t)
        if s == "Windows":
            os.startfile(t)  # noqa: S606
        else:
            subprocess.Popen(["open" if s == "Darwin" else "xdg-open", t], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Opened {t}"
    if s == "Darwin":
        r = subprocess.run(["open", "-a", t], capture_output=True, text=True)
        return f"Opened {t}" if r.returncode == 0 else f"Could not open {t}: {r.stderr.strip()}"
    if s == "Windows":
        subprocess.Popen(["cmd", "/c", "start", "", t])
        return f"Started {t}"
    exe = shutil.which(t) or shutil.which(t.lower().replace(" ", "-"))
    if not exe:
        return f"Cannot find an application called '{t}'."
    subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return f"Started {t}"
