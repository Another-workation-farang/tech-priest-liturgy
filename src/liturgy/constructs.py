"""Construct headers: recognising them, and rejecting their misuse.

The carrier pass rewrites a construct header in place, on one line, into
valid Python that parses. The AST pass in `rewrite` then restructures it.

A construct that needs no carrier reports itself out of band instead, in the
`ConstructFacts` the pass returns alongside its substitutions. `consecrated`
does: the annotation it used to hide in is the author's to spend on an
archetype. `unsanctioned` never had a choice -- it is a modifier with no
Python spelling at all, so the pass splices it away and its absence is the
only thing the generated source can say about it.
"""

from __future__ import annotations

import token as tokmod
import tokenize

from .lexicon import CONSTRUCT_KEYWORDS
from .transform import (
    _CLOSERS,
    _INSIGNIFICANT,
    _OPENERS,
    Consecration,
    ConstructFacts,
    Exemption,
    PassResult,
    Substitution,
)


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


# The names the carrier pass writes into the generated Python, and the
# prefix `rewrite._build_retry` mints its bookkeeping under. They appear in
# no lexicon table, but the AST pass recognises carriers by exactly these
# spellings -- a litany that wrote one itself would be indistinguishable
# from a carrier and silently rewritten (a `with __litany__(...) styled x:`
# lost its binding this way). They are the machine's own; using one is loud.
#
# One authority: the substitution texts below and `rewrite`'s carrier
# matching both use these constants, and MACHINE_NAMES is built from them,
# so a fourth construct cannot be added without its carrier name joining
# the reserved set.
#
# `__consecrated__` is the exception, and stays reserved on purpose: no pass
# writes it any more -- `consecrated` travels in `ConstructFacts` now -- but
# a name the machine has ever claimed does not become the author's again.
# Un-reserving it would turn `x: __consecrated__ = 5`, which is loud today,
# into an ordinary annotation.
CONSECRATED_CARRIER = "__consecrated__"
LITANY_CARRIER = "__litany__"
AUGUR_CARRIER = "__augur__"
MACHINE_NAMES: frozenset[str] = frozenset(
    {CONSECRATED_CARRIER, LITANY_CARRIER, AUGUR_CARRIER}
)
MACHINE_PREFIX = "__liturgy_"


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

    # The final ENDMARKER is recorded as a statement start too. Harmless and
    # unreachable in practice: `carrier_pass` acts only on a NAME token whose
    # text is a construct keyword, and ENDMARKER is neither.
    return starts


def opens_a_block(significant: list[tokenize.TokenInfo], i: int) -> bool:
    """Does the logical line starting at `significant[i]` end in a `:`?

    Statement position alone is not enough for a block construct. The spec
    requires the line to open a block, and without that check
    `match: litany(3)` -- annotating a variable named `match` -- would be
    read as a construct header. Both halves of the rule are needed.

    This deliberately answers yes for an annotation like `litany: int` --
    an annotation colon is a depth-zero colon like any other -- so the
    carriers themselves disambiguate: `_litany_carrier` and
    `_augur_carrier` each check what follows the keyword before treating
    the line as a header, and an annotation of a construct-named variable
    is left as the author's own (the M10 shape, since resolved there).
    """
    depth = 0
    for tok in significant[i:]:
        if tok.type == tokmod.NEWLINE:
            return False
        if tok.type != tokmod.OP:
            continue
        if tok.string in _OPENERS:
            depth += 1
        elif tok.string in _CLOSERS:
            depth -= 1
        elif tok.string == ":" and depth == 0:
            return True
    return False


def is_machine_name(name: str) -> bool:
    """Is `name` one the generated code claims for itself?

    The dunder gate goes first: this runs once per NAME token of every
    compile, and almost no token starts with two underscores.
    """
    return name.startswith("__") and (
        name in MACHINE_NAMES or name.startswith(MACHINE_PREFIX)
    )


# What `unsanctioned` may stand in front of. `remote` earns its place
# because `remote rite f():` is a rite -- the word between the modifier and
# `rite` is `async`, and an exemption that stopped at the sight of it would
# be a rule about spelling rather than about rites.
_UNSANCTIONABLE: frozenset[str] = frozenset({"rite", "remote", "consecrated"})


def carrier_pass(toks: list[tokenize.TokenInfo]) -> PassResult:
    """Rewrite construct headers, in place, into parseable Python.

    Returns the substitutions and the facts no substitution can carry --
    every `consecrated` header this pass recognised, and every
    `unsanctioned` marker it spliced away.
    """
    significant = [t for t in toks if t.type not in _INSIGNIFICANT]
    starts = statement_starts(significant)
    subs: list[Substitution] = []
    consecrated: list[Consecration] = []
    exempt: list[Exemption] = []
    exempt_file = False

    # Before anything is rewritten: a machine name spelled by the author.
    # Only attribute position is spared, on Rule 1's reasoning -- another
    # module's attributes are its own affair, and `_carrier_call` only ever
    # matches a bare Name anyway.
    for i, tok in enumerate(significant):
        if tok.type != tokmod.NAME or not is_machine_name(tok.string):
            continue
        prev = significant[i - 1] if i else None
        if prev is not None and prev.type == tokmod.OP and prev.string == ".":
            continue
        raise heresy(
            f"{tok.string} is the machine's own name",
            "<unknown>", tok.start[0], tok.start[1] + 1, tok.line,
        )

    # Every `unsanctioned` in the file, in source order, before anything is
    # rewritten: silence would be a modifier that looked applied and was not.
    _check_unsanctioned(significant, starts)

    for i in sorted(starts):
        tok = significant[i]
        if tok.type != tokmod.NAME or tok.string not in CONSTRUCT_KEYWORDS:
            continue

        marked = False
        if tok.string == "unsanctioned":
            sub, kind = _unsanctioned_modifier(significant, i)
            subs.append(sub)
            if kind is None:
                exempt_file = True
                continue
            # The modifier is not the statement. What follows it is, and it
            # is not itself a statement start, so the dispatch below has to
            # be pointed at it by hand.
            i += 1
            tok = significant[i]
            marked = True
            if kind == "rite":
                exempt.append(Exemption(tok.start[0], tok.start[1], "rite"))

        if tok.string == "consecrated":
            header, seal = _consecrated_carrier(significant, i)
            subs.extend(header)
            consecrated.append(seal)
            if marked:
                # The name's column, which is what survives the splice and
                # what an AST pass can ask a binding for. See `Exemption`.
                exempt.append(Exemption(seal.row, seal.col, "consecrated"))
        elif tok.string == "litany":
            subs.extend(_litany_carrier(significant, i))
        elif tok.string == "augur":
            subs.extend(_augur_carrier(significant, i))

    return PassResult(
        subs,
        ConstructFacts(
            consecrated=frozenset(consecrated),
            unsanctioned=frozenset(exempt),
            unsanctioned_file=exempt_file,
        ),
    )


def _check_unsanctioned(
    significant: list[tokenize.TokenInfo], starts: set[int]
) -> None:
    """Judge every `unsanctioned` in the file, left to right.

    One scan, in source order, so the first fault in the file is the one
    reported. The header loop in `carrier_pass` visits statement starts
    only, and a stray word further down would otherwise be judged before a
    malformed header above it -- `unsanctioned = 5` on line 1 blamed on
    line 2. `_unsanctioned_modifier` is pure, so calling it here to judge
    and again there to splice costs nothing but the walk.

    Outside statement position the word is a heresy, not a name. It is
    reserved and has no Python spelling, so leaving a stray one alone would
    generate `x = unsanctioned` and defer the complaint to a `NameError` at
    prayer -- or, worse, to nothing at all, when the author wrote
    `y = unsanctioned rite ...` believing something was exempted.

    Two positions are spared, on the same reasoning the alias pass spares
    them. After a dot the word is another object's attribute and no
    business of ours (Rule 1), and as a keyword-argument name inside a call
    it is the callee's parameter, not a word in this litany (Rule 2). The
    corpus sweep's skip test spares exactly these two as well, which is why
    `transform` may be handed a stdlib file containing either.

    Rule 2 asks for the *innermost* open bracket, not merely for a nonzero
    depth. PEP 701 f-string debug syntax (`f"{unsanctioned=}"`, and the
    spaced `f"{unsanctioned = }"`) tokenizes the same NAME-then-`=` shape
    one bracket deep, because on 3.12+ a replacement field's `{` is a real
    `OP` token that depth alone cannot tell from a call's `(`. Sparing it
    would defer exactly the `NameError` this scan exists to prevent. The
    bracket stack carries each open bracket's own character so the sparing
    can require a literal `(`, which an f-string's `{`, a dict or set
    literal's `{`, and a subscript's `[` never are. This is the shape
    `tests/test_roundtrip.py`'s sweep predicate settled on for the same
    question.
    """
    # One entry per currently-open bracket: its own character.
    brackets: list[str] = []
    for i, tok in enumerate(significant):
        if tok.type == tokmod.OP:
            if tok.string in _OPENERS:
                brackets.append(tok.string)
            elif tok.string in _CLOSERS:
                if brackets:
                    brackets.pop()
            continue
        if tok.type != tokmod.NAME or tok.string != "unsanctioned":
            continue
        prev = significant[i - 1] if i else None
        if prev is not None and prev.type == tokmod.OP and prev.string == ".":
            continue
        nxt = significant[i + 1] if i + 1 < len(significant) else None
        if (
            brackets
            and brackets[-1] == "("
            and nxt is not None
            and nxt.type == tokmod.OP
            and nxt.string == "="
        ):
            continue
        if i in starts:
            _unsanctioned_modifier(significant, i)  # raises, or is well-formed
            continue
        raise heresy(
            "unsanctioned cannot stand mid-statement",
            "<unknown>", tok.start[0], tok.start[1] + 1, tok.line,
        )


def _unsanctioned_modifier(
    significant: list[tokenize.TokenInfo], i: int
) -> tuple[Substitution, str | None]:
    """Splice `unsanctioned` away and say what it marked.

    Returns the substitution and the kind of exemption: `"rite"`,
    `"consecrated"`, or `None` for the bare form, which exempts the whole
    litany.

    The span runs from the word's own column **through the whitespace after
    it**, to the start of whatever it marks. Replacing only the word would
    leave that whitespace behind and shift a `pattern`'s method a dozen
    columns to the right of its siblings; splicing the gap too means the
    remainder of the line slides left and the leading indentation -- which
    lies before the span -- is never touched.

    The bare form spans the word alone, leaving an empty line. It must
    never remove one: line N of the generated Python is line N of the
    litany, and every traceback depends on it.
    """
    kw = significant[i]
    nxt = significant[i + 1] if i + 1 < len(significant) else None

    if nxt is None or nxt.type == tokmod.NEWLINE:
        if kw.start[1] != 0:
            # Indented, it is inside somebody's block, and splicing it out
            # would leave an empty line where Python demanded a statement.
            # The author meant to mark something and marked nothing.
            raise heresy(
                "unsanctioned alone on a line exempts the whole litany "
                "and must stand at the margin",
                "<unknown>", kw.start[0], kw.start[1] + 1, kw.line,
            )
        return Substitution(kw.start[0], kw.start[1], kw.end[1], ""), None

    if nxt.type != tokmod.NAME or nxt.string not in _UNSANCTIONABLE:
        raise heresy(
            "unsanctioned marks a rite or a consecrated name",
            "<unknown>", kw.start[0], kw.start[1] + 1, kw.line,
        )
    if nxt.string == "remote":
        after = significant[i + 2] if i + 2 < len(significant) else None
        if after is None or after.type != tokmod.NAME or after.string != "rite":
            raise heresy(
                "unsanctioned marks a rite or a consecrated name",
                "<unknown>", kw.start[0], kw.start[1] + 1, kw.line,
            )
    if nxt.start[0] != kw.start[0]:
        # The same trap `_consecrated_carrier` documents: the span would
        # take its row from one line and its end column from another, and
        # `_splice` would cut whatever happens to sit at that column here.
        raise heresy(
            "unsanctioned and what it marks must share a line",
            "<unknown>", kw.start[0], kw.start[1] + 1, kw.line,
        )
    kind = "consecrated" if nxt.string == "consecrated" else "rite"
    return (
        Substitution(kw.start[0], kw.start[1], nxt.start[1], ""),
        kind,
    )


def _consecrated_carrier(
    significant: list[tokenize.TokenInfo], i: int
) -> tuple[list[Substitution], Consecration]:
    """`consecrated NAME = v` -> `NAME = v`, plus the fact that it was one.

    The annotation slot is left alone, so `consecrated NAME: T = v`
    -> `NAME: T = v` and a sealed name may declare its archetype like any
    other. Nothing in the generated Python says the binding is consecrated;
    the returned `Consecration` is the only record, and `rewrite` matches it
    back to the statement by row, column and name.
    """
    kw = significant[i]
    name = significant[i + 1] if i + 1 < len(significant) else None
    if name is None or name.type != tokmod.NAME:
        raise heresy(
            "consecrated must be followed by a name",
            "<unknown>", kw.start[0], kw.start[1] + 1, kw.line,
        )
    if name.start[0] != kw.start[0]:
        # The keyword-swallowing substitution below takes its row from the
        # keyword and its end column from the name. Across a line
        # continuation those are two different rows, and the result is a
        # substitution that reaches off the end of its own line: `_splice`
        # would silently cut `consecrated \` down to `ecrated \` and the
        # author would get `SyntaxError: invalid syntax` on text they never
        # wrote. This is also the one way the carrier pass can break the
        # line invariant, and `_splice`'s newline guard cannot see it --
        # it inspects the replacement text, not the span.
        raise heresy(
            "consecrated and its name must share a line",
            "<unknown>", kw.start[0], kw.start[1] + 1, kw.line,
        )
    return (
        # Swallow the keyword and the space after it, keeping indentation.
        [Substitution(kw.start[0], kw.start[1], name.start[1], "")],
        # `name.start[1]` is a character column in the *Liturgy* line, which
        # is the coordinate system `SourceMap.to_lit` hands back and the one
        # `rewrite` compares against.
        Consecration(name.start[0], name.start[1], name.string),
    )


def _litany_carrier(
    significant: list[tokenize.TokenInfo], i: int
) -> list[Substitution]:
    """`litany(args):` -> `with __litany__(args):`."""
    kw = significant[i]
    nxt = significant[i + 1] if i + 1 < len(significant) else None
    if nxt is not None and nxt.type == tokmod.OP and nxt.string == ":":
        after = significant[i + 2] if i + 2 < len(significant) else None
        if after is not None and after.type != tokmod.NEWLINE:
            # `litany: int = 5` -- an annotation of a variable named
            # litany, which is the author's own name until the construct
            # is wanted on the line. The construct's argument list cannot
            # begin with `:`.
            return []
        # A bare `litany:` is the construct missing its count, not an
        # annotation of nothing; keep the targeted heresy rather than
        # leaving Python to report bare "invalid syntax".
    if not opens_a_block(significant, i):
        return []  # not a construct header: somebody's call, left alone
    if nxt is None or nxt.type != tokmod.OP or nxt.string != "(":
        raise heresy(
            "litany takes a parenthesised attempt count",
            "<unknown>", kw.start[0], kw.start[1] + 1, kw.line,
        )
    return [
        Substitution(
            kw.start[0], kw.start[1], kw.end[1], f"with {LITANY_CARRIER}"
        )
    ]


def _augur_carrier(
    significant: list[tokenize.TokenInfo], i: int
) -> list[Substitution]:
    """`augur:` -> `with __augur__():`.

    The construct is exactly `augur:` with nothing after the colon: its
    conditions stand one per line beneath. `augur: int` -- a colon with
    anything after it -- is an annotation of a variable named augur, and
    is left alone here. Where that leniency would hide a botched one-line
    augury -- a bare annotation, no value, anywhere a block augury would
    be judged -- `rewrite._reject_misplaced_auguries` rejects it loudly;
    an annotation *with* a value is unmistakably the author's own.
    """
    kw = significant[i]
    nxt = significant[i + 1] if i + 1 < len(significant) else None
    if nxt is not None and nxt.type == tokmod.OP and nxt.string == ":":
        after = significant[i + 2] if i + 2 < len(significant) else None
        if after is not None and after.type != tokmod.NEWLINE:
            return []  # an annotation: the colon does not end the line
        return [
            Substitution(
                kw.start[0], kw.start[1], kw.end[1], f"with {AUGUR_CARRIER}()"
            )
        ]
    if not opens_a_block(significant, i):
        return []  # not a construct header: somebody's call, left alone
    raise heresy(
        "augur opens a block and takes no arguments",
        "<unknown>", kw.start[0], kw.start[1] + 1, kw.line,
    )
