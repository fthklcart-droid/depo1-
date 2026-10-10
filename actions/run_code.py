"""Run Python or a shell command. Always asks the HUMAN first; the model cannot approve it."""
import subprocess
import sys

TIMEOUT = 30


def _run(argv, ctx, what, shell=False):
    if not ctx.confirm(f"{what}"):
        return "The user declined, nothing was run."
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=TIMEOUT, shell=shell)
    except subprocess.TimeoutExpired:
        return f"Stopped after {TIMEOUT}s."
    return (f"exit {r.returncode}\n{r.stdout[-4000:]}{('STDERR:' + r.stderr[-2000:]) if r.stderr else ''}").strip()


def python(p, ctx):
    return _run([sys.executable, "-I", "-c", p["code"]], ctx, "Python kodu çalıştırılsın mı?\n" + p["code"][:600])


def shell(p, ctx):
    return _run(p["command"], ctx, "Komut çalıştırılsın mı?\n" + p["command"][:600], shell=True)


TOOLS = [
    ({"name": "run_python", "description": "Run a Python snippet for calculations, data work or automation; returns stdout. Print what you need.",
      "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}}, python),
    ({"name": "run_shell", "description": "Run a shell command on this computer. Use only when no dedicated tool fits.",
      "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}, shell),
]
