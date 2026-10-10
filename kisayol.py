"""Masaüstüne SIRIUS kısayolu oluşturur (Windows, macOS, Linux).

    python kisayol.py            kısayolu oluştur
    python kisayol.py --run      oluştur ve hemen çalıştır
    python kisayol.py --remove   kısayolu sil
    python kisayol.py --dry-run  ne yapacağını yaz, hiçbir şey oluşturma
"""
from __future__ import annotations

import argparse
import os
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "SIRIUS"
LOG = ROOT / "memory" / "sirius.log"


def make_icons() -> dict[str, Path | None]:
    """Draw the SIRIUS star (Pillow). Returns paths, or None if Pillow is missing."""
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError:
        return {"png": None, "ico": None}
    out = ROOT / "assets"
    out.mkdir(exist_ok=True)
    S = 512
    img = Image.new("RGBA", (S, S), (4, 7, 13, 255))
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((96, 96, 416, 416), fill=(143, 227, 255, 120))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(50)))
    d = ImageDraw.Draw(img)
    c, big, small = S / 2, 190, 22
    d.polygon([(c, c - big), (c + small, c - small), (c + big, c), (c + small, c + small), (c, c + big), (c - small, c + small), (c - big, c), (c - small, c - small)], fill=(207, 243, 255, 255))
    d.ellipse((c + 96, c - 138, c + 130, c - 104), fill=(255, 213, 138, 255))           # the companion star
    png, ico = out / "sirius.png", out / "sirius.ico"
    img.save(png)
    img.save(ico, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return {"png": png, "ico": ico}


def desktop_dir(system: str | None = None, home: Path | None = None) -> Path:
    system, home = system or platform.system(), home or Path.home()
    if system == "Windows":
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"], capture_output=True, text=True, timeout=15)
            if r.stdout.strip():
                return Path(r.stdout.strip())                      # honours OneDrive-redirected desktops
        except (OSError, subprocess.TimeoutExpired):
            pass
        return home / "Desktop"
    if system == "Linux" and shutil.which("xdg-user-dir"):
        r = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True)
        if r.stdout.strip() and Path(r.stdout.strip()) != home:
            return Path(r.stdout.strip())
    for name in ("Desktop", "Masaüstü"):
        if (home / name).is_dir():
            return home / name
    return home / "Desktop"


def linux_desktop_entry(py: str, icon: Path | None) -> str:
    cmd = f"cd {shlex.quote(str(ROOT))} && exec {shlex.quote(py)} main.py --web >> {shlex.quote(str(LOG))} 2>&1"
    esc = cmd.replace("\\", "\\\\").replace('"', '\\"')
    return ("[Desktop Entry]\nVersion=1.0\nType=Application\nName=SIRIUS\nComment=Kişisel yapay zekâ asistanı\n"
            f'Exec=sh -c "{esc}"\n' + (f"Icon={icon}\n" if icon else "") + f"Path={ROOT}\nTerminal=false\nCategories=Utility;\n")


def mac_command(py: str) -> str:
    return f"#!/bin/bash\ncd {shlex.quote(str(ROOT))}\nmkdir -p memory\nexec {shlex.quote(py)} main.py --web >> {shlex.quote(str(LOG))} 2>&1\n"


def windows_shortcut_script(lnk: Path, py: str, icon: Path | None) -> str:
    pyw = Path(py).with_name("pythonw.exe")
    target = pyw if pyw.exists() else Path(py)                     # pythonw: no console window
    q = lambda s: str(s).replace("'", "''")  # noqa: E731
    lines = ["$s=(New-Object -ComObject WScript.Shell).CreateShortcut('" + q(lnk) + "')",
             "$s.TargetPath='" + q(target) + "'",
             "$s.Arguments='\"" + q(ROOT / "main.py") + "\" --web'",
             "$s.WorkingDirectory='" + q(ROOT) + "'",
             "$s.Description='SIRIUS kişisel yapay zekâ asistanı'"]
    if icon:
        lines.append("$s.IconLocation='" + q(icon) + "'")
    return "; ".join(lines + ["$s.Save()"])


def create(system: str, desk: Path, py: str, icons: dict, dry: bool = False) -> Path:
    desk.mkdir(parents=True, exist_ok=True) if not dry else None
    if system == "Windows":
        lnk = desk / f"{NAME}.lnk"
        script = windows_shortcut_script(lnk, py, icons.get("ico"))
        if not dry:
            subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True, timeout=30)
        return lnk
    if system == "Darwin":
        f = desk / f"{NAME}.command"
        if not dry:
            f.write_text(mac_command(py), "utf-8"); f.chmod(0o755)
        return f
    f = desk / f"{NAME}.desktop"
    if not dry:
        f.write_text(linux_desktop_entry(py, icons.get("png")), "utf-8"); f.chmod(0o755)
        if shutil.which("gio"):                                    # lets GNOME launch it without the "untrusted" prompt
            subprocess.run(["gio", "set", str(f), "metadata::trusted", "true"], capture_output=True)
    return f


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="SIRIUS masaüstü kısayolu")
    ap.add_argument("--run", action="store_true", help="oluşturduktan sonra çalıştır")
    ap.add_argument("--remove", action="store_true", help="kısayolu sil")
    ap.add_argument("--dry-run", action="store_true", help="hiçbir şey yazma, sadece göster")
    ap.add_argument("--desktop", help="masaüstü klasörünü elle belirt")
    a = ap.parse_args(argv)
    system = platform.system()
    desk = Path(a.desktop).expanduser() if a.desktop else desktop_dir()
    if a.remove:
        for ext in ("lnk", "command", "desktop"):
            f = desk / f"{NAME}.{ext}"
            if f.exists():
                f.unlink(); print(f"Silindi: {f}")
        return 0
    if sys.version_info < (3, 11):
        print("Python 3.11 ya da üstü gerekir."); return 1
    icons = {"png": None, "ico": None} if a.dry_run else make_icons()
    if not a.dry_run:
        LOG.parent.mkdir(exist_ok=True)
    path = create(system, desk, sys.executable, icons, a.dry_run)
    print(("Oluşturulurdu: " if a.dry_run else "Oluşturuldu: ") + str(path))
    if not icons.get("png") and not a.dry_run:
        print("(Simge için Pillow gerekir: pip install pillow)")
    if a.run and not a.dry_run:
        print("SIRIUS başlatılıyor… tarayıcın açılacak.")
        kw = {"creationflags": 0x08000000} if system == "Windows" else {"start_new_session": True}
        LOG.parent.mkdir(exist_ok=True)
        subprocess.Popen([sys.executable, str(ROOT / "main.py"), "--web"], cwd=ROOT, stdout=open(LOG, "ab"), stderr=subprocess.STDOUT, **kw)
    return 0


if __name__ == "__main__":
    sys.exit(main())
