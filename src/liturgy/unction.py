"""Render a litany as Python text, with a map from its lines back to the litany's.

Constructs are desugared on the AST, so no Python text keeps the litany's line
numbers; Nuitka compiles text. `ast.unparse` gives the text and `line_map` the
generated-line -> litany-line table the executable's curses read.
"""

import ast
import importlib.util
import os
import pathlib
import shutil

from . import rubric
from .compiler import _artifacts
from .lexicon import INVERSE
from .transform import split_lines

HOOK_MODULE = "__liturgy_curse"


class UnctionFault(Exception):
    def __init__(self, path: str, reason: str):
        super().__init__(reason)
        self.path = path
        self.reason = reason


def _lockstep(a: ast.AST, b: ast.AST, out: dict[int, int]) -> None:
    # Every located node, pre-order, first wins: decorators, `except` clauses and
    # `case` patterns have lines of their own that a statement-only map would miss.
    if getattr(a, "lineno", 0):
        out.setdefault(b.lineno, a.lineno)
    for (_, va), (_, vb) in zip(ast.iter_fields(a), ast.iter_fields(b)):
        if isinstance(va, list):
            for x, y in zip(va, vb):
                if isinstance(x, ast.AST):
                    _lockstep(x, y, out)
        elif isinstance(va, ast.AST):
            _lockstep(va, vb, out)


def line_map(tree: ast.Module, text: str, path: str = "<unknown>") -> dict[int, int]:
    """{generated line: litany line} for every located node, first wins."""
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


def bake(tables: rubric.Tables) -> str:
    """The generated `__liturgy_curse.py`: rubric's source, then the baked tables."""
    return (
        pathlib.Path(rubric.__file__).read_text(encoding="utf-8")
        + f"\n_TABLES = {tables!r}\n_NAMES = {dict(INVERSE)!r}\n"
        + "install(TableSeer(_TABLES, os.path.dirname(os.path.abspath(__file__))), _NAMES)\n"
    )


def stage(entry: pathlib.Path, files: list[pathlib.Path], staging: pathlib.Path) -> int:
    """Mirror the project under `staging` as plain Python; returns the litany count."""
    root = pathlib.Path(os.path.abspath(entry.parent))
    entry_abs = os.path.abspath(entry)
    if not any(f.suffix == ".lit" and os.path.abspath(f) == entry_abs for f in files):
        raise UnctionFault(str(entry), "is not among the gathered litanies")
    tables: rubric.Tables = {}
    count = 0
    twinned = {os.path.abspath(f.with_suffix("")) for f in files if f.suffix == ".lit"}
    for path in files:
        rel = pathlib.Path(os.path.abspath(path)).relative_to(root)
        if rel.as_posix() == f"{HOOK_MODULE}.py" or (rel.as_posix() == f"{HOOK_MODULE}.lit"):
            raise UnctionFault(str(path), f"would overwrite the generated {HOOK_MODULE}.py")
        # `chant` prefers x.lit to x.py, so the executable must too.
        if path.suffix == ".py" and os.path.abspath(path.with_suffix("")) in twinned:
            continue
        dest = staging / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix != ".lit":
            shutil.copy2(path, dest)
            continue
        try:
            src = importlib.util.decode_source(path.read_bytes())
            text, lmap = render_litany(src, str(path), entry=os.path.abspath(path) == entry_abs)
        except (UnicodeDecodeError, ValueError, LookupError) as err:
            raise UnctionFault(str(path), f"{type(err).__name__}: {err}") from err
        dest = dest.with_suffix(".py")
        dest.write_text(text, encoding="utf-8")
        # Keyed as the runtime keys a frame's filename: one shared key function.
        lines = [l.rstrip("\n") for l in split_lines(src)]
        tables[rubric.key_for(str(dest), str(staging))] = (rel.as_posix(), lmap, lines)
        count += 1
    (staging / f"{HOOK_MODULE}.py").write_text(bake(tables), encoding="utf-8")
    return count
