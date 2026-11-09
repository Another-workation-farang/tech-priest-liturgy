"""Themed traceback rendering for .lit frames."""

from __future__ import annotations

import linecache
import os
import sys
import threading
import traceback

from . import rubric
from .compiler import _PASSES
from .lexicon import INVERSE
from .rubric import (
    BANNER_CLOSE,
    BANNER_OPEN,
    CAUSE_SEPARATOR,
    CONTEXT_SEPARATOR,
)
from .sourcemap import SourceMap, char_offset
from .transform import UnfinishedLitany, split_lines, transform

SUFFIX = ".lit"

# Our own compile path, for the plumbing filter below.
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))

# The generated Python and its column map, cached together: rendering a
# caret needs both. See `_transformed`.
_map_cache: dict[str, tuple[list[str], SourceMap | None]] = {}

# The exact source compiled for a given path, recorded at the moment of
# compilation by the loader and by chant(). This is the only place the truly
# executed source is known for certain -- linecache re-reads the file lazily
# and will happily show whatever currently sits on disk, which drifts the
# instant a persistent process's .lit file is edited after import. Preferring
# the recorded source keeps that drift out of the correctness path; linecache
# and the filesystem remain only as a fallback for paths nothing recorded.
_source_cache: dict[str, str] = {}


def record_source(path: str, src: str) -> None:
    """Record the exact source compiled for `path`.

    Call this at the moment of compilation -- from `LiturgyLoader.
    source_to_code`, from `chant()`, and from the commune prompt -- so a
    later curse render reflects what actually ran, not whatever the file
    currently contains on disk. A recorded path need not exist on disk at
    all: the prompt records each entry under a virtual name, which is what
    lets a curse quote what was typed there.
    """
    _source_cache[path] = src
    _map_cache.pop(path, None)


def forget_source(path: str) -> None:
    """Drop a recorded source. The commune prompt retires old entries with
    this so an arbitrarily long session does not grow the cache without
    bound; forgetting a real file merely falls back to reading it."""
    _source_cache.pop(path, None)
    _map_cache.pop(path, None)


def _is_litany(filename: str) -> bool:
    """Is `filename` Liturgy -- a .lit path, or a recorded virtual source?

    Everything rendering-related branches on this rather than on the
    suffix alone: an entry typed at the commune prompt has no file and no
    suffix, but its source is recorded, and quoting the generated Python
    at someone who typed Liturgy was the old behaviour this replaces.
    """
    return filename.endswith(SUFFIX) or filename in _source_cache



def curse_name(exc_type: type) -> str:
    """The themed name for an exception type. See `rubric.curse_name`."""
    return rubric.curse_name(exc_type, INVERSE)



def _read_source(path: str) -> str:
    """The best available source text for `path`.

    Prefers the exact source recorded at compile time; falls back to
    linecache (which may already be stale) and then a direct read, for
    paths nothing ever recorded.
    """
    src = _source_cache.get(path)
    if src is not None:
        return src
    src = "".join(linecache.getlines(path))
    if src:
        return src
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _transformed(path: str) -> tuple[list[str], SourceMap | None]:
    """The generated Python and its column map. Lazy; only a curse needs it.

    Both come from one `transform`, and both are needed to place a caret:
    `traceback` reports `colno`/`end_colno` as UTF-8 *byte* offsets into the
    generated Python line, while every column the SourceMap speaks is a
    character offset. Converting one to the other requires the very line the
    byte offset indexes into.

    Must run the same passes `compiler` actually compiled with, `_PASSES` --
    including `carrier_pass`. A `consecrated` (or other construct) header
    line is itself an executable statement, so a runtime frame can point
    straight at it; mapping that line's columns with only the default passes
    leaves the map off by the carrier's width delta.
    """
    if path not in _map_cache:
        try:
            out = transform(_read_source(path), _PASSES)
            _map_cache[path] = (split_lines(out.python), out.source_map)
        except UnfinishedLitany as err:
            # Source that never finishes tokenising still has a usable map
            # for everything before the failure -- which is where the caret
            # for that very failure belongs. The generated text does not
            # survive on the exception; `char_offset` reads an empty line as
            # "nothing to measure against" and passes the offset through.
            _map_cache[path] = ([], err.sourcemap)
        except Exception:
            _map_cache[path] = ([], None)
    return _map_cache[path]


def _map_for(path: str) -> SourceMap | None:
    return _transformed(path)[1]


def _py_line_for(path: str, lineno: int) -> str:
    """The generated-Python line `traceback`'s byte columns index into."""
    lines = _transformed(path)[0]
    return lines[lineno - 1] if 1 <= lineno <= len(lines) else ""


def _line_for(path: str, lineno: int) -> str:
    """The source line actually executed, without its trailing newline.

    Prefers the recorded source over linecache for the same staleness
    reason as `_map_for`. Returns "" if the line is unavailable by any
    means, which callers treat as "render nothing further for this frame".
    """
    src = _source_cache.get(path)
    if src is not None:
        lines = split_lines(src)
        if 1 <= lineno <= len(lines):
            return lines[lineno - 1].rstrip("\n")
        return ""
    return linecache.getline(path, lineno).rstrip("\n")



def _is_plumbing(frame: traceback.FrameSummary) -> bool:
    """Is this frame the import system, or our own compile path?

    A .lit frame is never plumbing, however it got there -- a litany that
    somehow lives inside the package directory is still the user's code.
    """
    if _is_litany(frame.filename):
        return False
    if frame.filename.startswith("<frozen importlib."):
        return True
    return os.path.abspath(frame.filename).startswith(_PACKAGE_DIR + os.sep)



class _LiveSeer:
    """Places frames by the recorded sources and sourcemaps of this process."""

    def is_litany(self, filename: str) -> bool:
        return _is_litany(filename)

    def is_plumbing(self, frame: traceback.FrameSummary) -> bool:
        return _is_plumbing(frame)

    def place(self, frame: traceback.FrameSummary) -> rubric.Placement:
        path, lineno = frame.filename, frame.lineno
        line = _line_for(path, lineno)
        smap = _map_for(path) if line else None
        if smap is None or frame.colno is None:
            return path, lineno, line, None
        # colno/end_colno are UTF-8 byte offsets into the *generated Python*
        # line, so they have to be converted against that line -- not the
        # Liturgy one -- before the SourceMap, which counts characters, sees
        # them. Without this a single multi-byte character earlier on the line
        # slides the caret right by its extra bytes, or off the end entirely.
        py_line = _py_line_for(path, lineno)
        start = smap.to_lit(lineno, char_offset(py_line, frame.colno))
        if frame.end_lineno is not None and frame.end_lineno != lineno:
            # end_colno is a column on end_lineno, not on this line: the
            # expression runs off the end. Underline to the end of what we
            # print rather than dropping the caret.
            end = len(line.rstrip())
        elif frame.end_colno is None:
            end = start + 1
        else:
            end = smap.to_lit(lineno, char_offset(py_line, frame.end_colno))
        return path, lineno, line, (start, end)

    def place_syntax(self, exc: SyntaxError) -> rubric.Placement:
        filename = exc.filename or "<unknown>"
        lineno = exc.lineno
        # exc.text is the generated Python, which is not what the author
        # wrote. Prefer the recorded Liturgy, and map the column back to it;
        # fall back to exc.text unmapped, since then the columns describe
        # what we print.
        line = _line_for(filename, lineno)
        if not line:
            return (
                filename,
                lineno,
                (exc.text or "").rstrip("\n"),
                rubric.syntax_span(exc),
            )
        span = rubric.syntax_span(exc)
        smap = _map_for(filename)
        if span is not None and smap is not None:
            span = (smap.to_lit(lineno, span[0]), smap.to_lit(lineno, span[1]))
        return filename, lineno, line, span


_SEER = _LiveSeer()


def render_curse(exc_type, exc, tb, *, file=None) -> None:
    """Never raises. A failing excepthook would destroy the original error."""
    rubric.render(
        exc_type, exc, tb, seer=_SEER, names=INVERSE, file=file or sys.stderr
    )


def _thread_hook(args) -> None:
    render_curse(args.exc_type, args.exc_value, args.exc_traceback)


def install() -> None:
    sys.excepthook = render_curse
    threading.excepthook = _thread_hook


def uninstall() -> None:
    sys.excepthook = sys.__excepthook__
    threading.excepthook = threading.__excepthook__
