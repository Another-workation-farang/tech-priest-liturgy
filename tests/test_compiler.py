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
