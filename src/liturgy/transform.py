"""Liturgy source -> Python source, preserving line numbers exactly."""

from __future__ import annotations

import io
import re
import token as tokmod
import tokenize
from collections.abc import Callable, Sequence
from typing import NamedTuple, Protocol

from .lexicon import LEXICON
from .sourcemap import SourceMap, Span

# str.splitlines() also breaks on \x0b \x0c \x1c \x1d \x1e \x85    .
# CPython's tokenizer breaks only on \n, so anything that splits source into
# "lines" alongside token rows must do the same or the two silently
# desynchronise -- and a form feed (a conventional page separator) or any of
# the others *inside a string literal* is perfectly legal Python.
_LINE = re.compile(r"[^\n]*\n|[^\n]+")


def split_lines(src: str) -> list[str]:
    """Split into newline-terminated lines exactly as the tokenizer does.

    `"".join(split_lines(s)) == s` for every `s`, and element N-1 is the
    text the tokenizer reports as row N.
    """
    return _LINE.findall(src)


class Substitution(NamedTuple):
    row: int  # 1-based
    col_start: int  # 0-based, inclusive
    col_end: int  # 0-based, exclusive
    text: str


class TokenPass(Protocol):
    def __call__(
        self, toks: list[tokenize.TokenInfo]
    ) -> list[Substitution]: ...


# Tokens that carry no syntactic weight when looking backwards.
_INSIGNIFICANT = frozenset(
    {
        tokmod.COMMENT,
        tokmod.NL,
        tokmod.INDENT,
        tokmod.DEDENT,
    }
)

# Inside an import statement, only these targets may still be substituted.
_IMPORT_SAFE = frozenset({"import", "from", "as"})

_OPENERS = frozenset("([{")
_CLOSERS = frozenset(")]}")


# Given the current token and its translation (None if untranslated), does
# this token start an import statement? Direction-sensitive: Liturgy source
# may spell the keyword either way (it is a superset of Python), so the
# forward direction must check both spellings. Python source is unambiguous,
# so the reverse pass (see `_reverse.py`) only needs to check the raw token.
IsImportStart = Callable[[tokenize.TokenInfo, str | None], bool]


def _lexicon_is_import_start(tok: tokenize.TokenInfo, target: str | None) -> bool:
    return tok.string in ("import", "from") or target in ("import", "from")


def _walk_tokens(
    toks: list[tokenize.TokenInfo],
    lookup: dict[str, str],
    is_import_start: IsImportStart,
    import_safe: frozenset[str],
) -> list[Substitution]:
    """Shared traversal for both translation directions.

    `lookup` maps a source-language word to its destination-language word
    (`LEXICON` for Liturgy -> Python, `INVERSE` for the reverse pass).
    `import_safe` holds the *destination*-language spellings of the
    import/from/as keywords, since that is the set actually compared against
    `target` below — it differs per direction because the two languages
    spell those keywords differently.
    """
    subs: list[Substitution] = []
    significant = [t for t in toks if t.type not in _INSIGNIFICANT]

    depth = 0
    in_import = False

    for i, tok in enumerate(significant):
        if tok.type == tokmod.NEWLINE:
            in_import = False
            continue

        if tok.type == tokmod.OP:
            if tok.string in _OPENERS:
                depth += 1
            elif tok.string in _CLOSERS:
                depth -= 1
            elif tok.string == ";":
                # A new statement starts after the semicolon; a preceding
                # import's scope does not carry over to it.
                in_import = False
            continue

        if tok.type != tokmod.NAME:
            continue

        target = lookup.get(tok.string)
        prev = significant[i - 1] if i else None
        nxt = significant[i + 1] if i + 1 < len(significant) else None

        # Track import statements. Do this before the substitution decision
        # so the keyword itself is still translated.
        #
        # Only a NAME in *statement position* can begin one. Without that
        # gate, `button.invoke()` (standard Tkinter, and the shape of
        # ctx.invoke / CliRunner.invoke / chain.invoke) sets in_import and
        # the bypass below then rewrites the attribute to `button.import()`
        # before Rule 1 can protect it -- the exact failure the named
        # `template.render()` regression exists to prevent. The knock-on is
        # worse: a spuriously-set in_import makes Rule 3 suppress every
        # Liturgy word for the rest of the line, so some shapes fail
        # silently rather than loudly.
        at_stmt_start = (
            prev is None
            or prev.type == tokmod.NEWLINE
            or (prev.type == tokmod.OP and prev.string in (";", ":"))
        )
        if at_stmt_start and is_import_start(tok, target):
            in_import = True

        if target is None:
            continue

        # Import-statement keywords always translate, even directly after a
        # relative-import dot (`from . import x`) which would otherwise look
        # like attribute access to Rule 1 below.
        if in_import and target in import_safe:
            subs.append(
                Substitution(tok.start[0], tok.start[1], tok.end[1], target)
            )
            continue

        # Rule 1: attribute access. obj.render must not become obj.return.
        if prev is not None and prev.type == tokmod.OP and prev.string == ".":
            continue

        # Rule 2: keyword-argument name inside a call. Guard against PEP 701
        # f-string debug (`{measure=}`) and format-spec (`{measure=:>10}`)
        # syntax, which also tokenizes a bare `=` but is not a kwarg.
        if (
            depth > 0
            and nxt is not None
            and nxt.type == tokmod.OP
            and nxt.string == "="
        ):
            after_eq = significant[i + 2] if i + 2 < len(significant) else None
            is_fstring_debug = (
                after_eq is not None
                and after_eq.type == tokmod.OP
                and after_eq.string in ("}", ":", "!")
            )
            if not is_fstring_debug:
                continue

        # Rule 3: import statements — only the statement keywords translate.
        if in_import and target not in import_safe:
            continue

        subs.append(Substitution(tok.start[0], tok.start[1], tok.end[1], target))

    return subs


def alias_pass(toks: list[tokenize.TokenInfo]) -> list[Substitution]:
    return _walk_tokens(toks, LEXICON, _lexicon_is_import_start, _IMPORT_SAFE)


DEFAULT_PASSES: tuple[TokenPass, ...] = (alias_pass,)


class UnfinishedLitany(SyntaxError):
    """The litany ends inside an unclosed bracket or string literal.

    A `SyntaxError` subclass on purpose. For a file that is simply what it
    is -- a syntax error -- so the loader and `chant` need no special case
    and the curse renders it like any other. `commune` catches this exact
    type, because at a prompt an unclosed bracket is not an error but a
    request for the next line.

    `sourcemap` carries the column map for the part that did tokenise, so a
    curse can still place its caret; rebuilding it by calling `transform`
    again would only fail the same way.
    """

    sourcemap: SourceMap | None = None


def transform(
    src: str,
    passes: Sequence[TokenPass] = DEFAULT_PASSES,
    *,
    filename: str = "<litany>",
) -> tuple[str, SourceMap]:
    """Translate Liturgy source into Python, preserving lines exactly.

    Returns the generated Python and the column map from it back to `src`.

    Raises:
        UnfinishedLitany: the source ends mid-bracket or mid-string.
        SyntaxError: (including `IndentationError`/`TabError`) a complete,
            unrecoverable tokenisation error, e.g. a dedent matching no
            outer indentation level. `filename` replaces the "<string>"
            the tokenizer invents.
        ValueError: a pass returned a substitution containing a newline,
            which would break the line invariant (see `_splice`).

    Every location raised is in **generated-Python** column coordinates --
    the same coordinates `compile()` reports for the same file -- so one
    mapping through the SourceMap serves both sources of error.
    """
    toks, unfinished = _tokenize(src, filename)
    subs = [s for p in passes for s in p(toks)]
    py, smap = _splice(src, subs)
    if unfinished is not None:
        raise _unfinished_litany(unfinished, py, smap, filename)
    return py, smap


def _tokenize(
    src: str, filename: str
) -> tuple[list[tokenize.TokenInfo], tokenize.TokenError | None]:
    """Tokenise, returning the tokens gathered before any unfinished input.

    A `TokenError` means only "the source ran out" -- an unclosed bracket or
    string. Everything up to that point tokenised fine and is worth keeping.
    A `SyntaxError` from the tokenizer is a real, complete error and is
    re-raised, with the filename the tokenizer cannot know filled in.
    """
    toks: list[tokenize.TokenInfo] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            toks.append(tok)
    except tokenize.TokenError as err:
        return toks, err
    except SyntaxError as err:
        # The tokenizer works from a readline callable and has no idea what
        # file this is; it labels everything "<string>".
        err.filename = filename
        raise
    return toks, None


def _unfinished_litany(
    err: tokenize.TokenError, py: str, smap: SourceMap, filename: str
) -> UnfinishedLitany:
    """Turn a `TokenError` into a located `SyntaxError`.

    `TokenError` is not a `SyntaxError`, carries no filename, and reports the
    position of EOF -- so it escaped `chant` raw as
    `TokenError: ('unexpected EOF in multi-line statement', (4, 0))` where
    Python would have said `'(' was never closed` with a file and a caret.

    Compiling the partially spliced Python recovers exactly that message and
    the opener's position. It is safe: `compile` only parses, and the source
    is one we just generated. If it somehow parses, or fails some other way,
    the tokenizer's own message and position still stand.
    """
    msg = str(err.args[0]) if err.args else "unexpected end of litany"
    pos = err.args[1] if len(err.args) > 1 else None
    lineno, offset = (pos[0], pos[1] + 1) if pos else (1, 1)
    text: str | None = None
    end_lineno: int | None = None
    end_offset: int | None = None

    try:
        compile(py, filename, "exec", dont_inherit=True)
    except SyntaxError as better:
        msg = better.msg or msg
        lineno = better.lineno or lineno
        offset = better.offset or offset
        text = better.text
        end_lineno, end_offset = better.end_lineno, better.end_offset
    except ValueError:
        pass  # e.g. a null byte in the source; keep the tokenizer's account

    if text is None:
        lines = split_lines(py)
        if 1 <= lineno <= len(lines):
            text = lines[lineno - 1]

    exc = UnfinishedLitany(
        msg, (filename, lineno, offset, text, end_lineno, end_offset)
    )
    exc.sourcemap = smap
    return exc


def _splice(src: str, subs: list[Substitution]) -> tuple[str, SourceMap]:
    lines = split_lines(src)
    smap = SourceMap()

    by_line: dict[int, list[Substitution]] = {}
    for s in subs:
        # The line invariant is the foundation everything downstream rests
        # on. No shipped pass can emit a newline today, but Spec II's
        # CarrierPass is precisely the pass that will, and the resulting
        # desynchronisation would be silent. Refuse loudly instead.
        if "\n" in s.text:
            raise ValueError(
                f"substitution would add a line: {s.text!r} at row {s.row}"
            )
        # The other way to break it, which the check above cannot see: a span
        # whose columns come from two different rows. Nothing in the text
        # gives it away -- the replacement may be the empty string -- but the
        # splice below indexes one line with both, so the excess silently
        # eats whatever sits at those columns on the wrong line. A carrier
        # built across a line continuation did exactly this.
        if s.col_end < s.col_start or s.col_end > len(
            lines[s.row - 1].rstrip("\n")
        ):
            raise ValueError(
                f"substitution span [{s.col_start}, {s.col_end}) "
                f"does not lie within row {s.row}"
            )
        by_line.setdefault(s.row, []).append(s)

    for row, row_subs in by_line.items():
        row_subs.sort(key=lambda s: s.col_start)

        # Forward pass: where does each replacement land in the output?
        delta = 0
        for s in row_subs:
            py_start = s.col_start + delta
            py_end = py_start + len(s.text)
            smap.add(row, Span(py_start, py_end, s.col_start, s.col_end))
            delta += len(s.text) - (s.col_end - s.col_start)

        # Backward pass: edit the line without invalidating earlier offsets.
        line = lines[row - 1]
        for s in reversed(row_subs):
            line = line[: s.col_start] + s.text + line[s.col_end :]
        lines[row - 1] = line

    smap.freeze()
    return "".join(lines), smap
