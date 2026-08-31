"""Construct headers: recognising them, and rejecting their misuse.

The carrier pass rewrites a construct header in place, on one line, into
valid Python that parses. The AST pass in `rewrite` then restructures it.
"""

from __future__ import annotations

import token as tokmod
import tokenize

from .lexicon import CONSTRUCT_KEYWORDS
from .transform import _CLOSERS, _INSIGNIFICANT, _OPENERS, Substitution


# Statements whose depth-zero `:` opens a block. Both spellings appear,
# because the carrier pass runs on the same token stream as the alias pass --
# before substitution -- and a .lit file may legally use either.
_BLOCK_OPENERS = frozenset(
    {
        # Python
        "if", "elif", "else", "for", "while", "with", "def", "class",
        "try", "except", "finally", "match", "case", "async",
        # Liturgy
        "should", "lest", "otherwise", "foreach", "whilst", "anointed",
        "rite", "pattern", "attempt", "curse", "regardless", "discern",
        "wherein", "remote",
        # Spec II block constructs
        "litany", "augur",
    }
)


class TechHeresy(SyntaxError):
    """A construct used in a way the compiler rejects.

    A SyntaxError subclass so that `curse SyntaxError` catches it and the
    curse renderer already knows how to show its file, line and caret.
    """


def heresy(
    message: str,
    filename: str,
    lineno: int,
    offset: int,
    text: str,
) -> TechHeresy:
    """Build a TechHeresy carrying everything the curse renderer needs."""
    exc = TechHeresy(message)
    exc.filename = filename
    exc.lineno = lineno
    exc.offset = offset
    exc.text = text
    return exc


def statement_starts(significant: list[tokenize.TokenInfo]) -> set[int]:
    """Indices in `significant` that begin a logical statement.

    A construct keyword is only a construct here. Everywhere else it is
    somebody's identifier, and substituting it would repeat the Spec I
    failure where a rule fired on a name without checking its position.

    A statement begins at the start of input, after a logical NEWLINE, or
    after a `;` or a block-opening `:` at bracket depth zero.

    Two things make the colon case correct. The depth test keeps `{1: x}`
    and `items[1:x]` out. Consulting the statement's *head* keeps
    `alpha: int = 1` out -- an annotation colon opens no block, and only a
    statement that began with a compound keyword has a colon that does.
    """
    starts: set[int] = set()
    depth = 0
    fresh = True
    head = ""  # first token of the statement in progress

    for i, tok in enumerate(significant):
        if tok.type == tokmod.NEWLINE:
            fresh = True
            head = ""
            continue

        if tok.type == tokmod.OP:
            if tok.string in _OPENERS:
                depth += 1
            elif tok.string in _CLOSERS:
                depth -= 1
            elif depth == 0 and tok.string == ";":
                fresh = True
                head = ""
                continue
            elif depth == 0 and tok.string == ":" and head in _BLOCK_OPENERS:
                # A block-opening colon starts a new statement after it.
                # An annotation colon (`x: int = 1`) does not, which is why
                # the head of the statement has to be consulted.
                fresh = True
                head = ""
                continue
            fresh = False
            continue

        if fresh:
            starts.add(i)
            head = tok.string
        fresh = False

    return starts


def carrier_pass(toks: list[tokenize.TokenInfo]) -> list[Substitution]:
    """Rewrite construct headers, in place, into parseable Python."""
    significant = [t for t in toks if t.type not in _INSIGNIFICANT]
    starts = statement_starts(significant)
    subs: list[Substitution] = []

    for i in sorted(starts):
        tok = significant[i]
        if tok.type != tokmod.NAME or tok.string not in CONSTRUCT_KEYWORDS:
            continue
        if tok.string == "consecrated":
            subs.extend(_consecrated_carrier(significant, i))

    return subs


def _consecrated_carrier(
    significant: list[tokenize.TokenInfo], i: int
) -> list[Substitution]:
    """`consecrated NAME = v` -> `NAME: __consecrated__ = v`."""
    kw = significant[i]
    name = significant[i + 1] if i + 1 < len(significant) else None
    if name is None or name.type != tokmod.NAME:
        raise heresy(
            "consecrated must be followed by a name",
            "<unknown>", kw.start[0], kw.start[1] + 1, kw.line,
        )
    return [
        # Swallow the keyword and the space after it, keeping indentation.
        Substitution(kw.start[0], kw.start[1], name.start[1], ""),
        Substitution(
            name.start[0], name.start[1], name.end[1],
            f"{name.string}: __consecrated__",
        ),
    ]
