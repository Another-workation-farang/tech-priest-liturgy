import ast

import pytest

from liturgy.compiler import _rewritten_tree

SOURCES = {
    "consecrated": "consecrated PORT = 8080\n",
    "litany": "litany(thrice, resting=1, curse=MotiveFailure):\n    abide\n",
    "augur": "rite f(x):\n    augur:\n        x > 0\n    render x\n",
    "nested": (
        "rite f(x):\n"
        "    augur:\n"
        "        x > 0\n"
        "    litany(twice, curse=MotiveFailure):\n"
        "        consecrated INNER = x\n"
        "        render INNER\n"
    ),
}


@pytest.mark.parametrize("name", sorted(SOURCES))
def test_every_node_in_the_rewritten_tree_has_a_position(name):
    tree = _rewritten_tree(SOURCES[name], "prayer.lit")
    missing = [
        f"{type(n).__name__}"
        for n in ast.walk(tree)
        if isinstance(n, (ast.stmt, ast.expr))
        and getattr(n, "lineno", None) is None
    ]
    assert not missing, f"nodes without a position: {missing}"


@pytest.mark.parametrize("name", sorted(SOURCES))
def test_no_synthesised_node_claims_a_line_beyond_the_source(name):
    src = SOURCES[name]
    limit = src.count("\n")
    tree = _rewritten_tree(src, "prayer.lit")
    beyond = [
        (type(n).__name__, n.lineno)
        for n in ast.walk(tree)
        if isinstance(n, (ast.stmt, ast.expr))
        and getattr(n, "lineno", 0) > limit
    ]
    assert not beyond, f"nodes past the end of the source: {beyond}"
