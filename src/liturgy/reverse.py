"""Python to Liturgy, the reverse of the alias pass.

The engine behind `transcribe`. It shares `transform`'s traversal, so the
three context rules -- attribute position, keyword-argument position, import
statements -- apply identically in both directions.
"""

from __future__ import annotations

import tokenize

from liturgy import transform as _t
from liturgy.lexicon import INVERSE

# The Liturgy spellings of import/from/as: the destination-language
# equivalent of transform._IMPORT_SAFE for this direction.
_IMPORT_SAFE = frozenset({INVERSE["import"], INVERSE["from"], INVERSE["as"]})


def _is_import_start(tok: tokenize.TokenInfo, target: str | None) -> bool:
    del target  # unused: Python source is unambiguous, unlike Liturgy source
    return tok.string in ("import", "from")


def _reverse_pass(toks: list[tokenize.TokenInfo]) -> list[_t.Substitution]:
    return _t._walk_tokens(toks, INVERSE, _is_import_start, _IMPORT_SAFE)


def to_liturgy(src: str) -> str:
    return _t.transform(src, passes=(_reverse_pass,)).python
