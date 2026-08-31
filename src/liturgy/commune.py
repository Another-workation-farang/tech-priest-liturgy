"""Interactive Liturgy session."""

from __future__ import annotations

import code
import os
import sys

from .compiler import compile_litany
from .loader import install as install_hook
from .transform import UnfinishedLitany, transform

BANNER = (
    "++ COMMUNION ESTABLISHED ++\n"
    f"++ cogitator {sys.version.split()[0]} attends your litanies ++"
)
FAREWELL = "++ communion ended. the Omnissiah is served. ++"


class LiturgyConsole(code.InteractiveConsole):
    def runsource(self, source, filename="<commune>", symbol="single"):
        try:
            py, _smap = transform(source)
        except UnfinishedLitany:
            # Unterminated bracket or string: not an error, just unfinished.
            # transform() reports this as a SyntaxError subclass so file
            # callers need no special case; only a prompt can ask for more.
            return True
        except SyntaxError:
            # tokenize never raises this for genuinely incomplete input --
            # an open block tokenizes cleanly, and incompleteness is only
            # decided afterwards by compile() returning None below. Any
            # SyntaxError here (including IndentationError/TabError, e.g. a
            # dedent that doesn't match an outer indentation level) is a
            # complete, unrecoverable error and must be reported, not
            # buffered.
            self.showsyntaxerror(filename)
            return False

        try:
            compiled = self.compile(py, filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            self.showsyntaxerror(filename)
            return False

        if compiled is None:
            return True  # incomplete

        try:
            compiled = compile_litany(source, filename, mode=symbol)
        except SyntaxError:
            self.showsyntaxerror(filename)
            return False

        self.runcode(compiled)
        return False


def commune(banner: str | None = None) -> int:
    # The REPL is the natural place to poke at a .lit module you just wrote,
    # so it needs the import hook as much as chant does. install() is
    # idempotent and only ever registered from an entry point.
    install_hook()
    # `python` prepends the working directory when it drops into its REPL;
    # a console script's sys.path[0] is the script's own bin directory, so
    # without this the installed `liturgy commune` cannot import anything
    # from the directory the user is standing in -- .lit or .py alike.
    cwd = os.getcwd()
    if "" not in sys.path and cwd not in sys.path:
        sys.path.insert(0, cwd)
    console = LiturgyConsole()
    console.interact(
        banner=BANNER if banner is None else banner, exitmsg=FAREWELL
    )
    return 0
