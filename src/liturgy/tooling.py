"""The Spec III verbs: augur, transcribe, purge."""

from __future__ import annotations

import pathlib
import sys

from .collisions import find_collisions
from .compiler import compile_litany
from .transform import UnfinishedLitany, split_lines

_SOURCES = (".lit", ".py")


def _gather(
    paths: list[str],
) -> tuple[list[pathlib.Path], list[pathlib.Path]]:
    """Files to read, expanding directories to the sources we understand.

    Returns `(files, unscanned_dirs)`. `rglob` lists a symlinked directory
    itself but does not descend into it -- true through this project's 3.12
    floor; the glob methods only grew a `recurse_symlinks` keyword in 3.13.
    So a `.lit`/`.py` file reachable only through one is invisible to a
    plain walk, and reporting the tree clean without a word about it would
    be the one thing a linter must not do: claiming to have read what it
    never saw. Each such directory is named instead, in `unscanned_dirs`,
    so the caller can say so rather than silently skip it. (The path the
    caller names directly is never itself skipped this way, symlink or not
    -- `rglob` walks *from* it regardless; the gap is only for a symlinked
    directory met partway through the walk.)
    """
    files: list[pathlib.Path] = []
    unscanned_dirs: list[pathlib.Path] = []
    for raw in paths:
        p = pathlib.Path(raw)
        if p.is_dir():
            entries = list(p.rglob("*"))
            files.extend(
                sorted(f for f in entries if f.suffix in _SOURCES and f.is_file())
            )
            unscanned_dirs.extend(
                sorted(d for d in entries if d.is_dir() and d.is_symlink())
            )
        else:
            files.append(p)
    return files, unscanned_dirs


def _report(path, line, src_line, col, width, message, *, out) -> None:
    print("++ THE OMENS ARE TROUBLED ++", file=out)
    print(f"   {path}, line {line}", file=out)
    if src_line:
        print(f"       {src_line}", file=out)
        print(f"       {' ' * col}{'^' * max(width, 1)}", file=out)
    print(f"   {message}", file=out)


def augur(paths: list[str], *, plain: bool = False, out=None) -> int:
    """Read litanies for faults without chanting them. 0 clean, 1 findings."""
    out = out if out is not None else sys.stdout
    troubled = False

    files, unscanned_dirs = _gather(paths)

    for d in unscanned_dirs:
        troubled = True
        _emit_bare(
            d, "symlinked directory: not descended into, not scanned",
            plain=plain, out=out,
        )

    for path in files:
        try:
            src = path.read_text(encoding="utf-8")
        except OSError as err:
            troubled = True
            _emit_bare(path, f"cannot be read: {err.strerror}", plain=plain, out=out)
            continue

        liturgy = path.suffix == ".lit"
        try:
            collisions = find_collisions(src, str(path), liturgy=liturgy)
        except UnfinishedLitany:
            troubled = True
            _emit_bare(
                path, "omens unread: the litany does not tokenise",
                plain=plain, out=out,
            )
            continue
        except SyntaxError as err:
            troubled = True
            _emit_bare(
                path, f"{type(err).__name__}: {err.msg}",
                line=err.lineno or 1, plain=plain, out=out,
            )
            continue

        if liturgy:
            # Compiling is what makes augur agree with chant. Collisions are
            # already in hand, so a failure here is something else entirely.
            try:
                compile_litany(src, str(path))
            except SyntaxError as err:
                troubled = True
                _emit_bare(
                    path, f"{type(err).__name__}: {err.msg}",
                    line=err.lineno or 1, plain=plain, out=out,
                )

        lines = split_lines(src)
        for c in collisions:
            troubled = True
            note = f"{c.word} is reserved; it becomes {c.target}"
            if c.quiet:
                note += " -- silently"
            if plain:
                print(f"{path}:{c.line}:{c.col + 1}: {note}", file=out)
            else:
                text = lines[c.line - 1].rstrip("\n") if c.line <= len(lines) else ""
                _report(path, c.line, text, c.col, len(c.word), note, out=out)

    return 1 if troubled else 0


def _emit_bare(path, message, *, line: int = 1, plain: bool, out) -> None:
    if plain:
        print(f"{path}:{line}:1: {message}", file=out)
    else:
        _report(path, line, "", 0, 0, message, out=out)
