import ast
import pathlib

import pytest

from liturgy import unction


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
