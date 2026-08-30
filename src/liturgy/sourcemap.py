"""Column mapping between generated Python and original Liturgy source.

Line numbers need no mapping: the token pass preserves lines exactly, so
line N of the Python is line N of the Liturgy. Only columns move.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field


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

    def to_lit(self, line: int, col: int) -> int:
        """Map a column in generated Python back to the .lit column."""
        spans = self._spans.get(line)
        if not spans:
            return col
        i = bisect_right(self._starts[line], col) - 1
        if i < 0:
            return col
        if col < spans[i].py_end:
            return spans[i].lit_start
        return col + self._cum[line][i]
