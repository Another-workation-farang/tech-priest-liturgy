"""Interactive Liturgy session."""

from __future__ import annotations

import code
import os
import sys

from .compiler import _PASSES, compile_litany
from .constructs import TechHeresy
from .curse import forget_source, record_source
from .loader import install as install_hook
from .transform import UnfinishedLitany, transform

# How many prompt entries stay recorded for curse rendering. A rite defined
# this many entries ago still gets its source quoted in a traceback; beyond
# that the frame renders plain, which is where the standard REPL starts.
# Keeps an arbitrarily long session from growing the source cache unbounded.
_REMEMBERED = 1000

BANNER = (
    "++ COMMUNION ESTABLISHED ++\n"
    f"++ cogitator {sys.version.split()[0]} attends your litanies ++"
)
FAREWELL = "++ communion ended. the Omnissiah is served. ++"


class LiturgyConsole(code.InteractiveConsole):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._entry = 0

    def runsource(self, source, filename="<commune>", symbol="single"):
        # Each entry compiles under its own virtual name, and its exact
        # source is recorded under that name before anything can fail.
        # That is what lets a curse -- syntax or runtime, this entry or a
        # rite defined many entries ago -- quote the Liturgy that was
        # typed, instead of the generated Python or nothing at all. The
        # passed `filename` (the console's fixed "<console>") is unused:
        # one shared name cannot tell two entries' sources apart.
        #
        # The number advances only when an entry *completes*: while a
        # multi-line block is still being typed, every continuation call
        # re-records the growing buffer under the same name, so partial
        # buffers neither burn retention slots nor linger once superseded.
        del filename
        name = f"<commune:{self._entry + 1}>"
        record_source(name, source)
        more = self._entry_result(source, name, symbol)
        if not more:
            self._entry += 1
            forget_source(f"<commune:{self._entry - _REMEMBERED}>")
        return more

    def _entry_result(self, source, name, symbol):
        """True if `source` is an unfinished entry; run or report it if not."""
        try:
            # _PASSES, not the default: the alias pass alone leaves every
            # construct header unparseable, so the incompleteness probe
            # below would report `consecrated PORT = 8080` as a syntax
            # error and compile_litany would never be reached.
            py, _smap = transform(source, _PASSES, filename=name)
        except UnfinishedLitany:
            # Unterminated bracket or string: not an error, just unfinished.
            # transform() reports this as a SyntaxError subclass so file
            # callers need no special case; only a prompt can ask for more.
            return True
        except TechHeresy as err:
            # The carrier pass cannot know what "file" it is reading; fill
            # in the entry's name the same way `compiler` does for real
            # files, so the curse can anchor and quote it.
            if err.filename in (None, "<unknown>"):
                err.filename = name
            self.showsyntaxerror()
            return False
        except SyntaxError:
            # tokenize never raises this for genuinely incomplete input --
            # an open block tokenizes cleanly, and incompleteness is only
            # decided afterwards by compile() returning None below. Any
            # SyntaxError here (including IndentationError/TabError, e.g. a
            # dedent that doesn't match an outer indentation level) is a
            # complete, unrecoverable error and must be reported, not
            # buffered.
            self.showsyntaxerror()
            return False

        # The probe answers exactly one question -- is this entry finished?
        # A complete-but-wrong entry is NOT reported from here: the probe's
        # error describes the generated Python, and compile_litany below
        # re-raises the same fault located against the recorded Liturgy.
        try:
            if self.compile(py, name, symbol) is None:
                return True  # incomplete
        except (OverflowError, SyntaxError, ValueError):
            pass  # complete, and wrong: let compile_litany say so

        try:
            compiled = compile_litany(source, name, mode=symbol)
        except (OverflowError, SyntaxError, ValueError):
            self.showsyntaxerror()
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
