"""Liturgy source -> Python source, preserving line numbers exactly."""

from __future__ import annotations

import io
import token as tokmod
import tokenize
from collections.abc import Sequence
from typing import NamedTuple, Protocol

from .lexicon import LEXICON
from .sourcemap import SourceMap, Span


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


def alias_pass(toks: list[tokenize.TokenInfo]) -> list[Substitution]:
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

        py = LEXICON.get(tok.string)

        # Track import statements in either spelling. Do this before the
        # substitution decision so the keyword itself is still translated.
        if tok.string in ("import", "from") or py in ("import", "from"):
            in_import = True

        if py is None:
            continue

        prev = significant[i - 1] if i else None
        nxt = significant[i + 1] if i + 1 < len(significant) else None

        # Import-statement keywords always translate, even directly after a
        # relative-import dot (`from . import x`) which would otherwise look
        # like attribute access to Rule 1 below.
        if in_import and py in _IMPORT_SAFE:
            subs.append(Substitution(tok.start[0], tok.start[1], tok.end[1], py))
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
        if in_import and py not in _IMPORT_SAFE:
            continue

        subs.append(Substitution(tok.start[0], tok.start[1], tok.end[1], py))

    return subs


DEFAULT_PASSES: tuple[TokenPass, ...] = (alias_pass,)


def transform(
    src: str, passes: Sequence[TokenPass] = DEFAULT_PASSES
) -> tuple[str, SourceMap]:
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    subs = [s for p in passes for s in p(toks)]
    return _splice(src, subs)


def _splice(src: str, subs: list[Substitution]) -> tuple[str, SourceMap]:
    lines = src.splitlines(keepends=True)
    smap = SourceMap()

    by_line: dict[int, list[Substitution]] = {}
    for s in subs:
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
