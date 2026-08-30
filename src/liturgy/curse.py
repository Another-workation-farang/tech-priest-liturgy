"""Themed traceback rendering for .lit frames."""

from __future__ import annotations

import builtins
import linecache
import os
import sys
import threading
import traceback
import types

from .lexicon import INVERSE
from .sourcemap import SourceMap
from .transform import UnfinishedLitany, split_lines, transform

BANNER_OPEN = "++ MACHINE CURSE ++"
BANNER_CLOSE = "++ the machine spirit is displeased ++"

# The separators traceback.format_exception writes between chained
# exceptions, in the local dialect. Losing the chain loses the root cause.
CAUSE_SEPARATOR = "   ++ the curse above was the direct cause of the next ++"
CONTEXT_SEPARATOR = (
    "   ++ whilst enduring the curse above, another was invoked ++"
)

SUFFIX = ".lit"

# Our own compile path, for the plumbing filter below.
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))

# MachineCurse and PrimalCurse are the names of `Exception` and
# `BaseException` themselves, not of everything descended from them. An MRO
# walk that ran through to the root would rename every unaliased builtin --
# IndentationError, PermissionError -- to the least informative word we have.
_CATCH_ALL_ANCESTORS = frozenset({"Exception", "BaseException", "object"})

_map_cache: dict[str, SourceMap | None] = {}

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
    source_to_code` and from `chant()` -- so a later curse render reflects
    what actually ran, not whatever the file currently contains on disk.
    """
    _source_cache[path] = src
    _map_cache.pop(path, None)


def curse_name(exc_type: type) -> str:
    """The themed name for an exception type.

    Exact matches first, then the MRO: `ModuleNotFoundError` is the
    commonest import failure there is, and an exact-name lookup left it
    rendering un-themed inside a themed curse. It is an `ImportError`, so it
    is `ForbiddenLore`.

    The MRO walk applies only to types in the builtin hierarchy. A library's
    or a user's own exception keeps its own name -- calling
    `json.JSONDecodeError` an `ImpureOffering` because it happens to derive
    from `ValueError` would hide the informative half of the name.
    """
    name = INVERSE.get(exc_type.__name__)
    if name is not None:
        return name
    if getattr(builtins, exc_type.__name__, None) is exc_type:
        for base in exc_type.__mro__[1:]:
            if base.__name__ in _CATCH_ALL_ANCESTORS:
                break
            name = INVERSE.get(base.__name__)
            if name is not None:
                return name
    return exc_type.__name__


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


def _map_for(path: str) -> SourceMap | None:
    """Lazily build the column map. Only needed when rendering a curse."""
    if path not in _map_cache:
        try:
            _map_cache[path] = transform(_read_source(path))[1]
        except UnfinishedLitany as err:
            # Source that never finishes tokenising still has a usable map
            # for everything before the failure -- which is where the caret
            # for that very failure belongs.
            _map_cache[path] = err.sourcemap
        except Exception:
            _map_cache[path] = None
    return _map_cache[path]


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


def _lit_location(exc: BaseException | None) -> str | None:
    """The .lit file an exception points at by itself, if any.

    `SyntaxError` and `OSError` both name a file directly. When one of them
    names a `.lit` file and no frame does -- a litany that failed to compile,
    or a mistyped path handed to `chant` -- that filename is the anchor the
    launcher frames sit above.
    """
    filename = getattr(exc, "filename", None)
    if isinstance(filename, str) and filename.endswith(SUFFIX):
        return filename
    return None


def _drop_launcher_frames(
    frames: list[traceback.FrameSummary],
    *,
    anchored: bool = False,
) -> list[traceback.FrameSummary]:
    """Drop launcher frames above the first .lit frame, and plumbing anywhere.

    Two rules, because neither covers the other:

    *Positionally*, everything before the user's first Liturgy frame is
    launcher plumbing by definition -- runpy's module-as-main machinery, the
    console-script wrapper, and anything a future entry point adds. Those sit
    above the first .lit frame wherever their own files live, so no
    package-scoped check would catch them all.

    *By origin*, the import system and our own compile path can also appear
    strictly between two .lit frames, which the positional rule cannot reach:
    when one litany invokes another that will not compile, the frames for
    `_find_and_load`, `exec_module` and `transform` land between the invoking
    line and the fault. CPython hides its equivalents for the same .py case,
    and so do we.

    Frames after the first .lit frame that belong to neither category -- the
    stdlib or third-party code a litany calls into -- are left untouched, and
    a .lit frame is never dropped.

    If there is no .lit frame at all, there is no launcher to hide relative
    to: the exception never reached Liturgy code, so all frames are kept
    rather than silently discarding the only information available -- unless
    `anchored`, meaning the exception names a .lit file itself (see
    `_lit_location`). Then the litany is the subject even though it never ran
    a line, and every frame present is plumbing that got us to it.
    """
    for i, frame in enumerate(frames):
        if frame.filename.endswith(SUFFIX):
            return [f for f in frames[i:] if not _is_plumbing(f)]
    return [] if anchored else frames


def _is_plumbing(frame: traceback.FrameSummary) -> bool:
    """Is this frame the import system, or our own compile path?

    A .lit frame is never plumbing, however it got there -- a litany that
    somehow lives inside the package directory is still the user's code.
    """
    if frame.filename.endswith(SUFFIX):
        return False
    if frame.filename.startswith("<frozen importlib."):
        return True
    return os.path.abspath(frame.filename).startswith(_PACKAGE_DIR + os.sep)


def _render_caret(
    line: str, start: int, end: int, out: list[str]
) -> None:
    """Underline columns [start, end) of `line` as it is printed (stripped)."""
    stripped = line.strip()
    lead = len(line) - len(line.lstrip())
    start -= lead
    end = min(end - lead, len(stripped))
    if end <= start:
        end = start + 1
    if 0 <= start < end <= len(stripped):
        out.append("       " + " " * start + "^" * (end - start))


def _render_lit_frame(frame: traceback.FrameSummary, out: list[str]) -> None:
    if frame.name == "<module>":
        out.append(
            f"   the rite was broken at the threshold of {frame.filename}, "
            f"line {frame.lineno}"
        )
    else:
        out.append(
            f"   the rite was broken at {frame.filename}, "
            f"line {frame.lineno}, in rite {frame.name}"
        )
    line = _line_for(frame.filename, frame.lineno)
    if not line:
        return
    out.append(f"       {line.strip()}")

    smap = _map_for(frame.filename)
    if smap is None or frame.colno is None:
        return
    start = smap.to_lit(frame.lineno, frame.colno)
    if frame.end_lineno is not None and frame.end_lineno != frame.lineno:
        # end_colno is a column on end_lineno, not on this line: the
        # expression runs off the end. Underline to the end of what we print
        # rather than dropping the caret, which is what comparing the two
        # lines' columns used to do.
        end = len(line.rstrip())
    elif frame.end_colno is None:
        end = start + 1
    else:
        end = smap.to_lit(frame.lineno, frame.end_colno)
    _render_caret(line, start, end, out)


def _render_syntax_location(exc: SyntaxError, out: list[str]) -> None:
    """Render the location a SyntaxError carries instead of a frame.

    A litany that fails to compile never runs a line, so it has no traceback
    frame of its own: walking `extract_tb` alone produced no .lit frame, no
    source line and no caret -- strictly worse than the plain Python
    traceback for the single commonest class of error. The location lives on
    the exception.
    """
    filename = exc.filename or "<unknown>"
    lineno = exc.lineno
    is_lit = filename.endswith(SUFFIX)
    if is_lit:
        out.append(f"   the rite was ill-written at {filename}, line {lineno}")
    else:
        out.append(f'   File "{filename}", line {lineno}')

    # exc.text is the generated Python, which is not what the author wrote.
    # Prefer the recorded Liturgy, and map the column back to it; fall back
    # to exc.text unmapped, since then the columns describe what we print.
    line = _line_for(filename, lineno) if is_lit else ""
    smap = _map_for(filename) if line else None
    if not line:
        line = (exc.text or "").rstrip("\n")
    if not line:
        return
    out.append(f"       {line.strip()}")

    if not exc.offset or exc.offset < 1:
        return
    start = exc.offset - 1
    if exc.end_offset and exc.end_lineno == lineno and exc.end_offset > exc.offset:
        end = exc.end_offset - 1
    else:
        end = start + 1
    if smap is not None:
        start = smap.to_lit(lineno, start)
        end = smap.to_lit(lineno, end)
    _render_caret(line, start, end, out)


def _exception_message(exc: BaseException | None) -> str:
    if isinstance(exc, SyntaxError) and exc.msg:
        # str() would append "(file.lit, line N)", which we have just
        # rendered properly above.
        return str(exc.msg)
    return str(exc)


def _render_one(
    exc_type: type,
    exc: BaseException | None,
    tb: types.TracebackType | None,
    out: list[str],
) -> None:
    frames = _drop_launcher_frames(
        traceback.extract_tb(tb), anchored=_lit_location(exc) is not None
    )
    for frame in frames:
        if frame.filename.endswith(SUFFIX):
            _render_lit_frame(frame, out)
        else:
            out.append(
                f'   File "{frame.filename}", line {frame.lineno}, '
                f"in {frame.name}"
            )
            if frame.line:
                out.append(f"       {frame.line}")
    if isinstance(exc, SyntaxError) and exc.lineno is not None:
        _render_syntax_location(exc, out)
    out.append(f"   {curse_name(exc_type)}: {_exception_message(exc)}")


def _render_chain(
    exc_type: type,
    exc: BaseException | None,
    tb: types.TracebackType | None,
    out: list[str],
    seen: set[int],
) -> None:
    """Render `exc` preceded by whatever it was raised from.

    `__cause__`/`__context__` used to be discarded silently, so
    `proclaim MotiveFailure(...) within exc` showed the MotiveFailure and
    nothing of the DivisionByTheVoid underneath it. Losing the root cause is
    a real regression against plain Python, which is the bar this project
    set itself.
    """
    # Collect the chain outermost-first, iteratively: it can be arbitrarily
    # long, and recursing down it would trade a rendered curse for a
    # RecursionError. Each link carries the separator that introduces it,
    # which is exactly the link's relationship to the one beneath it.
    links: list[
        tuple[type, BaseException | None, types.TracebackType | None, str | None]
    ] = []
    while True:
        if exc is not None:
            if id(exc) in seen:
                break
            seen.add(id(exc))
        cause = getattr(exc, "__cause__", None)
        context = (
            None
            if exc is None or exc.__suppress_context__
            else exc.__context__
        )
        beneath = cause if cause is not None else context
        separator = None
        if beneath is not None:
            separator = (
                CAUSE_SEPARATOR if cause is not None else CONTEXT_SEPARATOR
            )
        links.append((exc_type, exc, tb, separator))
        if beneath is None:
            break
        exc_type, exc, tb = type(beneath), beneath, beneath.__traceback__

    for exc_type, exc, tb, separator in reversed(links):
        if separator is not None:
            out.append(separator)
        _render_one(exc_type, exc, tb, out)
        if isinstance(exc, BaseExceptionGroup):
            # Groups nest by containment, not by chaining, and shallowly.
            total = len(exc.exceptions)
            for i, sub in enumerate(exc.exceptions, 1):
                out.append(
                    f"   ++ curse {i} of {total} bound within the above ++"
                )
                _render_chain(type(sub), sub, sub.__traceback__, out, seen)


def _render(
    exc_type: type,
    exc: BaseException,
    tb: types.TracebackType | None,
    file,
) -> None:
    out = [BANNER_OPEN]
    _render_chain(exc_type, exc, tb, out, set())
    out.append(BANNER_CLOSE)
    print("\n".join(out), file=file)


def render_curse(exc_type, exc, tb, *, file=None) -> None:
    """Never raises. A failing excepthook would destroy the original error."""
    try:
        _render(exc_type, exc, tb, file or sys.stderr)
    except Exception:
        sys.__excepthook__(exc_type, exc, tb)


def _thread_hook(args) -> None:
    render_curse(args.exc_type, args.exc_value, args.exc_traceback)


def install() -> None:
    sys.excepthook = render_curse
    threading.excepthook = _thread_hook


def uninstall() -> None:
    sys.excepthook = sys.__excepthook__
    threading.excepthook = threading.__excepthook__
