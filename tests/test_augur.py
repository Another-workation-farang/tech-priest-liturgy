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
