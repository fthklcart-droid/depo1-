"""Process-level hardening that must run before anything else prints or spawns."""
from __future__ import annotations

import platform
import subprocess
import sys


def harden_console() -> None:
    """Status lines carry emoji; a cp1254/cp1251/cp932 console would raise on them. Never fatal."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        try:
            if stream is not None and hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - pythonw, redirected pipes, anything exotic
            pass


def hide_subprocess_windows() -> None:
    """Windows only: no console flash for any child process."""
    if platform.system() != "Windows" or getattr(subprocess.Popen, "_jarvis_patched", False):
        return
    Orig = subprocess.Popen

    class _Popen(Orig):
        _jarvis_patched = True

        def __init__(self, args, **kw):
            kw["creationflags"] = kw.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
            kw.pop("startupinfo", None)
            super().__init__(args, **kw)

    subprocess.Popen = _Popen


def init() -> None:
    harden_console()
    hide_subprocess_windows()
