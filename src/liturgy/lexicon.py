"""Alias tables. Pure data plus lookup; depends on nothing."""

from __future__ import annotations

# Python keywords. Reserved words, so substitution is unambiguous.
KEYWORDS: dict[str, str] = {
    "Heretical": "False",
    "Void": "None",
    "Sanctioned": "True",
    "likewise": "and",
    "styled": "as",
    "attest": "assert",
    "remote": "async",
    "attend": "await",
    "cease": "break",
    "pattern": "class",
    "persist": "continue",
    "rite": "def",
    "purge": "del",
    "lest": "elif",
    "otherwise": "else",
    "curse": "except",
    "regardless": "finally",
    "foreach": "for",
    "within": "from",
    "universal": "global",
    "should": "if",
    "invoke": "import",
    "among": "in",
    "be": "is",
    "servitor": "lambda",
    "adjacent": "nonlocal",
    "nay": "not",
    "elsewise": "or",
    "abide": "pass",
    "proclaim": "raise",
    "render": "return",
    "attempt": "try",
    "whilst": "while",
    "anointed": "with",
    "emanate": "yield",
    # soft keywords
    "discern": "match",
    "wherein": "case",
    "archetype": "type",
}

# Builtins. Deliberately small: each entry widens the reserved-word surface.
SOFTWORDS: dict[str, str] = {
    "intone": "print",
    "measure": "len",
    "span": "range",
    "unseal": "open",
    "hearken": "input",
}

# Exception types. Also inverted at curse-render time.
CURSES: dict[str, str] = {
    "MachineCurse": "Exception",
    "PrimalCurse": "BaseException",
    "ImpureOffering": "ValueError",
    "PatternMismatch": "TypeError",
    "LostPattern": "KeyError",
    "BeyondTheManifest": "IndexError",
    "AbsentAugmetic": "AttributeError",
    "DivisionByTheVoid": "ZeroDivisionError",
    "ForbiddenLore": "ImportError",
    "RelicNotFound": "FileNotFoundError",
    "SpiralOfMadness": "RecursionError",
    "TheRiteIsEnded": "StopIteration",
    "UnknownInvocation": "NameError",
    "MotiveFailure": "RuntimeError",
    "RiteUnwritten": "NotImplementedError",
}

# Numeral words. Targets are integer literals, not Python names, so these
# cannot live in KEYWORDS or SOFTWORDS -- those tables' targets are validated
# against keyword.kwlist and builtins respectively.
NUMERALS: dict[str, str] = {
    "twice": "2",
    "thrice": "3",
}

# Recognised by the carrier pass, not substituted by the alias pass: they map
# to no Python word at all. Reserved nonetheless.
#
# `unsanctioned` is the odd one: the others generate *something*, while it
# generates nothing and is spliced away, reporting what it marked in
# `ConstructFacts` instead. It belongs here all the same -- this is the set
# the carrier pass dispatches on, and the set `RESERVED` is built from.
#
# Note `Sanctioned` (capital S) is already `True`, in KEYWORDS above. The two
# are a different word in a different case met in unrelated positions, and
# neither table nor `INVERSE` can confuse them; this is written down so the
# pairing is a recorded decision rather than a later discovery.
CONSTRUCT_KEYWORDS: frozenset[str] = frozenset(
    {"consecrated", "litany", "augur", "unsanctioned"}
)

LEXICON: dict[str, str] = {**KEYWORDS, **SOFTWORDS, **CURSES, **NUMERALS}
INVERSE: dict[str, str] = {py: lit for lit, py in LEXICON.items()}

# The one place that answers "is this word taken". Consumed by the corpus
# sweep's skip logic, the documented count, and Spec III's augur lint.
RESERVED: frozenset[str] = frozenset(LEXICON) | CONSTRUCT_KEYWORDS
