"""Python to Liturgy, the reverse of the alias pass.

The engine behind `transcribe`. It shares `transform`'s traversal, so the
three context rules -- attribute position, keyword-argument position, import
statements -- apply identically in both directions.

One thing here is not word-for-word. `introit` is a macro, so reversing it
is a *phrase* match over a token sequence rather than a table lookup, and
`_introit_subs` below is the only rule in this module that reads more than
one token. It sits after `constructs` in the dependency order for the two
things it borrows from there: the statement-position test, and the exact
text the forward carrier splices in.
"""

from __future__ import annotations

import token as tokmod
import tokenize

from liturgy import transform as _t
from liturgy.constructs import INTROIT_GUARD, statement_starts
from liturgy.lexicon import INVERSE

# The Liturgy spellings of import/from/as: the destination-language
# equivalent of transform._IMPORT_SAFE for this direction.
_IMPORT_SAFE = frozenset({INVERSE["import"], INVERSE["from"], INVERSE["as"]})

INTROIT = "introit"


def _is_import_start(tok: tokenize.TokenInfo, target: str | None) -> bool:
    del target  # unused: Python source is unambiguous, unlike Liturgy source
    return tok.string in ("import", "from")


def _introit_subs(toks: list[tokenize.TokenInfo]) -> list[_t.Substitution]:
    """Every `if __name__ == "__main__":` this pass will spell `introit:`.

    **What reverses.** Exactly one shape: a statement-position `if` whose
    line reads, character for character, `if __name__ == "__main__"` --
    the text `constructs.INTROIT_GUARD` holds -- followed by a `:` that
    ends the logical line. A trailing comment after that colon is fine;
    comments are not significant tokens, and the colon and everything after
    it is left untouched anyway.

    **What is deliberately left as Python**, because the forward direction
    could not put it back exactly as it was found, and a reversal that does
    not round-trip is worse than no reversal:

    - `if __name__ == '__main__':` -- single quotes. The carrier writes
      double ones, so reversing this would rewrite the author's quoting.
    - `if __name__=="__main__":`, or any other spacing. Same reason.
    - `if __name__ == "__main__" and ready:` -- the colon does not follow
      the string, so the guard is only part of the condition.
    - `if __name__ == "__main__": main()` -- a one-line body. `introit:`
      with anything after the colon is an annotation of a variable named
      introit, so the forward direction would not expand it back.
    - `elif __name__ == "__main__":` -- `introit` is not a continuation
      keyword and cannot be spelled as one.
    - A guard split across a line continuation. `Substitution` is a span on
      one row; a span whose columns come from two rows is the exact fault
      `_splice` refuses.

    None of these is a loss: leaving a guard as Python leaves it *correct*
    Liturgy, since Liturgy is a superset of Python.
    """
    significant = [t for t in toks if t.type not in _t._INSIGNIFICANT]
    subs: list[_t.Substitution] = []

    for i in sorted(statement_starts(significant)):
        window = significant[i : i + 6]
        if len(window) < 6:
            continue
        kw, name, eq, string, colon, after = window
        if kw.type != tokmod.NAME or kw.string != "if":
            continue
        if name.type != tokmod.NAME or name.string != "__name__":
            continue
        if eq.type != tokmod.OP or eq.string != "==":
            continue
        if string.type != tokmod.STRING:
            continue
        if colon.type != tokmod.OP or colon.string != ":":
            continue
        if after.type != tokmod.NEWLINE:
            continue
        # One row, or the span below would take its start column from one
        # line and its end column from another -- see `_splice`.
        if kw.start[0] != string.end[0]:
            continue
        # `kw.line` is the physical line the `if` stands on -- the same
        # text `_splice` will cut, and the only way to see the whitespace
        # and the quote characters the tokens themselves discard.
        if kw.line[kw.start[1] : string.end[1]] != INTROIT_GUARD:
            continue
        subs.append(
            _t.Substitution(kw.start[0], kw.start[1], string.end[1], INTROIT)
        )
    return subs


def _reverse_pass(toks: list[tokenize.TokenInfo]) -> list[_t.Substitution]:
    """The alias pass inverted, with the guard collapsed to `introit`.

    The two rules overlap on one token: `if` is `should`, and the guard's
    `if` is the first character of a span this pass replaces whole. Two
    substitutions covering the same columns would splice into nonsense, so
    the word-for-word ones inside a guard's span are dropped -- the phrase
    wins over its parts.
    """
    aliases = _t._walk_tokens(toks, INVERSE, _is_import_start, _IMPORT_SAFE)
    guards = _introit_subs(toks)
    if not guards:
        return aliases
    spans = {(g.row, g.col_start, g.col_end) for g in guards}
    kept = [
        a
        for a in aliases
        if not any(
            a.row == row and a.col_start < end and start < a.col_end
            for row, start, end in spans
        )
    ]
    return kept + guards


def to_liturgy(src: str) -> str:
    return _t.transform(src, passes=(_reverse_pass,)).python
