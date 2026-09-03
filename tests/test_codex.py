"""Codices: a package of litanies, and the two tongues interleaved.

A directory holding an ``__init__.lit`` is an ordinary Python package -- a
*codex*. Nothing in ``src/`` implements this; it falls out of the path hook
carrying the stdlib loader details alongside our own (see
``loader.install``). These tests pin that, because a hook registered with
only the ``.lit`` details would still match every directory and the mixed
cases below would stop working silently.

The module names here are deliberately long and unlovely. A test module was
once named ``broken``, collided with a cached ``sys.modules`` entry, and
passed alone while failing in the suite.
"""

from __future__ import annotations

import importlib
import importlib.util
import io
import pathlib
import sys

import pytest

from liturgy import loader
from liturgy.tooling import forge

LIT_CODEX = "codex_reliquarium_lit"
PY_CODEX = "codex_sanctum_py"

# The codex's own litany: a relative import, and a name of its own.
INIT_LIT = """\
within .relics invoke waken


rite bless(name: str) -> str:
    render f"Ave Omnissiah, {name}"
"""

RELICS_LIT = """\
rite waken(n: int) -> str:
    render f"relic {n} wakened"
"""

# A .py submodule living inside a .lit codex.
TALLY_PY = """\
def tally(items):
    return len(items)
"""

# A .lit submodule living inside a .py package.
ORISON_LIT = """\
rite orison() -> str:
    render "spoken in the sanctum"
"""


def _purge(prefix: str) -> None:
    for name in [n for n in sys.modules if n == prefix or n.startswith(prefix + ".")]:
        del sys.modules[name]


@pytest.fixture
def codices(tmp_path, monkeypatch):
    """Two packages on sys.path: a .lit codex and a .py one."""
    lit = tmp_path / LIT_CODEX
    lit.mkdir()
    (lit / "__init__.lit").write_text(INIT_LIT)
    (lit / "relics.lit").write_text(RELICS_LIT)
    (lit / "tally.py").write_text(TALLY_PY)

    py = tmp_path / PY_CODEX
    py.mkdir()
    (py / "__init__.py").write_text("")
    (py / "orison.lit").write_text(ORISON_LIT)

    monkeypatch.syspath_prepend(str(tmp_path))
    loader.install()
    importlib.invalidate_caches()

    # Clean before as well as after: a previous test in the same process may
    # have left a same-named module behind, and a cached sys.modules entry
    # would make every assertion below vacuous.
    _purge(LIT_CODEX)
    _purge(PY_CODEX)
    try:
        yield tmp_path
    finally:
        _purge(LIT_CODEX)
        _purge(PY_CODEX)
        sys.path_importer_cache.pop(str(tmp_path), None)
        sys.path_importer_cache.pop(str(lit), None)
        sys.path_importer_cache.pop(str(py), None)


def test_a_codex_imports_as_a_package(codices):
    codex = importlib.import_module(LIT_CODEX)

    assert codex.bless("Magos") == "Ave Omnissiah, Magos"
    # It is a package, not a lone module, and its own litany is the .lit file.
    assert hasattr(codex, "__path__")
    assert codex.__file__.endswith("__init__.lit")


def test_a_dotted_submodule_of_a_codex_imports(codices):
    relics = importlib.import_module(f"{LIT_CODEX}.relics")

    assert relics.waken(1) == "relic 1 wakened"
    assert relics.__file__.endswith("relics.lit")


def test_a_relative_import_inside_a_codex_resolves(codices):
    # __init__.lit's first line is `within .relics invoke waken`. If the
    # relative form did not resolve against the codex, importing it would
    # raise rather than bind the name.
    codex = importlib.import_module(LIT_CODEX)

    assert codex.waken(2) == "relic 2 wakened"
    assert codex.waken is sys.modules[f"{LIT_CODEX}.relics"].waken


def test_a_py_submodule_inside_a_lit_codex_imports(codices):
    # Mixed direction one. The path hook installed for the codex directory
    # must still carry SourceFileLoader, or this .py is invisible.
    tally = importlib.import_module(f"{LIT_CODEX}.tally")

    assert tally.tally([1, 2, 3]) == 3
    assert tally.__file__.endswith("tally.py")


def test_a_lit_submodule_inside_a_py_package_imports(codices):
    # Mixed direction two. The package is plain Python; only the submodule
    # is a litany.
    orison = importlib.import_module(f"{PY_CODEX}.orison")

    assert orison.orison() == "spoken in the sanctum"
    assert orison.__file__.endswith("orison.lit")


def test_forge_writes_a_codex_bytecode_where_import_looks(codices):
    lit = codices / LIT_CODEX

    buf = io.StringIO()
    assert forge([str(lit)], out=buf) == 0

    for name in ("__init__.lit", "relics.lit"):
        cached = pathlib.Path(importlib.util.cache_from_source(str(lit / name)))
        assert cached.exists(), f"no bytecode for {name}"
        assert cached.parent == lit / "__pycache__"
