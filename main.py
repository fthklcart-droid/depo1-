"""Entry point. Wires the pieces together and picks a mode; holds no logic of its own.

    python main.py            text assistant in the terminal
    python main.py --live     voice assistant (Gemini Live)
    python main.py --web      the HUD in your browser (add --live for voice)
"""
from core import bootstrap

bootstrap.init()  # must run before anything prints or spawns a process

import argparse  # noqa: E402
import asyncio  # noqa: E402
import sys  # noqa: E402

from core.action_loader import discover  # noqa: E402
from core.config import Config  # noqa: E402
from core.context import Context  # noqa: E402
from core.ui import ConsoleUI  # noqa: E402
from memory.memory_manager import Memory  # noqa: E402


def build_runtime(ui):
    cfg, memory = Config(), Memory()
    ctx = Context(memory=memory, confirm=ui.confirm, notify=ui.write_log,
                  log=lambda m: None)
    reg = discover()
    for fname, err in reg.errors.items():
        ui.write_log(f"SYS: skill {fname} not loaded - {err}")
    return cfg, ctx, reg


def run_text(ui) -> int:
    from core.agent import Agent
    from core.backends import GeminiBackend

    cfg, ctx, reg = build_runtime(ui)
    if not cfg.api_key:
        print("Gemini API anahtarı yok. GEMINI_API_KEY ortam değişkenini ya da config/api_keys.json "
              "içindeki gemini_api_key alanını ayarlayın.")
        return 1
    agent = Agent(GeminiBackend(cfg.api_key), reg, ctx, cfg.get("assistant_name"))
    print(f"{cfg.get('assistant_name')} hazır - {len(reg.tools)} yetenek. /yardim için yazın.")
    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0
        if not line:
            continue
        if line in ("/q", "/quit", "/cik"):
            return 0
        if line in ("/yardim", "/help"):
            print("/tools  yetenekler   /memory  bellek   /undo  geri al   /quit  çık")
        elif line == "/tools":
            print("\n".join(f"- {n}: {t['description'][:90]}" for n, t in sorted(reg.tools.items())))
        elif line == "/memory":
            print(ctx.memory.prompt_block() or "(boş)")
        elif line == "/undo":
            print(ctx.undo.undo())
        else:
            try:
                print(agent.ask(line))
            except Exception as e:  # noqa: BLE001 - a model error must not end the REPL
                print(f"Hata: {e}")


def run_live(ui) -> int:
    from core.live.session import LiveSession

    cfg, ctx, reg = build_runtime(ui)
    if not cfg.api_key:
        print("Gemini API anahtarı yok (GEMINI_API_KEY ya da config/api_keys.json).")
        return 1
    session = LiveSession(ui, reg, ctx, cfg)
    try:
        asyncio.run(session.run())
    except KeyboardInterrupt:
        print("\nKapatılıyor...")
    return 0


def run_web(args) -> int:
    import threading
    import webbrowser

    from core.web.server import Server, WebUI

    ui = WebUI()
    cfg, ctx, reg = build_runtime(ui)
    ctx.log = lambda m: ui.write_log(m[:160]) if m.startswith(("→", "←")) else None
    ui.registry, ui.ctx, ui.cfg = reg, ctx, cfg
    srv = Server(ui, args.port).start()
    print(f"SIRIUS arayüzü: {srv.url}\n(bu adres yalnızca bu bilgisayardan ve bu oturum için çalışır)")
    if not args.no_browser:
        webbrowser.open(srv.url)
    if not cfg.api_key:
        ui.write_log("SYS: Gemini API anahtarı yok; Bağlantılar çalışır ama sohbet kapalı.")
        threading.Event().wait()
    if args.live:
        from core.live.session import LiveSession
        session = LiveSession(ui, reg, ctx, cfg)
        ui.say = session.send_text
        try:
            asyncio.run(session.run())
        except KeyboardInterrupt:
            pass
        return 0
    from core.agent import Agent
    from core.backends import GeminiBackend
    ui.ask = Agent(GeminiBackend(cfg.api_key), reg, ctx, cfg.get("assistant_name")).ask
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\nKapatılıyor...")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kişisel yapay zekâ asistanı")
    ap.add_argument("--live", action="store_true", help="sesli mod (Gemini Live)")
    ap.add_argument("--web", action="store_true", help="arayüzü tarayıcıda aç")
    ap.add_argument("--port", type=int, default=0, help="web arayüzü portu (varsayılan: boş bir port)")
    ap.add_argument("--no-browser", action="store_true", help="tarayıcıyı otomatik açma")
    args = ap.parse_args(argv)
    if args.web:
        return run_web(args)
    ui = ConsoleUI()
    return run_live(ui) if args.live else run_text(ui)


if __name__ == "__main__":
    sys.exit(main())
