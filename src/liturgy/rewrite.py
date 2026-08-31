"""The construct AST pass.

Carriers arrive as annotated assignments and `with` blocks. This turns them
into real semantics, and rejects the misuses the compiler can see.
"""

from __future__ import annotations

import ast

from .constructs import heresy
from .sourcemap import char_offset


class ConstructPass(ast.NodeTransformer):
    def __init__(
        self, filename: str, lines: list[str], smap, py_lines: list[str]
    ) -> None:
        self.filename = filename
        self.lines = lines
        self.smap = smap
        self.py_lines = py_lines
        self._litany_seq = 0

    def _heresy(self, node: ast.AST, message: str):
        """A located TechHeresy, in the same coordinates `constructs.heresy`
        uses.

        `node.col_offset` is a UTF-8 *byte* offset into the generated Python
        line, an `ast` quirk. `TechHeresy.offset` is read by
        `curse._render_syntax_location`, which runs it through
        `SourceMap.to_lit` -- and every column the SourceMap knows is a
        *character* offset, because its spans come from `tokenize`. The
        carrier pass in `constructs.py` builds its offsets from
        `tok.start[1]`, which is already character-based. One exception
        class, one renderer: the conversion has to happen here.
        """
        line = node.lineno
        text = self.lines[line - 1] if line - 1 < len(self.lines) else ""
        py_line = self.py_lines[line - 1] if line - 1 < len(self.py_lines) else ""
        col = char_offset(py_line, node.col_offset or 0)
        return heresy(message, self.filename, line, col + 1, text)

    def _liturgy_source(self, node: ast.expr) -> str:
        """The Liturgy text of an expression, for an augury's message.

        The node's columns are generated-Python columns, and two mismatches
        stand between them and the Liturgy text.

        First, `col_offset`/`end_col_offset` are UTF-8 *byte* offsets (an
        `ast` quirk), while the SourceMap's spans are *character*-indexed --
        they come from `tokenize`, which counts characters. Byte offsets are
        converted to character offsets against the **generated Python**
        line -- the offsets are into that text, not the Liturgy line -- via
        `char_offset`, before the SourceMap is consulted.

        Second, a condition can be a parenthesised expression spanning
        several physical lines. Lines are identical in *number* between
        Liturgy and generated Python (the transform's invariant), but a
        diagnostic message must not itself contain a newline, so each
        covered line is sliced separately and the pieces are collapsed with
        a single space.

        Falls back to unparsing the Python if anything is missing.
        """
        try:
            parts = []
            for lineno in range(node.lineno, node.end_lineno + 1):
                py_line = self.py_lines[lineno - 1]
                lit_line = self.lines[lineno - 1]
                byte_start = node.col_offset if lineno == node.lineno else 0
                byte_end = (
                    node.end_col_offset
                    if lineno == node.end_lineno
                    else len(py_line.encode("utf-8"))
                )
                start = self.smap.to_lit(
                    lineno, char_offset(py_line, byte_start)
                )
                end = self.smap.to_lit(
                    lineno, char_offset(py_line, byte_end)
                )
                parts.append(lit_line[start:end].strip())
            text = " ".join(p for p in parts if p)
            if text:
                return text
        except Exception:
            pass
        return ast.unparse(node)

    # -- scopes ------------------------------------------------------
    def visit_Module(self, node):
        return self._scope(node)

    def visit_Interactive(self, node):
        # `commune` compiles with mode="single", which parses to Interactive,
        # not Module. Without this the prompt got no scope visit at all: no
        # rebinding check, and -- worse -- no consecrated carrier ever
        # desugared, so on 3.12/3.13 the eagerly-evaluated annotation made
        # every `consecrated` at the prompt a NameError.
        return self._scope(node)

    def visit_FunctionDef(self, node):
        return self._scope(node)

    def visit_AsyncFunctionDef(self, node):
        return self._scope(node)

    def visit_ClassDef(self, node):
        return self._scope(node)

    def _scope(self, node):
        _reject_misplaced_auguries(node, self._heresy)
        consecrated = _collect_consecrated(node, self._heresy)
        if consecrated:
            _reject_rebindings(node, consecrated, self._heresy)
        self.generic_visit(node)
        return node

    # -- litany / augur --------------------------------------------------
    def visit_With(self, node):
        self.generic_visit(node)
        call = _carrier_call(node, "__litany__")
        if call is not None:
            return self._litany(node, call)
        call = _carrier_call(node, "__augur__")
        if call is not None:
            return self._augur(node, call)
        return node

    def _litany(self, node, call):
        if len(call.args) == 2 and not call.keywords:
            raise self._heresy(node, "curse must be passed by keyword")
        if len(call.args) != 1:
            raise self._heresy(node, "litany takes one attempt count")
        for kw in call.keywords:
            if kw.arg not in ("resting", "curse"):
                raise self._heresy(node, f"litany has no {kw.arg} argument")
        by_name = {kw.arg: kw.value for kw in call.keywords}
        if "curse" not in by_name:
            raise self._heresy(
                node, "litany needs curse= naming what to re-attempt on"
            )
        count, rest = call.args[0], by_name.get("resting")

        if isinstance(count, ast.Constant) and isinstance(count.value, int):
            if count.value < 1:
                raise self._heresy(
                    node, "a litany must be chanted at least once"
                )

        _reject_loop_control(node.body, self._heresy)
        suffix = self._litany_seq
        self._litany_seq += 1
        return _build_retry(node, count, rest, by_name["curse"], suffix)

    def _augur(self, node, call):
        if call.args or call.keywords:
            raise self._heresy(node, "augur takes no arguments")
        checks = []
        for stmt in node.body:
            if not isinstance(stmt, ast.Expr):
                raise self._heresy(
                    stmt, "an augury holds conditions, not statements"
                )
            checks.append(self._omen(node, stmt.value))
        return checks

    def _omen(self, header, test):
        """`if not (test): raise ImpureOffering("the omens forbid it -- ...")`."""
        loc = lambda n: ast.copy_location(n, header)  # noqa: E731
        message = f"the omens forbid it -- {self._liturgy_source(test)}"
        return loc(ast.If(
            test=loc(ast.UnaryOp(op=ast.Not(), operand=test)),
            body=[loc(ast.Raise(
                exc=loc(ast.Call(
                    func=loc(ast.Name(id="ValueError", ctx=ast.Load())),
                    args=[loc(ast.Constant(value=message))],
                    keywords=[],
                )),
                cause=None,
            ))],
            orelse=[],
        ))


_LOOPS = (ast.For, ast.AsyncFor, ast.While)
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
_MODULES = (ast.Module, ast.Interactive)


def _in_scope(nodes, stop=()):
    """Yield `nodes` and every descendant of them in the same scope.

    Recursion is by `ast.iter_child_nodes`, and halts *below* any node that
    opens a nested scope (or is listed in `stop`): the boundary node itself
    is yielded, so a caller can inspect it, but its children are not.

    This is the one traversal in this module, and `ast.walk` is deliberately
    not used anywhere in it. `ast.walk` flattens the tree, and every rule
    here turns on exactly the distinction that flattening destroys -- which
    scope a binding, a `universal`, a `cease` or an augury belongs to. Five
    separate defects on this branch have been one `ast.walk` or another.
    """
    for node in nodes:
        yield node
        if not isinstance(node, _SCOPES + stop):
            yield from _in_scope(ast.iter_child_nodes(node), stop)


def _repeats(node) -> bool:
    """Does this node run its body more than once?

    An unconsumed `__litany__` carrier counts. `visit_With` has not turned it
    into a `for` yet -- `_scope` runs its checks before `generic_visit`
    descends -- but it is one, and a `consecrated` inside it would rebind on
    every attempt while looking like a single declaration: precisely what the
    rule against `consecrated` in a `foreach` exists to forbid.
    """
    return isinstance(node, _LOOPS) or (
        isinstance(node, ast.With) and _carrier_call(node, "__litany__") is not None
    )


def _collect_consecrated(scope, mkerr) -> dict[str, ast.AST]:
    """Find every `NAME: __consecrated__ = v` belonging to this scope.

    Rewrites each into a plain assignment as it goes, and records the
    *replacement* node -- the rebinding check compares against these by
    identity, so recording the original would make every declaration look
    like a rebinding of itself. Nested function and class scopes are left
    for their own visit.

    Recursion is by child node, like every other walker here. It used to
    recurse only into fields that were a list whose first element was an
    `ast.stmt`, which silently skipped `Try.handlers` (a list of
    `ExceptHandler`) and `Match.cases` (a list of `match_case`) -- neither
    element type is a statement, so a `consecrated` in a `curse` or a
    `wherein` block was never desugared at all. The carrier survived into the
    compiled tree, enforcement was off, and on Python 3.12/3.13 -- where a
    module-scope annotation is still evaluated eagerly -- the module died
    with `NameError: __consecrated__`.
    """
    found: dict[str, ast.AST] = {}

    def declare(stmt, body, index, in_loop):
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

    def descend(node, in_loop):
        """Visit `node`'s children. Statement lists are handled by index,
        because a declaration has to be *replaced* in the list holding it."""
        for _field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for index, item in enumerate(value):
                    if not isinstance(item, ast.AST):
                        continue
                    if _is_consecrated(item):
                        declare(item, value, index, in_loop)
                    else:
                        visit(item, in_loop)
            elif isinstance(value, ast.AST):
                visit(value, in_loop)

    def visit(node, in_loop):
        if isinstance(node, _SCOPES):
            return  # its own visit will collect its own declarations
        descend(node, in_loop or _repeats(node))

    descend(scope, False)
    return found


def _is_consecrated(stmt) -> bool:
    return (
        isinstance(stmt, ast.AnnAssign)
        and isinstance(stmt.annotation, ast.Name)
        and stmt.annotation.id == "__consecrated__"
        and isinstance(stmt.target, ast.Name)
        and stmt.value is not None
    )


def _reaching_declaration(scope):
    """The declaration a nested scope needs to rebind a name bound here.

    `universal` (`global`) names the module's binding; `adjacent`
    (`nonlocal`) the nearest enclosing rite's. They are not interchangeable,
    and conflating them is what made this check reject correct programs. A
    class body's names are reachable by neither -- a class scope takes no
    part in closure lookup and is not the module -- so nothing nested can
    rebind a `consecrated` declared in one.
    """
    if isinstance(scope, _MODULES):
        return ast.Global
    if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return ast.Nonlocal
    return None


def _reject_rebindings(scope, consecrated, mkerr) -> None:
    """Reject every rebinding the compiler can see.

    Descends through this scope's own blocks but NOT into nested function
    or class scopes: a function assigning the same name is making its own
    local binding, not rebinding ours.

    A nested scope counts only when it declares the name with the keyword
    that actually reaches this scope and then assigns to it, which is a real
    rebinding and is visible. What is not visible -- setattr, globals(),
    assignment through the module object, exec -- is not enforced, and the
    documentation says so.
    """
    declarations = set(consecrated)
    declaring = {id(node) for node in consecrated.values()}
    reaching = _reaching_declaration(scope)

    for node in _in_scope(scope.body):
        # A nested scope still binds its own *name* in our scope, so check
        # the node itself before handing its interior to _check_nested.
        for name, at in _stored_names(node):
            if name in declarations and id(at) not in declaring:
                raise mkerr(at, f"{name} is consecrated and may not be rebound")
        if isinstance(node, _SCOPES) and reaching is not None:
            _check_nested(node, declarations, reaching, mkerr)


def _check_nested(fn, declarations, reaching, mkerr) -> None:
    """A nested scope rebinds ours only by declaring the name and storing it.

    `reaching` is `ast.Global` when the `consecrated` is at module scope and
    `ast.Nonlocal` when it is in a rite. Only that keyword reaches; the other
    one names some other binding entirely, and rejecting on it rejects
    correct programs.

    Declarations are attributed to the scope that makes them, not harvested
    from the whole subtree, so a `universal` in a doubly-nested rite no
    longer condemns its parent's ordinary locals.
    """
    own = list(_in_scope(fn.body))
    declared = {
        name for node in own if isinstance(node, reaching) for name in node.names
    }
    condemned = declarations & declared
    if condemned:
        for node in own:
            for name, at in _stored_names(node):
                if name in condemned:
                    raise mkerr(
                        at, f"{name} is consecrated and may not be rebound"
                    )

    deeper = declarations
    if reaching is ast.Nonlocal and isinstance(
        fn, (ast.FunctionDef, ast.AsyncFunctionDef)
    ):
        # `nonlocal` binds to the nearest enclosing rite that holds the name
        # as a local, so a rite that binds it locally shields ours from
        # everything below. Merely declaring it `nonlocal` does not: that
        # makes the name free here, and a deeper `nonlocal` resolves straight
        # past to ours. A class body shields nothing, being skipped entirely
        # by closure lookup -- hence the isinstance guard.
        deeper = declarations - _locals_of(fn, own)

    for inner in own:
        if isinstance(inner, _SCOPES) and deeper:
            _check_nested(inner, deeper, reaching, mkerr)


def _locals_of(fn, own) -> set[str]:
    """The names this rite binds as its own -- parameters included."""
    declared = {
        name
        for node in own
        if isinstance(node, (ast.Global, ast.Nonlocal))
        for name in node.names
    }
    bound = {name for node in own for name, _ in _stored_names(node)}
    args = fn.args
    bound |= {
        a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)
    }
    bound |= {a.arg for a in (args.vararg, args.kwarg) if a is not None}
    return bound - declared


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
    # The three below bind as surely as an assignment does, and each one
    # silently rebound a consecrated name until it was listed here.
    elif isinstance(node, ast.ExceptHandler) and node.name is not None:
        # `curse MachineCurse styled PORT:`. The name is a plain str on the
        # handler, so the handler is what carries the location.
        yield node.name, node
    elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name is not None:
        # A capture pattern: `wherein PORT:`, `wherein X styled PORT:`,
        # `wherein [head, *PORT]:`.
        yield node.name, node
    elif isinstance(node, ast.MatchMapping) and node.rest is not None:
        # `wherein {**PORT}:`
        yield node.rest, node
    elif isinstance(node, _SCOPES):
        # `rite PORT():` / `pattern PORT:` bind PORT in the *declaring*
        # scope, which is the scope this walker is checking.
        yield node.name, node


def _names_in_target(target):
    if isinstance(target, ast.Name):
        yield target
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            yield from _names_in_target(elt)
    elif isinstance(target, ast.Starred):
        yield from _names_in_target(target.value)


def _carrier_call(node: ast.With, name: str):
    """The `__litany__(...)`/`__augur__()` call, if this With is a carrier."""
    if len(node.items) != 1:
        return None
    ctx = node.items[0].context_expr
    if (
        isinstance(ctx, ast.Call)
        and isinstance(ctx.func, ast.Name)
        and ctx.func.id == name
    ):
        return ctx
    return None


def _is_augur_carrier(stmt) -> bool:
    return isinstance(stmt, ast.With) and _carrier_call(stmt, "__augur__") is not None


def _is_docstring(stmt) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def _reject_misplaced_auguries(scope, mkerr) -> None:
    """An augury is a precondition, so it opens a rite or it is nothing."""
    in_rite = isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef))
    allowed = set()
    if in_rite:
        body = scope.body
        j = 1 if body and _is_docstring(body[0]) else 0
        while j < len(body) and _is_augur_carrier(body[j]):
            allowed.add(id(body[j]))
            j += 1

    # `_in_scope` stops below a nested rite, so that rite's own legitimate
    # opening augury is left for its own scope visit to allow.
    for node in _in_scope(scope.body):
        if _is_augur_carrier(node) and id(node) not in allowed:
            if not in_rite:
                raise mkerr(node, "an augury belongs at the opening of a rite")
            raise mkerr(node, "an augury must be the opening of its rite")


def _reject_loop_control(body, mkerr) -> None:
    """`cease`/`persist` at the litany's own level bind to the retry loop.

    Inside a real loop in the body they are the author's own, so this stops
    at loops as well as at scopes -- a loop is its own break target, a rite
    a different frame entirely.
    """
    for node in _in_scope(body, _LOOPS):
        if isinstance(node, ast.Break):
            raise mkerr(node, "cease in a litany body binds to the retry")
        if isinstance(node, ast.Continue):
            raise mkerr(node, "persist in a litany body binds to the retry")


def _build_retry(node, count, rest, curse, suffix):
    """for __i in range(__n): try: body; break; except curse: ...

    `__n`/`__i` carry a per-callsite `suffix` (see `ConstructPass._litany`)
    rather than being fixed names. Two litanies sharing a name would be a
    silent-corruption bug the moment one nests inside the other: the inner
    loop's assignments would overwrite the outer's bookkeeping before the
    outer's `except` handler ever compares attempt-count against total, so
    the outer's exhaustion check would simply never fire and its exception
    would vanish instead of propagating.
    """
    count_name = f"__liturgy_n_{suffix}"
    attempt_name = f"__liturgy_attempt_{suffix}"
    loc = lambda n: ast.copy_location(n, node)  # noqa: E731

    bind_n = loc(ast.Assign(
        targets=[loc(ast.Name(id=count_name, ctx=ast.Store()))], value=count
    ))

    guard = loc(ast.If(
        test=loc(ast.Compare(
            left=loc(ast.Name(id=count_name, ctx=ast.Load())),
            ops=[ast.Lt()],
            comparators=[loc(ast.Constant(value=1))],
        )),
        body=[loc(ast.Raise(
            exc=loc(ast.Call(
                func=loc(ast.Name(id="ValueError", ctx=ast.Load())),
                args=[loc(ast.Constant(
                    value="a litany must be chanted at least once"
                ))],
                keywords=[],
            )),
            cause=None,
        ))],
        orelse=[],
    ))

    # if __i == __n - 1: raise
    reraise = loc(ast.If(
        test=loc(ast.Compare(
            left=loc(ast.Name(id=attempt_name, ctx=ast.Load())),
            ops=[ast.Eq()],
            comparators=[loc(ast.BinOp(
                left=loc(ast.Name(id=count_name, ctx=ast.Load())),
                op=ast.Sub(),
                right=loc(ast.Constant(value=1)),
            ))],
        )),
        body=[loc(ast.Raise(exc=None, cause=None))],
        orelse=[],
    ))

    handler_body = [reraise]
    if rest is not None:
        # __import__("time").sleep(rest) -- self-contained, no injected import
        handler_body.append(loc(ast.Expr(value=loc(ast.Call(
            func=loc(ast.Attribute(
                value=loc(ast.Call(
                    func=loc(ast.Name(id="__import__", ctx=ast.Load())),
                    args=[loc(ast.Constant(value="time"))],
                    keywords=[],
                )),
                attr="sleep",
                ctx=ast.Load(),
            )),
            args=[rest],
            keywords=[],
        )))))

    attempt = loc(ast.Try(
        body=[*node.body, loc(ast.Break())],
        handlers=[loc(ast.ExceptHandler(
            # `curse` is the caller's expression, re-evaluated every time
            # this handler is reached -- i.e. once per failed attempt. Only
            # the attempt *count* carries a single-evaluation requirement;
            # a non-trivial curse= expression has no such guarantee.
            type=curse, name=None, body=handler_body
        ))],
        orelse=[],
        finalbody=[],
    ))

    loop = loc(ast.For(
        target=loc(ast.Name(id=attempt_name, ctx=ast.Store())),
        iter=loc(ast.Call(
            func=loc(ast.Name(id="range", ctx=ast.Load())),
            args=[loc(ast.Name(id=count_name, ctx=ast.Load()))],
            keywords=[],
        )),
        body=[attempt],
        orelse=[],
    ))

    return [bind_n, guard, loop]
