import ast

import pytest

from liturgy.compiler import compile_litany
from liturgy.transform import UnfinishedLitany


def test_compiles_liturgy_to_a_working_code_object():
    code = compile_litany('intone("ave")\n', "<test>")
    ns = {}
    exec(code, ns)


def test_result_carries_the_filename():
    code = compile_litany("x = 1\n", "prayer.lit")
    assert code.co_filename == "prayer.lit"


def test_single_mode_supports_the_repl():
    code = compile_litany("1 + 1\n", "<commune>", mode="single")
    exec(code, {})


def test_unfinished_input_still_raises_unfinished_litany():
    with pytest.raises(UnfinishedLitany):
        compile_litany("x = (1, 2\n", "prayer.lit")


def test_syntax_errors_carry_the_filename():
    with pytest.raises(SyntaxError) as exc:
        compile_litany("rite f(:\n", "prayer.lit")
    assert exc.value.filename == "prayer.lit"


def test_line_numbers_are_liturgy_line_numbers():
    code = compile_litany("x = 1\ny = 2\nproclaim MachineCurse('here')\n", "p.lit")
    try:
        exec(code, {})
    except Exception:
        import sys, traceback

        assert traceback.extract_tb(sys.exc_info()[2])[-1].lineno == 3


# --- M12: no carrier name may survive the construct pass --------------------
#
# The carriers are the private names the token pass invents so a construct
# header parses. Every one of them must be consumed by `ConstructPass`. One
# left behind is not cosmetic: `PORT: __consecrated__ = 8080` is a live
# annotation, and at module scope on Python 3.12/3.13 -- where PEP 649 has
# not yet made annotations lazy -- evaluating it raises
# `NameError: __consecrated__` and the module dies. This is the check that
# catches C1 (a `consecrated` in a `curse` or `wherein` block, never
# desugared) the moment it reappears, on any interpreter.

CARRIERS = {"__consecrated__", "__litany__", "__augur__"}

CARRIER_SOURCES = {
    "module": "consecrated PORT = 8080\n",
    "rite": "rite f():\n    consecrated PORT = 1\n    render PORT\n",
    "pattern": "pattern C:\n    consecrated PORT = 1\n",
    "curse-block": (
        "attempt:\n    abide\ncurse MachineCurse:\n    consecrated PORT = 1\n"
    ),
    "regardless-block": (
        "attempt:\n    abide\nregardless:\n    consecrated PORT = 1\n"
    ),
    "wherein-block": "discern 1:\n    wherein 1:\n        consecrated PORT = 1\n",
    "should-block": "should Sanctioned:\n    consecrated PORT = 1\n",
    "anointed-block": (
        "anointed unseal('/dev/null') styled fh:\n    consecrated PORT = 1\n"
    ),
    "litany": "litany(thrice, curse=MotiveFailure):\n    abide\n",
    "augur": "rite f(x):\n    augur:\n        x > 0\n    render x\n",
    "all-three": (
        "consecrated LIMIT = 2\n"
        "rite f(x):\n"
        "    augur:\n"
        "        x > 0\n"
        "    litany(LIMIT, curse=MotiveFailure):\n"
        "        render x\n"
    ),
}


@pytest.mark.parametrize("name", sorted(CARRIER_SOURCES))
def test_no_carrier_name_survives_into_the_rewritten_tree(name):
    from liturgy.compiler import _rewritten_tree

    tree = _rewritten_tree(CARRIER_SOURCES[name], "prayer.lit")
    left = sorted(
        {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in CARRIERS}
    )
    assert not left, f"carrier names survived ConstructPass: {left}"


# mode="single" accepts exactly one statement, so the multi-statement
# fixture above cannot be compiled that way. Everything else can.
SINGLE_MODE_SOURCES = sorted(set(CARRIER_SOURCES) - {"all-three"})


@pytest.mark.parametrize("name", SINGLE_MODE_SOURCES)
def test_no_carrier_name_survives_in_single_mode_either(name):
    # `commune` compiles with mode="single", which parses to `Interactive`
    # rather than `Module`. `ConstructPass` had no visitor for it, so the
    # prompt got no scope visit at all and every consecrated carrier
    # survived.
    from liturgy.compiler import _rewritten_tree

    tree = _rewritten_tree(CARRIER_SOURCES[name], "<commune>", mode="single")
    left = sorted(
        {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in CARRIERS}
    )
    assert not left, f"carrier names survived ConstructPass: {left}"


# --- I5: the compiler fills in the filename a token pass cannot know --------


@pytest.mark.parametrize(
    "src",
    [
        "consecrated = 5\n",
        "litany 3:\n    abide\n",
        "augur x:\n    abide\n",
    ],
    ids=["consecrated", "litany", "augur"],
)
def test_a_carrier_heresy_carries_the_real_filename(src):
    from liturgy.constructs import TechHeresy

    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    assert exc.value.filename == "prayer.lit"


def test_a_filename_the_carrier_pass_did_set_is_not_overwritten():
    # Only the "<unknown>" placeholder is replaced. A heresy that already
    # names a file -- as everything raised from `ConstructPass` does -- keeps
    # what it was given.
    from liturgy.constructs import TechHeresy
    from liturgy.compiler import _rewritten_tree

    with pytest.raises(TechHeresy) as exc:
        _rewritten_tree("litany(0, curse=MachineCurse):\n    abide\n", "p.lit")
    assert exc.value.filename == "p.lit"
