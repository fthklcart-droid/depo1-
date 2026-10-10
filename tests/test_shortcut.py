import queue
import threading
import time
from pathlib import Path

import kisayol


def test_linux_entry_is_launchable_and_quotes_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(kisayol, "ROOT", Path("/home/a b/sirius"))
    monkeypatch.setattr(kisayol, "LOG", Path("/home/a b/sirius/memory/sirius.log"))
    e = kisayol.linux_desktop_entry("/usr/bin/python3", Path("/x/icon.png"))
    assert e.startswith("[Desktop Entry]") and "Type=Application" in e and "Terminal=false" in e and "Icon=/x/icon.png" in e
    exec_line = [l for l in e.splitlines() if l.startswith("Exec=")][0]
    assert "'/home/a b/sirius'" in exec_line and "main.py --web" in exec_line       # a space in the path must not break the command


def test_create_and_remove_on_linux(tmp_path):
    f = kisayol.create("Linux", tmp_path / "Masaüstü", "/usr/bin/python3", {"png": None})
    assert f.name == "SIRIUS.desktop" and f.exists() and f.stat().st_mode & 0o100
    assert kisayol.main(["--remove", "--desktop", str(tmp_path / "Masaüstü")]) == 0 and not f.exists()


def test_dry_run_touches_nothing(tmp_path):
    d = tmp_path / "desk"
    assert kisayol.main(["--dry-run", "--desktop", str(d)]) == 0 and not d.exists()


def test_mac_command_is_executable_script(tmp_path):
    f = kisayol.create("Darwin", tmp_path, "/usr/bin/python3", {})
    assert f.suffix == ".command" and f.stat().st_mode & 0o100 and f.read_text().startswith("#!/bin/bash")


def test_windows_script_uses_windowless_python_and_escapes_quotes():
    s = kisayol.windows_shortcut_script(Path("C:/Users/O'Neil/Desktop/SIRIUS.lnk"), "C:/Python/python.exe", Path("C:/s/sirius.ico"))
    assert "O''Neil" in s and "--web" in s and "IconLocation" in s and s.endswith("$s.Save()")   # PowerShell single-quote escaping


def test_desktop_dir_prefers_existing_turkish_folder(tmp_path):
    (tmp_path / "Masaüstü").mkdir()
    assert kisayol.desktop_dir("Darwin", tmp_path) == tmp_path / "Masaüstü"
    assert kisayol.desktop_dir("Darwin", tmp_path / "bos") == tmp_path / "bos" / "Desktop"


def test_icons_are_generated():
    ic = kisayol.make_icons()
    assert ic["png"] and ic["png"].stat().st_size > 1000 and ic["ico"].suffix == ".ico"


def test_quit_endpoint_stops_the_process_only_when_wired(tmp_path):
    import http.client, json
    from core.web.server import Server, WebUI
    ui = WebUI()
    s = Server(ui).start()
    def post():
        c = http.client.HTTPConnection("127.0.0.1", s.port, timeout=5)
        c.request("POST", "/api/quit", "{}", {"Host": f"127.0.0.1:{s.port}", "X-Token": s.token, "Content-Length": "2"})
        return json.loads(c.getresponse().read())
    assert post() == {"ok": False}
    hit = threading.Event(); ui.quit = hit.set
    assert post() == {"ok": True} and hit.wait(3)
    c = http.client.HTTPConnection("127.0.0.1", s.port, timeout=5)
    c.request("POST", "/api/quit", "{}", {"Host": f"127.0.0.1:{s.port}", "Content-Length": "2"})
    assert c.getresponse().status == 401                                                # no token, no quit
    s.stop()
