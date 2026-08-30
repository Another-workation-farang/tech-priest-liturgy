"""Themed traceback rendering for .lit frames."""

from __future__ import annotations

import linecache
import sys
import threading
import traceback
import types

from .lexicon import INVERSE
from .sourcemap import SourceMap
from .transform import UnfinishedLitany, split_lines, transform

BANNER_OPEN = "++ MACHINE CURSE ++"
BANNER_CLOSE = "++ the machine spirit is displeased ++"

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
    return INVERSE.get(exc_type.__name__, exc_type.__name__)


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


def _drop_launcher_frames(
    frames: list[traceback.FrameSummary],
) -> list[traceback.FrameSummary]:
    """Drop every frame above the first .lit frame.

    Everything before the user's first Liturgy frame is launcher plumbing by
    definition -- runpy's module-as-main machinery, the console-script
    wrapper, our own loader's exec/compile, and anything a future entry
    point adds. Package-scoped suppression (checking whether a frame's file
    lives inside `liturgy`) only ever caught the frames we happened to know
    about; this subsumes it, since every launcher sits above the first .lit
    frame regardless of where its own file lives.

    Frames *after* the first .lit frame -- e.g. stdlib or third-party code a
    .lit file calls into -- are left untouched.

    If there is no .lit frame at all, there is no launcher to hide relative
    to: the exception never reached Liturgy code, so all frames are kept
    rather than silently discarding the only information available.
    """
    for i, frame in enumerate(frames):
        if frame.filename.endswith(".lit"):
            return frames[i:]
    return frames


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
    if smap is None or frame.colno is None or frame.end_colno is None:
        return
    lead = len(line) - len(line.lstrip())
    start = smap.to_lit(frame.lineno, frame.colno) - lead
    end = smap.to_lit(frame.lineno, frame.end_colno) - lead
    if 0 <= start < end <= len(line.strip()):
        out.append("       " + " " * start + "^" * (end - start))


def _render(
    exc_type: type,
    exc: BaseException,
    tb: types.TracebackType | None,
    file,
) -> None:
    frames = _drop_launcher_frames(traceback.extract_tb(tb))
    out = [BANNER_OPEN]
    for frame in frames:
        if frame.filename.endswith(".lit"):
            _render_lit_frame(frame, out)
        else:
            out.append(
                f'   File "{frame.filename}", line {frame.lineno}, '
                f"in {frame.name}"
            )
            if frame.line:
                out.append(f"       {frame.line}")
    out.append(f"   {curse_name(exc_type)}: {exc}")
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
