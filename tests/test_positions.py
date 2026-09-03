import ast

import pytest

from liturgy.compiler import _PASSES, _rewritten_tree
from liturgy.rewrite import ConstructPass
from liturgy.transform import split_lines, transform

SOURCES = {
    # T7: the leading comment is load-bearing. Without it the construct sat
    # on line 1, where `fix_missing_locations`' own default for a node with
    # no position is also 1 -- so a dropped `copy_location` produced exactly
    # the expected line by coincidence and the fixture proved nothing.
    "consecrated": (
        "# a comment, so the construct is not on line 1\n"
        "consecrated PORT = 8080\n"
    ),
    "litany": "litany(thrice, resting=1, curse=MotiveFailure):\n    abide\n",
    "augur": "rite f(x):\n    augur:\n        x > 0\n    render x\n",
    # The `consecrated` sits beside the litany rather than inside it: a
    # declaration in a litany body would rebind on every attempt, and is
    # rejected (see test_litany.py).
    "nested": (
        "rite f(x):\n"
        "    augur:\n"
        "        x > 0\n"
        "    consecrated INNER = x\n"
        "    litany(twice, curse=MotiveFailure):\n"
        "        render INNER\n"
    ),
}


def _tree_before_fixup(src: str, filename: str = "prayer.lit") -> ast.AST:
    """The construct-rewritten tree with NO `ast.fix_missing_locations` pass.

    `_rewritten_tree` calls that fixup, which walks top-down and copies a
    location onto any node missing one from its nearest located ancestor.
    That is exactly what makes a dropped `copy_location` invisible: the node
    ends up with *a* line, just the wrong one (the parent's), so neither "is
    it None" nor "is it beyond the source" can catch it. Building the tree
    by hand here, stopping short of the fixup, is what makes a missing
    `copy_location` actually observable.
    """
    out = transform(src, _PASSES, filename=filename)
    py, smap, facts = out.python, out.source_map, out.facts
    tree = ast.parse(py, filename, "exec")
    return ConstructPass(
        filename, split_lines(src), smap, split_lines(py), facts
    ).visit(tree)


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


# --- The real backstop: assert positions BEFORE fix_missing_locations runs --
#
# The two tests above run on the post-fixup tree, so they cannot tell a
# genuine `copy_location` from one `fix_missing_locations` faked by copying
# from a parent. They stay because the post-fixup invariant is still worth
# guarding cheaply, but the tests below are what actually catch a dropped
# `copy_location`.


@pytest.mark.parametrize("name", sorted(SOURCES))
def test_no_node_lacks_a_position_before_fixup(name):
    tree = _tree_before_fixup(SOURCES[name])
    missing = [
        f"{type(n).__name__}"
        for n in ast.walk(tree)
        if isinstance(n, (ast.stmt, ast.expr))
        and getattr(n, "lineno", None) is None
    ]
    assert not missing, (
        f"nodes without a position before fix_missing_locations: {missing} "
        "-- a copy_location call is missing in the construct that produced "
        "this node"
    )


# --- Stronger still: the synthesised nodes must carry the HEADER's line ----
#
# A copy_location call that fires but points at the wrong node is invisible
# to "does it have a position" -- it still has one, just not the right one.
# These pin each construct's synthesised nodes to the exact source line of
# the construct's own header (the `augur:`/`litany(...):` line, or the
# `consecrated` statement), computed by hand from the fixtures above.


def _is_augur_raise_if(n: ast.AST) -> bool:
    """The `if not (test): raise ValueError(...)` an augury check compiles to."""
    return (
        isinstance(n, ast.If)
        and isinstance(n.test, ast.UnaryOp)
        and isinstance(n.test.op, ast.Not)
        and len(n.body) == 1
        and isinstance(n.body[0], ast.Raise)
        and isinstance(n.body[0].exc, ast.Call)
        and isinstance(n.body[0].exc.func, ast.Name)
        and n.body[0].exc.func.id == "ValueError"
    )


AUGUR_HEADER_LINE = {"augur": 2, "nested": 2}


@pytest.mark.parametrize("name", sorted(AUGUR_HEADER_LINE))
def test_augur_check_carries_the_augur_header_line(name):
    tree = _tree_before_fixup(SOURCES[name])
    checks = [n for n in ast.walk(tree) if _is_augur_raise_if(n)]
    assert checks, "expected at least one synthesised augur check"
    expected = AUGUR_HEADER_LINE[name]
    for n in checks:
        assert n.lineno == expected, f"If at line {n.lineno}, expected {expected}"
        assert n.test.lineno == expected
        assert n.body[0].lineno == expected


def _is_litany_bind(n: ast.AST) -> bool:
    """The `__liturgy_n_<suffix> = <count>` bind at the top of a retry."""
    return (
        isinstance(n, ast.Assign)
        and len(n.targets) == 1
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id.startswith("__liturgy_n_")
    )


LITANY_HEADER_LINE = {"litany": 1, "nested": 5}


@pytest.mark.parametrize("name", sorted(LITANY_HEADER_LINE))
def test_litany_retry_scaffold_carries_the_litany_header_line(name):
    tree = _tree_before_fixup(SOURCES[name])
    binds = [n for n in ast.walk(tree) if _is_litany_bind(n)]
    assert binds, "expected at least one synthesised litany retry bind"
    expected = LITANY_HEADER_LINE[name]
    for n in binds:
        assert n.lineno == expected, f"Assign at line {n.lineno}, expected {expected}"


CONSECRATED_HEADER_LINE = {
    "consecrated": (2, "PORT"),
    "nested": (4, "INNER"),
}


@pytest.mark.parametrize("name", sorted(CONSECRATED_HEADER_LINE))
def test_consecrated_assign_carries_the_consecrated_header_line(name):
    expected_line, target_name = CONSECRATED_HEADER_LINE[name]
    tree = _tree_before_fixup(SOURCES[name])
    assigns = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Assign)
        and len(n.targets) == 1
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == target_name
    ]
    assert assigns, f"expected a plain assign to {target_name}"
    for n in assigns:
        assert n.lineno == expected_line, (
            f"Assign at line {n.lineno}, expected {expected_line}"
        )
