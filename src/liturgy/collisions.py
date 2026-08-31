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
from types import SimpleNamespace

from .compiler import _PASSES
from .constructs import carrier_pass
from .lexicon import LEXICON
from .rewrite import _names_in_target, _stored_names
from .sourcemap import char_offset
from .transform import Substitution, alias_pass, split_lines, transform


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


def _import_bind_at(alias: ast.alias) -> SimpleNamespace:
    """Where the name `alias` binds actually starts, in generated Python.

    `ast.alias` (Python 3.10+) carries its own `lineno`/`col_offset` --
    but for `x as y` those point at `x`, the imported name, not `y`, the
    bound one. Unaliased, `alias.col_offset` already *is* the bound name's
    position (the first dotted component for `import a.b.c`, matching what
    `_stored_names` binds) and needs no adjustment.

    Aliased, the bound name is `y`, sitting at the *end* of the alias
    clause with nothing else able to follow it there -- so its start is
    `end_col_offset` minus its own width. Rule 3 forbids substituting an
    alias, so `asname` is guaranteed to appear in the generated Python
    exactly as spelled, and being a LEXICON word (the only reason this is
    ever called) it is plain ASCII, so the byte width and the character
    width are the same number.
    """
    if alias.asname is None:
        return SimpleNamespace(lineno=alias.lineno, col_offset=alias.col_offset)
    return SimpleNamespace(
        lineno=alias.end_lineno,
        col_offset=alias.end_col_offset - len(alias.asname),
    )


def _bindings(node):
    """Every binding, at the most precise position available.

    Clause (a) in `find_collisions` must attribute a substitution to the
    exact occurrence it produced -- not merely to the row, and not to
    whichever occurrence of the same word happens to be looked up first.
    `_stored_names` cannot supply that: it reports Assign, AugAssign,
    AnnAssign, NamedExpr, For/AsyncFor, withitem and Delete bindings against
    the *statement* (or expression) node, because that is what Spec II's
    `consecrated` needs -- it treats every target of one tuple assignment,
    or every name in one chained assignment, as opening the same scope, not
    as distinguishable occurrences. For collisions the opposite is true:
    `span, span = 1, 2` is two occurrences that must not be conflated, and
    `intone(span); span = 1` has a *load* of `span` sharing the row with
    the actual bind, which a lookup keyed by (row, word) alone cannot tell
    apart from the bind itself.

    So for those seven shapes, this re-derives the real `ast.Name` node
    directly -- via the same `_names_in_target` helper `_stored_names`
    itself uses to flatten tuple/list/starred targets, so the *rule* for
    what counts as a target is not duplicated, only the attribution of
    where to report it. A `Name`'s own column is exact in the generated
    Python regardless of what else shares its row, load or bind, same word
    or different.

    Parameters and comprehension targets are bindings `_stored_names` does
    not report at all (each opens its own scope, correctly not a rebinding
    for `consecrated`'s purposes) but each already has an exact node of its
    own -- `ast.arg`, and the comprehension's own `Name` targets.

    An exception name, a `match` capture and a `def`/`class` name are also
    plain strings on their node, not `ast.Name`s, so there is nothing more
    precise to re-derive for them. These are delegated to `_stored_names`
    unchanged, at the handler's (or pattern's) own column -- exactly as
    before. They are compound-statement headers, which Python's grammar
    forbids joining to anything else on the same source row, so the
    ambiguity a precise node exists to resolve cannot arise for them.
    `global`/`nonlocal` share that same lack of a per-name node, but --
    unlike those -- are simple statements a row can otherwise crowd with a
    load of the same word; this is accepted as a known, unlikely-to-matter
    gap rather than chased down, same as the other shapes.

    An import alias/target is a plain string too, but unlike those, it does
    have a node of its own -- `ast.alias`, since Python 3.10 -- so it is not
    delegated to `_stored_names` (whose position is the *statement's*, always
    column 0 in every case this project's own tooling reports: the `within`/
    `invoke` keyword, not the bound name). `import`'s aliases are never
    substituted (Rule 3 protects them), so clause (a) never needs precision
    there regardless -- but clause (b) does, and `_import_bind_at` derives it
    from the alias node below.
    """
    if isinstance(node, ast.Assign):
        for t in node.targets:
            yield from ((n.id, n) for n in _names_in_target(t))
    elif isinstance(node, ast.AugAssign):
        yield from ((n.id, n) for n in _names_in_target(node.target))
    elif isinstance(node, ast.AnnAssign) and node.value is not None:
        yield from ((n.id, n) for n in _names_in_target(node.target))
    elif isinstance(node, ast.NamedExpr):
        yield node.target.id, node.target
    elif isinstance(node, (ast.For, ast.AsyncFor)):
        yield from ((n.id, n) for n in _names_in_target(node.target))
    elif isinstance(node, ast.withitem) and node.optional_vars is not None:
        yield from ((n.id, n) for n in _names_in_target(node.optional_vars))
    elif isinstance(node, ast.Delete):
        for t in node.targets:
            yield from ((n.id, n) for n in _names_in_target(t))
    elif isinstance(node, ast.arg):
        yield node.arg, node
    elif isinstance(node, ast.comprehension):
        yield from ((n.id, n) for n in _names_in_target(node.target))
    elif isinstance(node, (ast.Global, ast.Nonlocal)):
        yield from ((name, node) for name in node.names)
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        for alias in node.names:
            yield alias.asname or alias.name.split(".")[0], _import_bind_at(alias)
    else:
        # Import/ImportFrom, ExceptHandler, MatchAs/MatchStar/MatchMapping,
        # and rite/pattern (FunctionDef/AsyncFunctionDef/ClassDef) names --
        # everything `_stored_names` reports that isn't re-derived above.
        # A no-op for any other node type `ast.walk` hands in.
        yield from _stored_names(node)


def _py_spans(
    subs: list[Substitution],
) -> dict[int, list[tuple[int, int, Substitution]]]:
    """Per row, each substitution's span in the *generated Python*.

    Mirrors `transform._splice`'s forward pass exactly -- sort by
    `col_start`, accumulate the same running width delta -- so a binding
    Name/arg's own column in the generated Python can be tested against
    these spans to answer "was *this exact occurrence* substituted",
    rather than merely "does this row contain a substitution to this
    text somewhere". That distinction is the whole fix: it is what tells
    a bind apart from an earlier load of the same word, and one target of
    a tuple assignment apart from another, without assuming anything
    about the order `ast.walk` or `_bindings` visits them in.
    """
    by_row: dict[int, list[Substitution]] = {}
    for s in subs:
        by_row.setdefault(s.row, []).append(s)

    spans: dict[int, list[tuple[int, int, Substitution]]] = {}
    for row, row_subs in by_row.items():
        row_subs.sort(key=lambda s: s.col_start)
        delta = 0
        row_spans: list[tuple[int, int, Substitution]] = []
        for s in row_subs:
            py_start = s.col_start + delta
            py_end = py_start + len(s.text)
            row_spans.append((py_start, py_end, s))
            delta += len(s.text) - (s.col_end - s.col_start)
        spans[row] = row_spans
    return spans


def _substitution_at(
    spans: dict[int, list[tuple[int, int, Substitution]]],
    row: int,
    py_col: int,
    reportable: set[int],
) -> Substitution | None:
    """The substitution covering `py_col`, if it is one clause (a) can use.

    `spans` is built from every pass's substitutions together (`_py_spans`
    needs the carrier pass's contribution too, or its column delta on a row
    the carrier pass also touches would disagree with the real generated
    Python). But only an `alias_pass` substitution is ever a LEXICON word
    turning into another LEXICON word -- a carrier substitution's own text
    (`""`, `"with __litany__"`, `NAME: __consecrated__`, ...) is not a
    reserved word and must never be reported as one. `reportable` holds
    `id()` of the substitutions that came from `alias_pass`, so a carrier
    substitution can still occupy a span here (to keep the delta right)
    without ever being handed back as a match.
    """
    for py_start, py_end, s in spans.get(row, ()):
        if py_start <= py_col < py_end and id(s) in reportable:
            return s
    return None


def find_collisions(
    src: str, filename: str, *, liturgy: bool
) -> list[Collision]:
    """Every binding in `src` whose name is a reserved Liturgy word.

    Two clauses, because a binding can collide two ways:

    (a) A substitution produced the bound name -- the author wrote `span`
        and it became `range`. Where the binding has its own exact node --
        an `ast.Name` in Store/Del context, or an `ast.arg` -- that node's
        own column in the generated Python is tested against the
        substitutions on its row (`_py_spans`/`_substitution_at`), so the
        exact occurrence is matched regardless of what else -- a load of
        the same word, a second identical target, an unrelated earlier
        substitution -- shares the row. The reported word and column come
        from the matched `Substitution` itself, which is already exact and
        in Liturgy coordinates. The handful of shapes with no such node
        (an import alias/target, an exception name, a `match` capture, a
        `def`/`class` name) fall back to a plain (row, word) lookup, which
        is safe for them specifically because Python's grammar forbids two
        of these compound-statement headers sharing one source row.
    (b) The bound name is itself a Liturgy word, surviving unsubstituted
        because an exemption protected it -- `invoke os styled span` binds
        `span`, and every later reference to it becomes `range`. The AST
        node's own column is a *generated-Python* column and is mapped
        back to Liturgy coordinates the same two-step way
        `rewrite._liturgy_source` does: `char_offset` from UTF-8 bytes to
        characters against the *generated* line, then `SourceMap.to_lit`
        from generated-Python characters to Liturgy. This corrects the
        column even for the statement-start shapes, where it was already
        usually right, and for a parameter or a `match` capture, where an
        earlier substitution on the same row can shift it (`rite` -> `def`
        is one character shorter).

    Clause (b) alone is the whole rule for a `.py` file, which has no
    substitutions and no SourceMap -- but the AST's column is still a UTF-8
    byte offset, so it still goes through `char_offset`; only the `to_lit`
    half of the two-step is what a `.py` file does not need.

    Raises:
        UnfinishedLitany: `src` ends mid-bracket or mid-string.
        SyntaxError: `src` does not parse. A loud collision -- `render = 1`
            becoming `return = 1` -- arrives this way, and the caller reports
            it as a compile failure rather than a collision.
    """
    if liturgy:
        # The same passes `compiler` compiles with (`_PASSES`, not the
        # alias pass alone) -- a construct header (`consecrated`, `litany`,
        # `augur`) is still raw, un-rewritten Python without the carrier
        # pass, and `ast.parse` below would reject it as a syntax error on
        # ordinary correct code, never reaching the compile step that is
        # meant to be the one place augur can disagree with chant.
        py, smap = transform(src, _PASSES, filename=filename)
        tree = ast.parse(py, filename)
        py_lines = split_lines(py)
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
        alias_subs = alias_pass(toks)
        carrier_subs = carrier_pass(toks)
        all_subs = alias_subs + carrier_subs
        row_spans = _py_spans(all_subs)
        reportable = {id(s) for s in alias_subs}
        stmt_subs = {(s.row, s.text): s for s in alias_subs}
    else:
        tree = ast.parse(src, filename)
        smap = None
        py_lines = []
        row_spans = {}
        stmt_subs = {}
        reportable = set()

    lines = split_lines(src)
    found: set[Collision] = set()

    for node in ast.walk(tree):
        for name, at in _bindings(node):
            line = getattr(at, "lineno", 0)
            raw_col = getattr(at, "col_offset", 0) or 0
            py_line = py_lines[line - 1] if 0 <= line - 1 < len(py_lines) else ""
            py_col = char_offset(py_line, raw_col) if smap is not None else raw_col

            sub = None
            if smap is not None:
                if isinstance(at, (ast.Name, ast.arg)):
                    sub = _substitution_at(row_spans, line, py_col, reportable)
                else:
                    sub = stmt_subs.get((line, name))

            if sub is not None:
                word = lines[line - 1][sub.col_start : sub.col_end]
                col = sub.col_start
            elif name in LEXICON:
                word = name
                if smap is not None:
                    col = smap.to_lit(line, py_col)
                else:
                    # A .py file has no map, but `col_offset` is still a UTF-8
                    # byte offset. Source and "generated" are the same text
                    # here, so the one `char_offset` is the whole conversion.
                    src_line = lines[line - 1] if 0 <= line - 1 < len(lines) else ""
                    col = char_offset(src_line, raw_col)
            else:
                continue
            found.add(
                Collision(line, col, word, LEXICON[word], _is_quiet(LEXICON[word]))
            )

    return sorted(found, key=lambda c: (c.line, c.col, c.word))
