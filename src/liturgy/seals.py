"""Consecrated names, and the rebindings that reach them from another file.

`consecrated` enforces per compilation unit: the compiler rejects a rebinding
it can see in the same file, and Chapter VII is candid that assignment through
the module object, `setattr` and `globals()` all get through. Two of those
three are visible to a whole-tree walk, because the name is written down --
`config.PORT = 9` names PORT, and so does `setattr(config, "PORT", 9)`. This
module finds them. `globals()` and a computed `setattr` name stay invisible,
and are not guessed at.

The walk is deliberately in two halves. Seals are module-level only: a
`consecrated` inside a rite is not reachable as `module.NAME`, so nothing
outside the file could rebind it if it tried.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from .compiler import _PASSES, parse_named
from .constructs import CONSECRATED_CARRIER
from .sourcemap import char_offset
from .transform import split_lines, transform


@dataclass(frozen=True, slots=True)
class Seal:
    """A module-level `consecrated NAME`. `col` is 0-based, Liturgy coords."""

    name: str
    module: str
    line: int
    col: int


@dataclass(frozen=True, slots=True)
class Breach:
    """A rebinding of `module.name` from outside the file that sealed it.

    `how` is one of `assigned`, `setattr` or `deleted` -- the three shapes
    that are written down plainly enough to be read off the tree.
    """

    name: str
    module: str
    line: int
    col: int
    how: str


def _parsed(src: str, filename: str, *, liturgy: bool):
    """The tree to walk, and what is needed to map positions back to Liturgy.

    Mirrors `collisions.find_collisions`: the carrier pass must run, or a
    construct header is raw un-rewritten Python and `ast.parse` rejects
    ordinary correct code.
    """
    if not liturgy:
        return ast.parse(src, filename), None, []
    py, smap = transform(src, _PASSES, filename=filename)
    return parse_named(py, filename, src, smap), smap, split_lines(py)


def _attr_at(node: ast.Attribute) -> tuple[int, int]:
    """Where the attribute *name* starts, in generated-Python byte columns.

    An `ast.Attribute` reports the start of the whole expression, so
    `config.PORT` gives column 0 and the caret would sit under `config`
    while the message names PORT. The name ends the node and nothing can
    follow it there, so its start is `end_col_offset` minus its own width --
    in *bytes*, because that is what `end_col_offset` counts.
    """
    return node.end_lineno, node.end_col_offset - len(node.attr.encode("utf-8"))


def _at(node, smap, py_lines, *, pos=None) -> tuple[int, int]:
    """A node's position in Liturgy coordinates.

    `ast` counts UTF-8 bytes and everything else counts characters, so the
    column goes through `char_offset` first; `to_lit` then carries it from
    generated Python back to the litany. A `.py` file needs only the first
    half -- it has no substitutions, but its columns are still bytes.
    """
    if pos is not None:
        line, raw = pos
    else:
        line = getattr(node, "lineno", 1)
        raw = getattr(node, "col_offset", 0) or 0
    if smap is None:
        return line, raw
    py_line = py_lines[line - 1] if 0 <= line - 1 < len(py_lines) else ""
    return line, smap.to_lit(line, char_offset(py_line, raw))


def find_seals(src: str, filename: str, *, liturgy: bool = True) -> list[Seal]:
    """Every module-level `consecrated NAME` in `src`.

    Raises:
        SyntaxError: `src` does not parse.
        UnfinishedLitany: `src` ends mid-bracket or mid-string.
    """
    if not liturgy:
        # `consecrated` is Liturgy-only. A .py file cannot declare one.
        return []

    tree, smap, py_lines = _parsed(src, filename, liturgy=True)
    module = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0]

    seals = []
    # Module body only -- not ast.walk. A consecrated inside a rite is not
    # reachable as `module.NAME`, so no other file can breach it.
    for stmt in tree.body:
        if (
            isinstance(stmt, ast.AnnAssign)
            and isinstance(stmt.annotation, ast.Name)
            and stmt.annotation.id == CONSECRATED_CARRIER
            and isinstance(stmt.target, ast.Name)
        ):
            line, col = _at(stmt.target, smap, py_lines)
            seals.append(Seal(stmt.target.id, module, line, col))
    return seals


def _module_aliases(tree) -> dict[str, str]:
    """Local name -> module basename, for every plain module import.

    `invoke config` binds `config`; `invoke config styled cfg` binds `cfg`;
    `within pkg invoke config` binds `config`. A `within config invoke PORT`
    binds a *local* PORT, not the module, and is deliberately absent -- the
    local is a copy, and rebinding it does not touch the module's attribute.
    """
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                base = a.name.rsplit(".", 1)[-1]
                aliases[a.asname or a.name.split(".")[0]] = (
                    base if a.asname else a.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                # `from pkg import config` -- the bound name may be a module
                # or may be an attribute; treated as a module, and a name
                # that never matches a seal costs nothing.
                aliases[a.asname or a.name] = a.name
    return aliases


def find_breaches(
    src: str,
    filename: str,
    sealed: dict[str, set[str]],
    *,
    liturgy: bool = True,
) -> list[Breach]:
    """Rebindings in `src` of a name `sealed` elsewhere.

    `sealed` maps a module basename to the names it consecrates.

    Only rebindings *through an imported module object* are reported. A
    plain `PORT = 9` is a local binding in this file, and where it is a
    genuine rebinding -- in the sealing file itself -- the compiler has
    already rejected it, so reporting it here would double up.

    Raises:
        SyntaxError: `src` does not parse.
        UnfinishedLitany: `src` ends mid-bracket or mid-string.
    """
    tree, smap, py_lines = _parsed(src, filename, liturgy=liturgy)
    aliases = _module_aliases(tree)
    if not aliases:
        return []

    found: list[Breach] = []

    def claim(node, name: str, mod: str, how: str) -> None:
        # For an attribute the caret belongs on the name, not on the module
        # it hangs off; a setattr call has no such inner position to aim at.
        pos = _attr_at(node) if isinstance(node, ast.Attribute) else None
        line, col = _at(node, smap, py_lines, pos=pos)
        found.append(Breach(name, mod, line, col, how))

    def attribute_target(node) -> tuple[str, str] | None:
        """`alias.NAME` where alias is an imported module that seals NAME."""
        if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name):
            return None
        mod = aliases.get(node.value.id)
        if mod is not None and node.attr in sealed.get(mod, ()):
            return node.attr, mod
        return None

    # One traversal. `ast.walk` is right here for the same reason
    # `collisions` may use it: the question is whole-file and scope-blind --
    # a rebinding through a module object breaches the seal from any scope.
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                for sub in ast.walk(t):
                    hit = attribute_target(sub)
                    if hit:
                        claim(sub, *hit, "assigned")
        elif isinstance(node, ast.Delete):
            for t in node.targets:
                hit = attribute_target(t)
                if hit:
                    claim(t, *hit, "deleted")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "setattr"
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Name)
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            # A computed name is genuinely invisible; only a literal is read.
            mod = aliases.get(node.args[0].id)
            name = node.args[1].value
            if mod is not None and name in sealed.get(mod, ()):
                claim(node, name, mod, "setattr")

    return found
