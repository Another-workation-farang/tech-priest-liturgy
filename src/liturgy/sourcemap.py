"""Column mapping between generated Python and original Liturgy source.

Line numbers need no mapping: the token pass preserves lines exactly, so
line N of the Python is line N of the Liturgy. Only columns move.

Every column here is a *character* offset. `char_offset` is the door
everything from `ast` and `traceback` has to come through first, since
those two count bytes.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field


def char_offset(line: str, byte_offset: int) -> int:
    """Convert a UTF-8 byte offset to a character offset within `line`.

    `ast.col_offset`/`end_col_offset` and `traceback`'s `colno`/`end_colno`
    all count UTF-8 bytes; everything else here -- `tokenize`, string
    slicing, `SourceMap` -- counts characters. A multi-byte character
    earlier on the line would otherwise skew every later column, so a byte
    offset must be converted against the very line it indexes into (the
    *generated Python* line, not the Liturgy one) before `to_lit` sees it.

    An empty `line` means "no text to measure against"; the offset is
    returned unchanged rather than collapsed to zero.
    """
    if not line:
        return byte_offset
    return len(line.encode("utf-8")[:byte_offset].decode("utf-8", "ignore"))


@dataclass(frozen=True, slots=True)
class Span:
    """One substitution, in 0-based column coordinates."""

    py_start: int
    py_end: int
    lit_start: int
    lit_end: int


@dataclass
class SourceMap:
    _spans: dict[int, list[Span]] = field(default_factory=dict)
    _starts: dict[int, list[int]] = field(default_factory=dict)
    _cum: dict[int, list[int]] = field(default_factory=dict)

    def add(self, line: int, span: Span) -> None:
        self._spans.setdefault(line, []).append(span)

    def freeze(self) -> None:
        """Sort spans and precompute cumulative width deltas."""
        for line, spans in self._spans.items():
            spans.sort(key=lambda s: s.py_start)
            self._starts[line] = [s.py_start for s in spans]
            total = 0
            cum: list[int] = []
            for s in spans:
                total += (s.lit_end - s.lit_start) - (s.py_end - s.py_start)
                cum.append(total)
            self._cum[line] = cum

    def _locate(self, line: int, col: int) -> tuple[list[Span], int] | None:
        """This line's spans and the index of the last one starting <= col.

        The shared prologue of every lookup below; one home for the bisect
        convention, so a change to how `freeze` indexes spans lands once.
        Returns None when the line has no spans; the index may be -1 when
        `col` precedes them all.
        """
        spans = self._spans.get(line)
        if not spans:
            return None
        return spans, bisect_right(self._starts[line], col) - 1

    def to_lit(self, line: int, col: int) -> int:
        """Map a column in generated Python back to the .lit column."""
        found = self._locate(line, col)
        if found is None:
            return col
        spans, i = found
        if i < 0:
            return col
        if col < spans[i].py_end:
            return spans[i].lit_start
        return col + self._cum[line][i]

    def to_py(self, line: int, col: int) -> int:
        """Map a column in the .lit source forward to generated Python.

        The inverse of `to_lit`, and needed by anything holding a Liturgy
        column that must reach a reader who will map it back -- a
        `TechHeresy`'s offset is read by `curse._render_syntax_location`,
        which runs every offset through `to_lit`. A diagnostic raised from
        Liturgy coordinates has to come the other way through here first or
        the caret is mapped twice and lands nowhere near the fault.

        Spans are stored in `py_start` order, which is also `lit_start`
        order: a substitution never moves text past its neighbours.
        """
        spans = self._spans.get(line)
        if not spans:
            return col
        delta = 0
        for s in spans:
            if col < s.lit_start:
                break
            if col < s.lit_end:
                return s.py_start
            delta += (s.py_end - s.py_start) - (s.lit_end - s.lit_start)
        return col + delta

    def span_at(self, line: int, col: int) -> Span | None:
        """The substitution span covering generated-Python column `col`.

        Lets an error renderer answer "did a substitution put this word
        here" -- a syntax error pointing into one is best explained by
        naming the source word, not only by moving the caret.
        """
        found = self._locate(line, col)
        if found is None:
            return None
        spans, i = found
        if i >= 0 and col < spans[i].py_end:
            return spans[i]
        return None

    def span_before(self, line: int, col: int) -> Span | None:
        """The nearest substitution span ending at or before `col`."""
        found = self._locate(line, col)
        if found is None:
            return None
        spans, i = found
        if i >= 0 and spans[i].py_end <= col:
            return spans[i]
        return None
