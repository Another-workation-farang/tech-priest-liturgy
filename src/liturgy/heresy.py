"""Rebukes for invoking a rite by its mundane name."""

from __future__ import annotations

import json
import os
import sys
import tempfile
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
    """Increment and persist the offence count. Never raises.

    Note: concurrent writes may lose increments (count race accepted on
    cosmetic escalation counter). Write is atomic (via temp + rename).
    """
    try:
        path = state_path()
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}
        # Verify data is a dict and can be processed safely.
        if not isinstance(data, dict):
            data = {}
        # Coerce the value safely; treat anything non-numeric as absent.
        try:
            current = int(data.get(alias, 0))
        except (TypeError, ValueError):
            current = 0
        count = current + 1
    except (OSError, json.JSONDecodeError, TypeError, ValueError, AttributeError):
        # Corruption or I/O error; start fresh.
        data = {}
        count = 1

    data[alias] = count

    # Atomic write: temp file then replace.
    try:
        path = state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temporary file in the same directory for atomicity.
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, text=True)
        try:
            with os.fdopen(fd, 'w') as tmp:
                tmp.write(json.dumps(data))
            os.replace(tmp_path, path)
        except Exception:
            # Clean up temp file on failure.
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception:
        pass  # the joke must never break the CLI

    return count


def rebuke(alias: str, proper: str, *, stream=None) -> None:
    # LITURGY_PIOUS must be exactly "0" to silence (not "false", "", etc.).
    if os.environ.get("LITURGY_PIOUS") == "0":
        return
    stream = stream if stream is not None else sys.stderr
    count = _bump(alias)
    message = REBUKES[min(count, len(REBUKES)) - 1].format(proper=proper.upper())
    print("++ TECH-HERESY DETECTED ++", file=stream)
    print(f"++ {message} ++", file=stream)
