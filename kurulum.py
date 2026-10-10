#!/usr/bin/env python3
"""SIRIUS kurulumu: tek komut.

    python kurulum.py                  sorarak kurar (önerilen)
    python kurulum.py --yes            soru sormadan kurar (otomatik araçlar için)
    python kurulum.py --dry-run        ne yapacağını yazar, hiçbir şey değiştirmez

Adımlar: Python sürümü → sanal ortam (.venv) → bağımlılıklar → Gemini anahtarı → anahtar doğrulama → (isteğe bağlı) sesli mod, kısayol, test, başlat.
API anahtarı komut satırından ALINMAZ (kabuk geçmişine düşer): ortam değişkeni GEMINI_API_KEY ya da gizli giriş kullanılır.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config" / "api_keys.json"
LOG = ROOT / "memory" / "kurulum.log"
MIN_PY = (3, 11)
SECRETS: list[str] = []
QUIET_LOG = False                # --dry-run must not write anything          # anything in here is masked before it reaches the screen or the log


def mask(text: str) -> str:
    for s in SECRETS:
        if s:
            text = text.replace(s, "***")
    return text


def say(msg: str = "") -> None:
    msg = mask(msg)
    print(msg, flush=True)
    if QUIET_LOG:
        return
    try:
        LOG.parent.mkdir(exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except OSError:
        pass


def venv_python(root: Path = ROOT, system: str | None = None) -> Path:
    return root / ".venv" / ("Scripts/python.exe" if (system or platform.system()) == "Windows" else "bin/python")


def python_ok(v=None) -> bool:
    return tuple((v or sys.version_info)[:2]) >= MIN_PY


def write_key(key: str, path: Path = CONFIG) -> None:
    """Merge the key into config/api_keys.json (other settings stay), owner-only permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(path.read_text("utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    data["gemini_api_key"] = key
    data.setdefault("assistant_name", "SIRIUS")
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    tmp.replace(path)


def existing_key(path: Path = CONFIG) -> str | None:
    try:
        return json.loads(path.read_text("utf-8")).get("gemini_api_key") or None
    except (OSError, ValueError, AttributeError):
        return None


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, **kw)


def make_venv() -> tuple[bool, str]:
    import venv
    try:
        venv.EnvBuilder(with_pip=True).create(ROOT / ".venv")
    except Exception as e:  # noqa: BLE001 - Debian/Ubuntu without python3-venv raises here
        return False, f"{type(e).__name__}: {e}. Linux'ta: sudo apt install python3-venv"
    return venv_python().exists(), ""


def pip_install(py: str, req: str) -> bool:
    return run([py, "-m", "pip", "install", "--disable-pip-version-check", "-r", req]).returncode == 0


def validate_key(py: str, key: str) -> tuple[bool, str]:
    """One tiny read-only call (list models) with the venv's own google-genai. Nothing is generated or billed."""
    code = "import os;from google import genai;c=genai.Client(api_key=os.environ['SIRIUS_K']);next(iter(c.models.list()));print('OK')"
    try:
        r = run([py, "-c", code], capture_output=True, text=True, timeout=60, env={**os.environ, "SIRIUS_K": key})
    except subprocess.TimeoutExpired:
        return False, "zaman aşımı (ağ erişimi yok mu?)"
    if "OK" in r.stdout:
        return True, "anahtar geçerli"
    err = mask((r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout).strip() else "bilinmeyen hata")
    return False, err[:200]


def ask(q: str, default: bool, yes: bool) -> bool:
    if yes:
        return default
    a = input(f"{q} [{'E/h' if default else 'e/H'}]: ").strip().lower()
    return default if not a else a in ("e", "evet", "y", "yes")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="SIRIUS kurulumu")
    ap.add_argument("--yes", action="store_true", help="soru sorma, varsayılanları uygula")
    ap.add_argument("--dry-run", action="store_true", help="hiçbir şey değiştirme, planı yaz")
    ap.add_argument("--no-venv", action="store_true", help="sanal ortam kurma, bu Python'a kur")
    ap.add_argument("--voice", action="store_true", help="sesli mod paketlerini de kur")
    ap.add_argument("--shortcut", action="store_true", help="masaüstü kısayolu oluştur")
    ap.add_argument("--test", action="store_true", help="kurulumdan sonra testleri çalıştır")
    ap.add_argument("--run", action="store_true", help="kurulumdan sonra başlat (web arayüzü)")
    ap.add_argument("--skip-validate", action="store_true", help="anahtarı Google'a sorarak doğrulama")
    a = ap.parse_args(argv)
    global QUIET_LOG
    QUIET_LOG = a.dry_run
    done, warn = [], []

    say(f"== SIRIUS kurulumu ({platform.system()}, Python {sys.version.split()[0]}) ==")
    if not python_ok():
        say(f"HATA: Python {MIN_PY[0]}.{MIN_PY[1]} ya da üstü gerekir; bu {sys.version.split()[0]}. https://www.python.org/downloads/")
        return 1
    if a.dry_run:
        say("Plan: " + ("sanal ortam (.venv) → " if not a.no_venv else "") + "pip install -r requirements.txt"
            + (" + requirements-voice.txt" if a.voice else "") + " → anahtar ayarı → doğrulama" + (" → kısayol" if a.shortcut else "") + (" → test" if a.test else "") + (" → başlat" if a.run else ""))
        return 0

    # 1) venv
    py = sys.executable
    if not a.no_venv:
        if venv_python().exists():
            say("1/5 Sanal ortam zaten var (.venv)")
        else:
            say("1/5 Sanal ortam oluşturuluyor (.venv)…")
            ok, why = make_venv()
            if not ok:
                say(f"HATA: sanal ortam kurulamadı: {why}\nİpucu: --no-venv ile bu Python'a doğrudan kurabilirsin.")
                return 1
        py = str(venv_python())
        done.append("sanal ortam")

    # 2) packages
    say("2/5 Bağımlılıklar kuruluyor (birkaç dakika sürebilir)…")
    if not pip_install(py, "requirements.txt"):
        say("HATA: bağımlılıklar kurulamadı. İnternet bağlantını kontrol et ve tekrar çalıştır; kurulum kaldığı yerden devam eder.")
        return 1
    done.append("çekirdek paketler")
    if a.voice or ask("Sesli mod (mikrofon/hoparlör) paketleri de kurulsun mu?", False, a.yes):
        if pip_install(py, "requirements-voice.txt"):
            done.append("sesli mod paketleri")
        else:
            warn.append("Sesli mod paketleri kurulamadı (Linux'ta: sudo apt install libportaudio2). Yazılı mod etkilenmez.")

    # 3) key
    say("3/5 Gemini anahtarı…")
    key = os.environ.get("GEMINI_API_KEY") or existing_key()
    src = "ortam değişkeninden" if os.environ.get("GEMINI_API_KEY") else "mevcut ayar dosyasından"
    if key:
        SECRETS.append(key)
        say(f"    Anahtar {src} alındı.")
        if os.environ.get("GEMINI_API_KEY") and existing_key() != key and ask("Anahtar config/api_keys.json dosyasına kaydedilsin mi?", True, a.yes):
            write_key(key); done.append("anahtar kaydedildi")
    elif not a.yes:
        key = getpass.getpass("    Gemini API anahtarını yapıştır (görünmez; boş bırakırsan atlanır): ").strip()
        if key:
            SECRETS.append(key)
            write_key(key); done.append("anahtar kaydedildi")
    if not key:
        warn.append("Anahtar ayarlanmadı. Sohbet için: GEMINI_API_KEY ortam değişkeni ya da config/api_keys.json (bkz. config/api_keys.example.json). Hızlı komutlar anahtarsız çalışır.")

    # 4) validate
    if key and not a.skip_validate:
        say("4/5 Anahtar doğrulanıyor (yalnızca model listesi istenir)…")
        ok, msg = validate_key(py, key)
        say(f"    {'✓' if ok else '✗'} {msg}")
        (done if ok else warn).append("anahtar doğrulandı" if ok else f"Anahtar doğrulanamadı: {msg}")
    else:
        say("4/5 Anahtar doğrulaması atlandı")

    # 5) extras
    say("5/5 İsteğe bağlı adımlar…")
    if a.test or ask("Testler çalıştırılsın mı? (pytest kurar, ~30 sn)", False, a.yes):
        if run([py, "-m", "pip", "install", "--disable-pip-version-check", "-q", "pytest"]).returncode == 0:
            r = run([py, "-m", "pytest", "-q", "tests"], env={**os.environ, "SIRIUS_NO_AUDIT": "1"})
            (done if r.returncode == 0 else warn).append("testler geçti" if r.returncode == 0 else "bazı testler başarısız (ağ ya da eksik isteğe bağlı paket olabilir)")
    if a.shortcut or (not a.yes and ask("Masaüstüne SIRIUS kısayolu oluşturulsun mu?", True, False)):
        r = run([py, "kisayol.py"])
        (done if r.returncode == 0 else warn).append("masaüstü kısayolu" if r.returncode == 0 else "kısayol oluşturulamadı")

    say("\n== Özet ==")
    for d in done:
        say(f"  ✓ {d}")
    for w in warn:
        say(f"  ! {w}")
    cmd = f'"{py}" main.py --web' if not a.no_venv else "python main.py --web"
    say(f"\nBaşlatmak için:  {cmd}\nSesli mod:       {cmd.replace('--web', '--live')}")
    if a.run:
        say("SIRIUS başlatılıyor…")
        os.execv(py, [py, "main.py", "--web"]) if platform.system() != "Windows" else subprocess.Popen([py, "main.py", "--web"], cwd=ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
