"""Themed traceback rendering for .lit frames."""

from __future__ import annotations

import linecache
import sys
import threading
import traceback
import types

from .lexicon import INVERSE
from .sourcemap import SourceMap
from .transform import transform

BANNER_OPEN = "++ MACHINE CURSE ++"
BANNER_CLOSE = "++ the machine spirit is displeased ++"

_map_cache: dict[str, SourceMap | None] = {}


def curse_name(exc_type: type) -> str:
    return INVERSE.get(exc_type.__name__, exc_type.__name__)


def _map_for(path: str) -> SourceMap | None:
    """Lazily build the column map. Only needed when rendering a curse."""
    if path not in _map_cache:
        try:
            src = "".join(linecache.getlines(path))
            if not src:
                with open(path, encoding="utf-8") as fh:
                    src = fh.read()
            _map_cache[path] = transform(src)[1]
        except Exception:
            _map_cache[path] = None
    return _map_cache[path]


def _render_lit_frame(frame: traceback.FrameSummary, out: list[str]) -> None:
    out.append(
        f"   the rite was broken at {frame.filename}, "
        f"line {frame.lineno}, in rite {frame.name}"
    )
    line = linecache.getline(frame.filename, frame.lineno).rstrip("\n")
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
    frames = traceback.extract_tb(tb)
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
