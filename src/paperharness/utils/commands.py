from __future__ import annotations


def quote_command(command: str | None) -> str:
    return command or "missing"
