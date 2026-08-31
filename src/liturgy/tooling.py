"""The Spec III verbs: augur, transcribe, purge."""

from __future__ import annotations

import importlib.util
import pathlib
import sys

from .collisions import find_collisions
from .compiler import compile_litany
from .reverse import to_liturgy
from .transform import UnfinishedLitany, split_lines, transform

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


def _newline_style(raw: bytes) -> str:
    """The line ending `raw` was written with, so the output can keep it.

    `decode_source` (like `read_text`) performs universal-newline
    translation on the way in, so by the time `src` exists as `str` the
    original bytes' line endings are gone and the round-trip self-check --
    which compares that already-normalised text against `back` -- cannot
    see a CRLF-to-LF change happen underneath it. Detecting the style here,
    from the untranslated bytes, and re-applying it to the output at the
    very end is what keeps the written file's *bytes*, not just its text,
    faithful to the source -- rewriting a user's line endings without a
    word about it is exactly the kind of silent lie `transcribe` exists to
    refuse elsewhere.
    """
    return "\r\n" if b"\r\n" in raw else "\n"


def transcribe(source: str, dest: str | None = None, *, out=None) -> int:
    """Render a Python file into Liturgy. 0 written, 1 refused."""
    out = out if out is not None else sys.stdout
    path = pathlib.Path(source)

    try:
        raw = path.read_bytes()
    except OSError as err:
        print(f"++ CANNOT TRANSCRIBE: {path} {err.strerror} ++", file=out)
        return 1

    # decode_source, not read_text(encoding="utf-8"): it honours a UTF-8 BOM
    # and a PEP 263 `coding:` cookie, so a latin-1 or BOM'd source decodes
    # the same way the import path decodes it, instead of being reported as
    # a bogus SyntaxError or crashing outright.
    try:
        src = importlib.util.decode_source(raw)
    except (SyntaxError, UnicodeDecodeError, LookupError) as err:
        print(f"++ CANNOT TRANSCRIBE: {path} cannot be decoded: {err} ++", file=out)
        return 1

    newline = _newline_style(raw)

    try:
        collisions = find_collisions(src, str(path), liturgy=False)
    except SyntaxError as err:
        print(
            f"++ CANNOT TRANSCRIBE: {type(err).__name__} at line {err.lineno} ++",
            file=out,
        )
        return 1

    if collisions:
        print(
            f"++ CANNOT TRANSCRIBE: {len(collisions)} "
            f"COLLISION{'S' if len(collisions) != 1 else ''} ++",
            file=out,
        )
        for c in collisions:
            print(
                f"  {path}:{c.line}  {c.word:<12} -> reserved ({c.target})",
                file=out,
            )
        print("rename these, then chant again", file=out)
        return 1

    litany = to_liturgy(src)

    # Verify before writing. This is the round-trip property test applied to
    # one real file: if the output does not transform back to the input, the
    # output is wrong and must not reach disk claiming otherwise.
    try:
        back, _ = transform(litany, filename=str(path))
    except SyntaxError:
        back = None
    if back != src:
        print("++ CANNOT TRANSCRIBE: the output does not round-trip ++", file=out)
        print("   this is a fault in Liturgy, not in your source", file=out)
        return 1

    output = litany if newline == "\n" else litany.replace("\n", newline)

    if dest is None:
        print(output, end="", file=out)
    else:
        try:
            pathlib.Path(dest).write_bytes(output.encode("utf-8"))
        except OSError as err:
            print(
                f"++ CANNOT TRANSCRIBE: cannot write {dest}: {err.strerror} ++",
                file=out,
            )
            return 1
        print(f"++ {len(split_lines(litany))} lines transcribed ++", file=out)
    return 0
