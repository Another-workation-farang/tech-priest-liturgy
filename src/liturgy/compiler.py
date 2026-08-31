"""Liturgy source to a code object.

`transform` is text-to-text and stays that way -- the reverse pass, the
round-trip property and most of the suite are built on it. The construct
layer needs an AST stage between parse and compile, so it layers on top
here rather than changing that contract.
"""

from __future__ import annotations

import ast
import types

from .constructs import TechHeresy, carrier_pass
from .rewrite import ConstructPass
from .transform import DEFAULT_PASSES, split_lines, transform

_PASSES = (*DEFAULT_PASSES, carrier_pass)

# What `constructs.heresy` writes when it has no filename to write. The token
# passes are handed a bare token list -- see `transform.TokenPass` -- so the
# carrier pass genuinely cannot know what file it is reading.
_UNKNOWN = "<unknown>"


def _rewritten_tree(src: str, filename: str, *, mode: str = "exec") -> ast.AST:
    try:
        py, smap = transform(src, _PASSES, filename=filename)
    except TechHeresy as err:
        # The carrier pass raises for the two commonest construct typos --
        # `consecrated = 5` and `litany 3:` -- and cannot name the file.
        # Filling it in here is what lets `curse` recognise a .lit anchor:
        # without it `_lit_location` returns None, `_drop_launcher_frames`
        # finds nothing to cut at, and the user gets ten frames of
        # runpy/cli/compiler/transform/constructs plumbing instead of the
        # two-line render every other Liturgy error produces. Threading a
        # filename through the TokenPass protocol would cost every pass a
        # parameter to serve one of them.
        if err.filename == _UNKNOWN:
            err.filename = filename
        raise
    tree = ast.parse(py, filename, mode)
    tree = ConstructPass(
        filename, split_lines(src), smap, split_lines(py)
    ).visit(tree)
    ast.fix_missing_locations(tree)
    return tree


def compile_litany(
    src: str,
    filename: str,
    *,
    mode: str = "exec",
    dont_inherit: bool = True,
    optimize: int = -1,
) -> types.CodeType:
    """Compile Liturgy source, applying the construct rewrites.

    Raises:
        UnfinishedLitany: the source ends mid-bracket or mid-string.
        SyntaxError: a complete tokenisation or parse error.
        TechHeresy: a construct was used in a way the compiler rejects.
    """
    tree = _rewritten_tree(src, filename, mode=mode)
    return compile(
        tree, filename, mode, dont_inherit=dont_inherit, optimize=optimize
    )
