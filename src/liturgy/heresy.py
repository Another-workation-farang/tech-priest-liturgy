"""Rebukes for invoking a rite by its mundane name."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REBUKES = [
    "this rite is named {proper}. the omission is noted.",
    "this rite is named {proper}. the transgression is recorded in your "
    "permanent record.",
    "this rite is named {proper}. the Inquisition has been notified.",
]


def state_path() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")
    return Path(base) / "liturgy" / "heresies.json"


def _bump(alias: str) -> int:
    """Increment and persist the offence count. Never raises."""
    try:
        path = state_path()
        data = json.loads(path.read_text()) if path.exists() else {}
    except Exception:
        return 1
    count = int(data.get(alias, 0)) + 1
    data[alias] = count
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
    except Exception:
        pass  # the joke must never break the CLI
    return count


def rebuke(alias: str, proper: str, *, stream=None) -> None:
    if os.environ.get("LITURGY_PIOUS") == "0":
        return
    stream = stream if stream is not None else sys.stderr
    count = _bump(alias)
    message = REBUKES[min(count, len(REBUKES)) - 1].format(proper=proper.upper())
    print("++ TECH-HERESY DETECTED ++", file=stream)
    print(f"++ {message} ++", file=stream)
