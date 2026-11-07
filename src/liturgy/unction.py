"""Render a litany as Python text, with a map from its lines back to the litany's.

Constructs are desugared on the AST, so no Python text keeps the litany's line
numbers; Nuitka compiles text. `ast.unparse` gives the text and `line_map` the
generated-line -> litany-line table the executable's curses read.
"""

import ast

from .compiler import _artifacts

HOOK_MODULE = "__liturgy_curse"


class UnctionFault(Exception):
    def __init__(self, path: str, reason: str):
        super().__init__(reason)
        self.path = path
        self.reason = reason


def _lockstep(a: ast.AST, b: ast.AST, out: dict[int, int]) -> None:
    if isinstance(a, ast.stmt) and getattr(a, "lineno", 0):
        out.setdefault(b.lineno, a.lineno)
    for (_, va), (_, vb) in zip(ast.iter_fields(a), ast.iter_fields(b)):
        if isinstance(va, list):
            for x, y in zip(va, vb):
                if isinstance(x, ast.AST):
                    _lockstep(x, y, out)
        elif isinstance(va, ast.AST):
            _lockstep(va, vb, out)


def line_map(tree: ast.Module, text: str, path: str = "<unknown>") -> dict[int, int]:
    """{generated statement line: litany statement line}, first wins."""
    try:
        again = ast.parse(text)
    except SyntaxError:
        raise UnctionFault(path, "does not render as valid Python") from None
    if ast.dump(tree) != ast.dump(again):
        raise UnctionFault(path, "does not survive rendering as Python")
    out: dict[int, int] = {}
    _lockstep(tree, again, out)
    return out


def _insert_hook(tree: ast.Module) -> None:
    body = tree.body
    i = 0
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        i = 1
    while i < len(body) and isinstance(body[i], ast.ImportFrom) and body[i].module == "__future__":
        i += 1
    hook = ast.Import(names=[ast.alias(name=HOOK_MODULE)])
    # Line 0 everywhere: the lockstep walk skips it, so it maps to no litany line.
    hook.lineno = hook.end_lineno = hook.col_offset = hook.end_col_offset = 0
    body.insert(i, hook)


def render_litany(src: str, filename: str, *, entry: bool = False) -> tuple[str, dict[int, int]]:
    tree = _artifacts(src, filename, sanction=True)[0]
    if entry:
        _insert_hook(tree)
    text = ast.unparse(tree) + "\n"
    return text, line_map(tree, text, filename)
