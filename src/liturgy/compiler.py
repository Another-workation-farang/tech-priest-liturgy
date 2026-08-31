"""Liturgy source to a code object.

`transform` is text-to-text and stays that way -- the reverse pass, the
round-trip property and most of the suite are built on it. The construct
layer needs an AST stage between parse and compile, so it layers on top
here rather than changing that contract.
"""

from __future__ import annotations

import ast
import types

from .transform import transform


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
    py, _smap = transform(src, filename=filename)
    tree = ast.parse(py, filename, mode)
    return compile(
        tree, filename, mode, dont_inherit=dont_inherit, optimize=optimize
    )
