"""Irreversible-action gate. The answer comes from the human, not from a tool parameter."""
from __future__ import annotations


def cli_confirm(prompt: str) -> bool:
    try:
        answer = input(f"\n⚠️  {prompt}\n   Onaylıyor musun? [e/E=evet, diğer=hayır]: ")
    except (EOFError, KeyboardInterrupt):
        return False
    return answer.strip().lower() in {"e", "evet", "y", "yes"}
