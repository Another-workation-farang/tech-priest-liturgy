"""Python -> Liturgy, for test fixtures only.

Lives in `tests/`, not in the package: it is test support and has no
business inside the installed wheel. Its one dependency on the package is
`transform._walk_tokens`, already a deliberate two-module contract.

Not the Spec III `transcribe` verb: this exists so the round-trip property
test can generate Liturgy from real Python and assert we get the Python back.

Reuses `transform._walk_tokens`, the traversal `alias_pass` is built on, with
the lookup table inverted. Two things do not simply mirror the forward pass:

- Import-statement detection. The forward pass checks both the raw token
  and its translation, because Liturgy source may spell `import`/`from`
  either way (it is a superset of Python). This pass only ever sees real
  Python, where the keyword is unambiguous, so checking the raw token alone
  is enough — the translation (a Liturgy word, by construction never equal
  to the literal string "import" or "from") would never fire anyway, so we
  drop that half of the check rather than carry along a branch that is
  always false in this direction.
- The import-safe set. `_IMPORT_SAFE` in `transform.py` holds the Python
  spellings of import/from/as, because that is the *destination* language
  for the forward pass. Here the destination is Liturgy, so the safe set
  must hold the Liturgy spellings instead — reusing the Python one blindly
  would silently strip the `invoke`/`within`/`styled` keywords back out of
  every translated import statement.
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
    return _t.transform(src, passes=(_reverse_pass,))[0]
