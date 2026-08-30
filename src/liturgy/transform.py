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


def alias_pass(toks: list[tokenize.TokenInfo]) -> list[Substitution]:
    subs: list[Substitution] = []
    for tok in toks:
        if tok.type != tokmod.NAME:
            continue
        py = LEXICON.get(tok.string)
        if py is None:
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
