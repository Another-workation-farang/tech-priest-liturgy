"""Reserved words used as identifiers.

`augur` reports them; `transcribe` refuses on them. One definition, so the
two verbs cannot drift apart about what counts.
"""

from __future__ import annotations

import ast
import io
import keyword
import tokenize
from dataclasses import dataclass

from .lexicon import LEXICON
from .rewrite import _names_in_target, _stored_names
from .sourcemap import char_offset
from .transform import alias_pass, split_lines, transform


@dataclass(frozen=True, slots=True)
class Collision:
    """A binding whose source-language name is reserved.

    `col` is 0-based. `quiet` means the substitution target is not a Python
    keyword, so the file compiles and silently shadows -- which is the whole
    reason this check exists.
    """

    line: int
    col: int
    word: str
    target: str
    quiet: bool


def _is_quiet(target: str) -> bool:
    return not keyword.iskeyword(target)


def _bindings(node):
    """Every binding, including three `_stored_names` does not report.

    `_stored_names` exists for Spec II's `consecrated` check, where a
    parameter and a comprehension target are correctly *not* rebindings --
    each opens its own scope. For collisions they matter, because the
    substitution does not care about scope:

        def f(span):        ->  def f(range):
        [p for p in xs]     ->  [p for p in xs]  with p == `pattern`
                                -> `class`, a syntax error

    Measured against the stdlib corpus, adding these three took the
    disagreement with the round-trip sweep's own predicate from 28 files to
    2 -- and both survivors are the sweep being wrong, not this.

    Extending `_stored_names` itself was rejected: it would change what
    Spec II's `consecrated` rejects, for no benefit there.
    """
    yield from _stored_names(node)
    if isinstance(node, ast.arg):
        yield node.arg, node
    elif isinstance(node, ast.comprehension):
        yield from ((n.id, n) for n in _names_in_target(node.target))
    elif isinstance(node, (ast.Global, ast.Nonlocal)):
        yield from ((name, node) for name in node.names)


def find_collisions(
    src: str, filename: str, *, liturgy: bool
) -> list[Collision]:
    """Every binding in `src` whose name is a reserved Liturgy word.

    Two clauses, because a binding can collide two ways:

    (a) A substitution produced the bound name -- the author wrote `span` and
        it became `range`. Position comes from the `Substitution` itself,
        which is already in Liturgy coordinates and exact. Two bindings on
        one row can share both row and substituted text -- `span, span = 1,
        2` -- so substitutions are consumed in left-to-right order rather
        than collapsed by `(row, text)`; `_bindings` yields same-node
        multi-target bindings in source order, matching that.
    (b) The bound name is itself a Liturgy word, surviving unsubstituted
        because an exemption protected it -- `invoke os styled span` binds
        `span`, and every later reference to it becomes `range`. The AST
        node's own column is a *generated-Python* column -- for `for`/
        `def`/`class`/`except`/`import` it is only the statement's start
        (Line is exact regardless), but for a parameter or a `match`
        capture it is the name's own column, and an earlier substitution on
        the same row can have shifted it (`rite` -> `def` is one character
        shorter). Either way it is mapped back to Liturgy coordinates the
        same two-step way `rewrite._liturgy_source` does: `char_offset` from
        UTF-8 bytes to characters against the *generated* line, then
        `SourceMap.to_lit` from generated-Python characters to Liturgy.

    Clause (b) alone is the whole rule for a `.py` file, which has no
    substitutions and no SourceMap -- the AST's own column already is the
    answer.

    Raises:
        UnfinishedLitany: `src` ends mid-bracket or mid-string.
        SyntaxError: `src` does not parse. A loud collision -- `render = 1`
            becoming `return = 1` -- arrives this way, and the caller reports
            it as a compile failure rather than a collision.
    """
    if liturgy:
        py, smap = transform(src, filename=filename)
        tree = ast.parse(py, filename)
        py_lines = split_lines(py)
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
        subs: dict[tuple[int, str], list] = {}
        for s in alias_pass(toks):
            subs.setdefault((s.row, s.text), []).append(s)
    else:
        tree = ast.parse(src, filename)
        smap = None
        py_lines = []
        subs = {}

    lines = split_lines(src)
    found: set[Collision] = set()

    for node in ast.walk(tree):
        for name, at in _bindings(node):
            line = getattr(at, "lineno", 0)
            queue = subs.get((line, name))
            sub = queue.pop(0) if queue else None
            if sub is not None:
                word = lines[line - 1][sub.col_start : sub.col_end]
                col = sub.col_start
            elif name in LEXICON:
                word = name
                raw_col = getattr(at, "col_offset", 0) or 0
                if smap is None:
                    col = raw_col
                else:
                    py_line = py_lines[line - 1] if line - 1 < len(py_lines) else ""
                    col = smap.to_lit(line, char_offset(py_line, raw_col))
            else:
                continue
            found.add(
                Collision(line, col, word, LEXICON[word], _is_quiet(LEXICON[word]))
            )

    return sorted(found, key=lambda c: (c.line, c.col, c.word))
