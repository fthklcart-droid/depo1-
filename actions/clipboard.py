"""Read or write the system clipboard using whatever tool the OS provides."""
import platform
import shutil
import subprocess

TOOL = {
    "name": "clipboard",
    "description": "Read the clipboard (action=read) or put text on it (action=write, text=...).",
    "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["read", "write"]},
                                                      "text": {"type": "string"}}, "required": ["action"]},
}


def _cmds():
    s = platform.system()
    if s == "Darwin":
        return ["pbpaste"], ["pbcopy"]
    if s == "Windows":
        return ["powershell", "-command", "Get-Clipboard"], ["clip"]
    for r, w in ((["wl-paste"], ["wl-copy"]), (["xclip", "-selection", "clipboard", "-o"], ["xclip", "-selection", "clipboard"]),
                 (["xsel", "-b", "-o"], ["xsel", "-b", "-i"])):
        if shutil.which(r[0]):
            return r, w
    return None, None


def run(p, ctx):
    r, w = _cmds()
    if not r:
        return "No clipboard tool found (install wl-clipboard or xclip)."
    if p["action"] == "read":
        out = subprocess.run(r, capture_output=True, text=True, timeout=5).stdout
        return out[:8000] or "(clipboard is empty)"
    subprocess.run(w, input=p.get("text", ""), text=True, timeout=5)
    return "Copied."
