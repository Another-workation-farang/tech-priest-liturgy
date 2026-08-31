"""The Spec III verbs: augur, transcribe, purge."""

from __future__ import annotations

import importlib.util
import io
import pathlib
import shutil
import sys
import tokenize

from .collisions import find_collisions
from .compiler import compile_litany
from .heresy import state_path
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
        # decode_source, not read_text(encoding="utf-8"): a BOM or a PEP 263
        # `coding:` cookie must be honoured exactly as `chant`, `transcribe`
        # and the import path honour it, or augur invents faults of its own
        # reading -- a stripped BOM reported as an invalid character, a
        # latin-1 cookie as a crash -- and stops agreeing with chant.
        # UnicodeDecodeError is a ValueError, not an OSError: caught here
        # rather than left to escape an `-> int` contract and end the walk.
        try:
            src = importlib.util.decode_source(path.read_bytes())
        except OSError as err:
            troubled = True
            _emit_bare(path, f"cannot be read: {err.strerror}", plain=plain, out=out)
            continue
        except (SyntaxError, UnicodeDecodeError, LookupError) as err:
            troubled = True
            _emit_bare(path, f"cannot be decoded: {err}", plain=plain, out=out)
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


def _source_encoding(raw: bytes) -> str:
    """The encoding named by `raw`'s BOM or PEP 263 `coding:` cookie.

    `decode_source` already runs `tokenize.detect_encoding` internally to
    decide how to decode `raw`; calling it again here is cheap (it only
    reads the first two lines) and returns the same name, so the
    destination can be written back in the encoding the source actually
    declared -- 'utf-8-sig' for a BOM, the cookie's name otherwise --
    instead of always UTF-8. Same rule as `_newline_style`: transcribe
    preserves the file's physical properties and changes only the words.
    """
    encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
    return encoding


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
        encoding = _source_encoding(raw)
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
        return 0

    # Encode in the source's own declared encoding, not always UTF-8: a
    # destination that carries the source's `coding:` cookie forward
    # verbatim (we never touch it -- it lives in a comment) but is written
    # in a different encoding is corrupt for every reader that honours that
    # cookie, this project's own loader included. This is not a case the
    # substitutions can trigger -- every reserved word is ASCII -- but
    # refuse rather than raise if it ever did.
    try:
        payload = output.encode(encoding)
    except (LookupError, UnicodeEncodeError) as err:
        print(
            f"++ CANNOT TRANSCRIBE: cannot encode the output as {encoding}: "
            f"{err} ++",
            file=out,
        )
        return 1

    # A second, byte-level round-trip: decode the exact bytes about to be
    # written the way a consumer honouring the destination's own cookie
    # would -- our loader, or CPython itself -- and confirm they still say
    # what we mean to write, i.e. `litany` (compared, not `output`, since
    # `decode_source` normalises newlines the same way it did for `src`).
    # The text-level check above compares `back` against `src`, neither of
    # which ever touches an encoding, so it cannot see bytes that are wrong
    # for the encoding their own cookie declares; this can.
    try:
        byte_roundtrip = importlib.util.decode_source(payload)
    except (SyntaxError, UnicodeDecodeError, LookupError):
        byte_roundtrip = None
    if byte_roundtrip != litany:
        print("++ CANNOT TRANSCRIBE: the output does not round-trip ++", file=out)
        print("   this is a fault in Liturgy, not in your source", file=out)
        return 1

    try:
        pathlib.Path(dest).write_bytes(payload)
    except OSError as err:
        print(
            f"++ CANNOT TRANSCRIBE: cannot write {dest}: {err.strerror} ++",
            file=out,
        )
        return 1
    print(f"++ {len(split_lines(litany))} lines transcribed ++", file=out)
    return 0


def purge(*, heresies: bool = False, root: str | None = None, out=None) -> int:
    """Clear generated caches. 0 done, 1 refused.

    The only destructive verb, so it is guarded: it refuses unless the tree
    holds at least one .lit file, because a recursive delete in the wrong
    directory is a bad afternoon. Symlinked directories are never entered --
    `rglob` does not follow them, and each candidate is checked anyway.

    A candidate that cannot be removed (permissions, or the directory
    vanishing between `rglob` and the delete) is reported and skipped
    rather than left to raise -- one unreadable directory must not strand
    the rest, and this is an `-> int` contract, not a traceback. Each
    `purged` line is printed only once the delete underneath it has
    actually succeeded, so the report never claims a deletion that didn't
    happen.
    """
    out = out if out is not None else sys.stdout
    base = pathlib.Path(root) if root is not None else pathlib.Path.cwd()

    if not any(base.rglob("*.lit")):
        print(f"++ {base} does not look like a Liturgy forge ++", file=out)
        print("   no .lit file found; refusing to delete anything", file=out)
        return 1

    removed = 0
    failed = False
    for cache in sorted(base.rglob("__pycache__")):
        if cache.is_symlink() or not cache.is_dir():
            continue
        try:
            shutil.rmtree(cache)
        except OSError as err:
            failed = True
            print(f"++ CANNOT PURGE: {cache} {err.strerror} ++", file=out)
            continue
        print(f"   purged {cache}", file=out)
        removed += 1

    if heresies:
        state = state_path()
        if state.exists():
            try:
                state.unlink()
            except OSError as err:
                failed = True
                print(f"++ CANNOT PURGE: {state} {err.strerror} ++", file=out)
            else:
                print(f"   purged {state}", file=out)
                removed += 1

    print(f"++ {removed} relic{'' if removed == 1 else 's'} purged ++", file=out)
    return 1 if failed else 0
