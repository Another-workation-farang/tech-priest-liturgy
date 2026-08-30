"""Interactive Liturgy session."""

from __future__ import annotations

import code
import sys
import tokenize

from .transform import transform

BANNER = (
    "++ COMMUNION ESTABLISHED ++\n"
    f"++ cogitator {sys.version.split()[0]} attends your litanies ++"
)
FAREWELL = "++ communion ended. the Omnissiah is served. ++"


class LiturgyConsole(code.InteractiveConsole):
    def runsource(self, source, filename="<commune>", symbol="single"):
        try:
            py, _smap = transform(source)
        except tokenize.TokenError:
            # Unterminated bracket or string: not an error, just unfinished.
            return True
        except IndentationError:
            return True
        except SyntaxError:
            self.showsyntaxerror(filename)
            return False

        try:
            compiled = self.compile(py, filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            self.showsyntaxerror(filename)
            return False

        if compiled is None:
            return True  # incomplete

        self.runcode(compiled)
        return False


def commune(banner: str | None = None) -> int:
    console = LiturgyConsole()
    console.interact(
        banner=BANNER if banner is None else banner, exitmsg=FAREWELL
    )
    return 0
