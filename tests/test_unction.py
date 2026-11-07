import ast
import pathlib
import subprocess
import sys

import pytest
from conftest import OMENS, chant_run, normalise

from liturgy import unction
from liturgy.tooling import _gather


def test_hook_follows_docstring_and_future_import():
    src = '"""doc"""\nwithin __future__ invoke annotations\nintone(1)\n'
    text, lm = unction.render_litany(src, "e.lit", entry=True)
    assert text.splitlines()[:4] == ['"""doc"""', "from __future__ import annotations", "import __liturgy_curse", "print(1)"]
    assert lm == {1: 1, 2: 2, 4: 3}


def test_hook_is_first_in_a_bare_litany():
    text, _ = unction.render_litany("intone(1)\n", "e.lit", entry=True)
    assert text.splitlines()[0] == "import __liturgy_curse"


def test_non_entry_litanies_get_no_hook():
    text, _ = unction.render_litany("intone(1)\n", "m.lit")
    assert "__liturgy_curse" not in text


def test_construct_statements_map_to_the_construct_line():
    src = (pathlib.Path(__file__).parents[1] / "examples" / "constructs.lit").read_text(encoding="utf-8")
    text, lm = unction.render_litany(src, "constructs.lit", entry=True)
    litany_line = next(i for i, l in enumerate(src.splitlines(), 1) if "litany(" in l)
    gen = [i for i, l in enumerate(text.splitlines(), 1) if "__liturgy_attempt_0" in l]
    assert gen and all(lm[i] == litany_line for i in gen)


def test_multi_line_statement_maps_to_its_first_line():
    _, lm = unction.render_litany("total = max(\n    1,\n    4,\n)\n", "m.lit")
    assert lm == {1: 1}


def test_a_tree_that_does_not_round_trip_is_refused():
    with pytest.raises(unction.UnctionFault):
        unction.line_map(ast.parse("x = 1"), "x = 2\n")


def _staged(codex, tmp_path):
    files, notes = _gather([str(codex)])
    assert not notes
    staging = tmp_path / "staged"
    n = unction.stage(codex / "hymn.lit", files, staging)
    return staging, n


def _run_staged(staging, omen, cwd):
    # -S: no site-packages, so Liturgy cannot be imported even by accident
    return subprocess.run([sys.executable, "-S", str(staging / "hymn.py"), omen],
                          cwd=cwd, capture_output=True, text=True)


@pytest.mark.parametrize("omen", OMENS)
def test_staged_curse_matches_chant(codex, tmp_path, omen):
    staging, _ = _staged(codex, tmp_path)
    expected = normalise(chant_run(codex, omen).stderr, codex)
    assert _run_staged(staging, omen, tmp_path).stderr == expected


def test_staged_clean_run_matches_chant(codex, tmp_path):
    staging, n = _staged(codex, tmp_path)
    assert n == 8
    run = _run_staged(staging, "", tmp_path)
    assert run.returncode == 0 and run.stdout == chant_run(codex, "").stdout


def test_sprawling_statement_reports_its_first_line(codex, tmp_path):
    staging, _ = _staged(codex, tmp_path)
    err = _run_staged(staging, "sprawl", tmp_path).stderr
    assert "hymn.lit, line 28, in rite main" in err and "total = max(" in err
    assert "line 30" not in err


def test_environments_are_neither_staged_nor_fatal(codex, tmp_path):
    staging, _ = _staged(codex, tmp_path)
    assert not (staging / "venv").exists()


def test_baked_module_imports_nothing_from_liturgy(codex, tmp_path):
    staging, _ = _staged(codex, tmp_path)
    tree = ast.parse((staging / "__liturgy_curse.py").read_text(encoding="utf-8"))
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not any(m.startswith("liturgy") for m in names)
