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
from .sourcemap import SourceMap, char_offset
from .transform import (
    DEFAULT_PASSES,
    name_the_substitution,
    split_lines,
    transform,
)

_PASSES = (*DEFAULT_PASSES, carrier_pass)

# What `constructs.heresy` writes when it has no filename to write. The token
# passes are handed a bare token list -- see `transform.TokenPass` -- so the
# carrier pass genuinely cannot know what file it is reading.
_UNKNOWN = "<unknown>"


def parse_named(py: str, filename: str, src: str, smap: SourceMap, mode: str = "exec") -> ast.AST:
    """`ast.parse`, naming the substitution a failure points into.

    `twice = 1` fails as "cannot assign to literal", which is
    unintelligible until something says twice became 2. One wrapper, used
    here and by `collisions.find_collisions`, so `augur` and `chant`
    cannot disagree about the message.
    """
    try:
        return ast.parse(py, filename, mode)
    except SyntaxError as err:
        name_the_substitution(err, src, py, smap)
        raise


def _artifacts(
    src: str, filename: str, *, mode: str = "exec", sanction: bool = True
) -> tuple[ast.AST, str, SourceMap]:
    """The rewritten tree, plus the generated Python and map it came from."""
    try:
        out = transform(src, _PASSES, filename=filename)
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
    py, smap = out.python, out.source_map
    tree = parse_named(py, filename, src, smap, mode)
    tree = ConstructPass(
        filename, split_lines(src), smap, split_lines(py), out.facts,
        sanction=sanction,
    ).visit(tree)
    ast.fix_missing_locations(tree)
    return tree, py, smap


def _rewritten_tree(
    src: str, filename: str, *, mode: str = "exec", sanction: bool = True
) -> ast.AST:
    tree, _, _ = _artifacts(src, filename, mode=mode, sanction=sanction)
    return tree


def compile_litany(
    src: str,
    filename: str,
    *,
    mode: str = "exec",
    dont_inherit: bool = True,
    optimize: int = -1,
    sanction: bool = True,
) -> types.CodeType:
    """Compile Liturgy source, applying the construct rewrites.

    `sanction=False` compiles without Spec IV's archetype rule and with
    every other rejection intact. It exists for one caller: `transcribe`,
    whose backstop compiles Liturgy that no author wrote, to ask "is this
    a program?" -- not "does this meet the annotation policy?". Python does
    not require annotations, so machine-rendered Python cannot be expected
    to carry them, and judging it by a policy about authored litanies is a
    category error. Nothing that *chants* a litany may pass it: a rule
    `chant` enforces and `augur` does not would be the one disagreement
    Spec II forbids.

    Raises:
        UnfinishedLitany: the source ends mid-bracket or mid-string.
        SyntaxError: a complete tokenisation or parse error.
        TechHeresy: a construct was used in a way the compiler rejects.
    """
    tree, py, smap = _artifacts(src, filename, mode=mode, sanction=sanction)
    try:
        return compile(
            tree, filename, mode, dont_inherit=dont_inherit, optimize=optimize
        )
    except SyntaxError as err:
        # The symtable pass fails here, after the parse succeeded --
        # `render 5` at module level arrives as "'return' outside
        # function". A tree-compile's offsets count UTF-8 bytes (they come
        # from the node's `col_offset`), unlike the parser's own, which
        # count characters; everything downstream -- the caret mapping in
        # `curse`, `name_the_substitution` -- speaks characters, so they
        # are converted in place before the error travels further.
        py_lines = split_lines(py)

        def to_char(lineno: int | None, offset: int | None) -> int | None:
            if not lineno or not offset or offset < 1:
                return offset
            line = py_lines[lineno - 1] if lineno - 1 < len(py_lines) else ""
            return char_offset(line, offset - 1) + 1

        err.offset = to_char(err.lineno, err.offset)
        err.end_offset = to_char(err.end_lineno, err.end_offset)
        name_the_substitution(err, src, py, smap)
        raise
