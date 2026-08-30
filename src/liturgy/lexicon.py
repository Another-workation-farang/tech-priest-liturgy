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

LEXICON: dict[str, str] = {**KEYWORDS, **SOFTWORDS, **CURSES}
INVERSE: dict[str, str] = {py: lit for lit, py in LEXICON.items()}
