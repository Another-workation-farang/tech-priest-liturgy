"""The construct AST pass.

Carriers arrive as annotated assignments and `with` blocks. This turns them
into real semantics, and rejects the misuses the compiler can see.
"""

from __future__ import annotations

import ast

from .constructs import heresy


class ConstructPass(ast.NodeTransformer):
    def __init__(self, filename: str, lines: list[str]) -> None:
        self.filename = filename
        self.lines = lines

    def _heresy(self, node: ast.AST, message: str):
        line = node.lineno
        text = self.lines[line - 1] if line - 1 < len(self.lines) else ""
        return heresy(
            message, self.filename, line, (node.col_offset or 0) + 1, text
        )

    # -- scopes ------------------------------------------------------
    def visit_Module(self, node):
        return self._scope(node)

    def visit_FunctionDef(self, node):
        return self._scope(node)

    def visit_AsyncFunctionDef(self, node):
        return self._scope(node)

    def visit_ClassDef(self, node):
        return self._scope(node)

    def _scope(self, node):
        consecrated = _collect_consecrated(node, self._heresy)
        if consecrated:
            _reject_rebindings(node, consecrated, self._heresy)
        self.generic_visit(node)
        return node


_LOOPS = (ast.For, ast.AsyncFor, ast.While)
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _collect_consecrated(scope, mkerr) -> dict[str, ast.AST]:
    """Find `NAME: __consecrated__ = v` directly in this scope's body.

    Rewrites each into a plain assignment as it goes, and records the
    *replacement* node -- the rebinding check compares against these by
    identity, so recording the original would make every declaration look
    like a rebinding of itself. Nested function and class scopes are left
    for their own visit.
    """
    found: dict[str, ast.AST] = {}

    def walk(body, in_loop):
        for index, stmt in enumerate(body):
            if isinstance(stmt, _SCOPES):
                continue
            if _is_consecrated(stmt):
                name = stmt.target.id
                if in_loop:
                    raise mkerr(stmt, f"{name} is consecrated inside a loop")
                if name in found:
                    raise mkerr(stmt, f"{name} is already consecrated")
                stmt.target.ctx = ast.Store()
                plain = ast.Assign(targets=[stmt.target], value=stmt.value)
                ast.copy_location(plain, stmt)
                ast.fix_missing_locations(plain)
                body[index] = plain
                found[name] = plain
                continue
            for _field, value in ast.iter_fields(stmt):
                if (
                    isinstance(value, list)
                    and value
                    and isinstance(value[0], ast.stmt)
                ):
                    walk(value, in_loop or isinstance(stmt, _LOOPS))

    walk(scope.body, False)
    return found


def _is_consecrated(stmt) -> bool:
    return (
        isinstance(stmt, ast.AnnAssign)
        and isinstance(stmt.annotation, ast.Name)
        and stmt.annotation.id == "__consecrated__"
        and isinstance(stmt.target, ast.Name)
        and stmt.value is not None
    )


def _reject_rebindings(scope, consecrated, mkerr) -> None:
    """Reject every rebinding the compiler can see.

    Descends through this scope's own blocks but NOT into nested function
    or class scopes: a function assigning the same name is making its own
    local binding, not rebinding ours. `ast.walk` is deliberately not used
    for that reason -- it would flatten the tree and reject legitimate
    shadowing.

    A nested scope counts only when it declares the name `global` or
    `nonlocal` and then assigns to it, which is a real rebinding and is
    visible. What is not visible -- setattr, globals(), assignment through
    the module object, exec -- is not enforced, and the documentation says
    so.
    """
    declarations = set(consecrated)
    declaring = {id(node) for node in consecrated.values()}

    def check(node):
        for name, at in _stored_names(node):
            if name in declarations and id(at) not in declaring:
                raise mkerr(at, f"{name} is consecrated and may not be rebound")

    def walk(node):
        if isinstance(node, _SCOPES) and node is not scope:
            _check_nested(node, declarations, mkerr)
            return
        check(node)
        for child in ast.iter_child_nodes(node):
            walk(child)

    for stmt in scope.body:
        walk(stmt)


def _check_nested(fn, declarations, mkerr) -> None:
    """A nested scope rebinds ours only via `universal`/`adjacent`."""
    declared: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            declared.update(node.names)
    reaching = declarations & declared
    if not reaching:
        return
    for node in ast.walk(fn):
        for name, at in _stored_names(node):
            if name in reaching:
                raise mkerr(at, f"{name} is consecrated and may not be rebound")


def _stored_names(node):
    """(name, node) for every binding this statement performs."""
    if isinstance(node, ast.Assign):
        for t in node.targets:
            yield from ((n.id, node) for n in _names_in_target(t))
    elif isinstance(node, ast.AugAssign):
        yield from ((n.id, node) for n in _names_in_target(node.target))
    elif isinstance(node, ast.AnnAssign) and node.value is not None:
        yield from ((n.id, node) for n in _names_in_target(node.target))
    elif isinstance(node, ast.NamedExpr):
        yield node.target.id, node
    elif isinstance(node, (ast.For, ast.AsyncFor)):
        yield from ((n.id, node) for n in _names_in_target(node.target))
    elif isinstance(node, ast.withitem) and node.optional_vars is not None:
        # Unlike the other branches, `node` itself carries no location --
        # `withitem` has no lineno/col_offset -- so report against the
        # bound Name instead, which does.
        yield from (
            (n.id, n) for n in _names_in_target(node.optional_vars)
        )
    elif isinstance(node, ast.Delete):
        for t in node.targets:
            yield from ((n.id, node) for n in _names_in_target(t))
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        for alias in node.names:
            yield alias.asname or alias.name.split(".")[0], node


def _names_in_target(target):
    if isinstance(target, ast.Name):
        yield target
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            yield from _names_in_target(elt)
    elif isinstance(target, ast.Starred):
        yield from _names_in_target(target.value)
