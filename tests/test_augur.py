import pytest

from liturgy.compiler import compile_litany
from liturgy.constructs import TechHeresy


def run(src, **ns):
    exec(compile_litany(src, "prayer.lit"), ns)
    return ns


DIVIDE = (
    "rite divide(a, b):\n"
    "    augur:\n"
    "        b be nay Void\n"
    "        b != 0\n"
    "    render a / b\n"
)


def test_a_satisfied_augury_lets_the_rite_run():
    assert run(DIVIDE)["divide"](6, 2) == 3


def test_a_failed_augury_raises_impure_offering():
    with pytest.raises(ValueError):
        run(DIVIDE)["divide"](1, 0)


def test_the_message_quotes_the_liturgy_source_not_the_python():
    with pytest.raises(ValueError) as exc:
        run(DIVIDE)["divide"](1, None)
    assert "b be nay Void" in str(exc.value)
    assert "is not None" not in str(exc.value)


def test_the_first_failing_condition_is_the_one_reported():
    with pytest.raises(ValueError) as exc:
        run(DIVIDE)["divide"](1, 0)
    assert "b != 0" in str(exc.value)


def test_it_survives_optimisation():
    # A contract, not an assertion: it must not compile away under -O.
    code = compile_litany(DIVIDE, "prayer.lit", optimize=2)
    ns = {}
    exec(code, ns)
    with pytest.raises(ValueError):
        ns["divide"](1, 0)


def test_an_augury_may_follow_a_docstring():
    src = (
        "rite f(x):\n"
        '    """Divide the thing."""\n'
        "    augur:\n"
        "        x > 0\n"
        "    render x\n"
    )
    assert run(src)["f"](2) == 2
    with pytest.raises(ValueError):
        run(src)["f"](0)


def test_an_augury_outside_a_rite_is_rejected():
    with pytest.raises(TechHeresy) as exc:
        compile_litany("augur:\n    Sanctioned\n", "prayer.lit")
    assert "rite" in str(exc.value)


def test_an_augury_after_real_statements_is_rejected():
    src = "rite f(x):\n    y = x\n    augur:\n        x > 0\n    render y\n"
    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    assert "opening" in str(exc.value)


def test_a_statement_inside_an_augury_is_rejected():
    src = "rite f(x):\n    augur:\n        y = 1\n    render x\n"
    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    assert "condition" in str(exc.value)


def test_a_nested_rite_may_have_its_own_augury():
    src = (
        "rite outer(x):\n"
        "    augur:\n"
        "        x > 0\n"
        "    rite inner(y):\n"
        "        augur:\n"
        "            y > 0\n"
        "        render y\n"
        "    render inner(x)\n"
    )
    assert run(src)["outer"](3) == 3
    with pytest.raises(ValueError):
        run(src)["outer"](0)


def test_augur_as_a_plain_call_is_untouched():
    # NAMED REGRESSION. Somebody's function, not a construct.
    ns = run("rite augur(n):\n    render n + 1\nresult = augur(1)\n")
    assert ns["result"] == 2


def test_the_traceback_points_at_the_augur_line():
    import traceback

    ns = run(DIVIDE)
    try:
        ns["divide"](1, 0)
    except ValueError:
        import sys

        frames = traceback.extract_tb(sys.exc_info()[2])
    # The synthesised raise carries the augur header's location (line 2).
    assert frames[-1].lineno == 2


# -- _liturgy_source: multi-line conditions and non-ASCII columns --------


def test_a_condition_spanning_two_lines_is_quoted_in_full():
    src = (
        "rite f(a, b):\n"
        "    augur:\n"
        "        (a > 0\n"
        "         and b > 0)\n"
        "    render a\n"
    )
    with pytest.raises(ValueError) as exc:
        run(src)["f"](-1, -1)
    assert str(exc.value) == "the omens forbid it -- a > 0 and b > 0"


def test_a_condition_spanning_three_lines_is_quoted_in_full():
    src = (
        "rite f(a, b, c):\n"
        "    augur:\n"
        "        (a > 0\n"
        "         and b > 0\n"
        "         and c > 0)\n"
        "    render a\n"
    )
    with pytest.raises(ValueError) as exc:
        run(src)["f"](-1, -1, -1)
    assert (
        str(exc.value) == "the omens forbid it -- a > 0 and b > 0 and c > 0"
    )


def test_a_non_ascii_condition_is_quoted_exactly():
    src = (
        "rite f(s):\n"
        "    augur:\n"
        '        s != "→"\n'
        "    render s\n"
    )
    with pytest.raises(ValueError) as exc:
        run(src)["f"]("→")
    assert str(exc.value) == 'the omens forbid it -- s != "→"'


def test_two_conditions_one_line_first_has_a_multibyte_character():
    # The first condition contains a multi-byte character; a naive
    # byte-offset slice into the (character-indexed) source line would
    # skew every column after it, corrupting the second condition's
    # message. Check both directions: whichever condition fails, its own
    # message must be exact, not bleeding into or truncating its neighbour.
    src = (
        "rite f(a, b):\n"
        "    augur:\n"
        '        a != "→"; b == 1\n'
        "    render a\n"
    )
    with pytest.raises(ValueError) as exc:
        run(src)["f"]("→", 1)
    assert str(exc.value) == 'the omens forbid it -- a != "→"'

    with pytest.raises(ValueError) as exc:
        run(src)["f"]("x", 0)
    assert str(exc.value) == "the omens forbid it -- b == 1"


def test_a_condition_both_multiline_and_non_ascii():
    src = (
        "rite f(a, b):\n"
        "    augur:\n"
        '        (a != "→"\n'
        "         and b > 0)\n"
        "    render a\n"
    )
    with pytest.raises(ValueError) as exc:
        run(src)["f"]("→", 1)
    assert str(exc.value) == 'the omens forbid it -- a != "→" and b > 0'


def test_the_unparse_fallback_triggers_when_the_slice_cannot_work():
    # _liturgy_source wraps its slicing in try/except and falls back to
    # ast.unparse(node) on any failure. Feeding it a node whose lineno
    # points past the end of the known source lines forces an IndexError
    # on the very first `self.py_lines[lineno - 1]` lookup -- before the
    # SourceMap is ever consulted -- which is what makes the fallback
    # trigger here.
    import ast

    from liturgy.rewrite import ConstructPass
    from liturgy.sourcemap import SourceMap

    smap = SourceMap()
    smap.freeze()
    lines = ["line one\n"]
    cp = ConstructPass("prayer.lit", lines, smap, lines)
    node = ast.parse("x > 0", mode="eval").body
    node.lineno = 99
    node.end_lineno = 99
    assert cp._liturgy_source(node) == "x > 0"
