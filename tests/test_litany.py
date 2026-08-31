import pytest

from liturgy.compiler import compile_litany
from liturgy.constructs import TechHeresy


def run(src, **ns):
    exec(compile_litany(src, "prayer.lit"), ns)
    return ns


def test_a_succeeding_body_runs_once():
    ns = run(
        "calls = []\n"
        "litany(thrice, curse=MotiveFailure):\n"
        "    calls.append(1)\n"
    )
    assert ns["calls"] == [1]


def test_exhausted_attempts_reraise_the_last_curse():
    src = (
        "calls = []\n"
        "litany(thrice, curse=MotiveFailure):\n"
        "    calls.append(1)\n"
        "    proclaim MotiveFailure('again')\n"
    )
    ns = {}
    with pytest.raises(RuntimeError):
        exec(compile_litany(src, "prayer.lit"), ns)
    assert ns["calls"] == [1, 1, 1]


def test_it_stops_as_soon_as_the_body_succeeds():
    src = (
        "calls = []\n"
        "litany(thrice, curse=MotiveFailure):\n"
        "    calls.append(1)\n"
        "    should measure(calls) < 2:\n"
        "        proclaim MotiveFailure('again')\n"
    )
    assert run(src)["calls"] == [1, 1]


def test_an_unnamed_curse_is_not_caught():
    # The whole point of requiring the filter: a TypeError surfaces at once.
    src = (
        "calls = []\n"
        "litany(thrice, curse=MotiveFailure):\n"
        "    calls.append(1)\n"
        "    proclaim PatternMismatch('wrong')\n"
    )
    ns = {}
    with pytest.raises(TypeError):
        exec(compile_litany(src, "prayer.lit"), ns)
    assert ns["calls"] == [1]


def test_a_tuple_of_curses_is_accepted():
    src = (
        "calls = []\n"
        "litany(twice, curse=(MotiveFailure, ImpureOffering)):\n"
        "    calls.append(1)\n"
        "    proclaim ImpureOffering('again')\n"
    )
    ns = {}
    with pytest.raises(ValueError):
        exec(compile_litany(src, "prayer.lit"), ns)
    assert ns["calls"] == [1, 1]


def test_the_count_is_evaluated_exactly_once():
    src = (
        "rolls = []\n"
        "rite roll():\n"
        "    rolls.append(1)\n"
        "    render 2\n"
        "litany(roll(), curse=MotiveFailure):\n"
        "    proclaim MotiveFailure('again')\n"
    )
    ns = {}
    with pytest.raises(RuntimeError):
        exec(compile_litany(src, "prayer.lit"), ns)
    assert ns["rolls"] == [1], "the count expression must be evaluated once"


def test_resting_pauses_between_attempts(monkeypatch):
    import time

    slept = []
    monkeypatch.setattr(time, "sleep", slept.append)
    src = (
        "litany(thrice, resting=0.25, curse=MotiveFailure):\n"
        "    proclaim MotiveFailure('again')\n"
    )
    with pytest.raises(RuntimeError):
        exec(compile_litany(src, "prayer.lit"), {})
    assert slept == [0.25, 0.25], "rests between attempts, not after the last"


def test_omitting_resting_emits_no_timing_code():
    # curse must NOT be MotiveFailure here: it aliases to the builtin
    # RuntimeError, whose own spelling contains "time" and would make this
    # assertion fail regardless of whether any timing code was emitted.
    py_free = compile_litany(
        "litany(twice, curse=ImpureOffering):\n    abide\n", "p.lit"
    )
    assert "time" not in str(py_free.co_consts) + " ".join(py_free.co_names)


def test_cease_in_a_litany_body_is_rejected():
    src = "litany(twice, curse=MotiveFailure):\n    cease\n"
    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    assert "cease" in str(exc.value)


def test_persist_in_a_litany_body_is_rejected():
    src = "litany(twice, curse=MotiveFailure):\n    persist\n"
    with pytest.raises(TechHeresy):
        compile_litany(src, "prayer.lit")


def test_cease_inside_a_real_loop_in_the_body_is_fine():
    src = (
        "seen = []\n"
        "litany(twice, curse=MotiveFailure):\n"
        "    foreach i among span(5):\n"
        "        seen.append(i)\n"
        "        cease\n"
    )
    assert run(src)["seen"] == [0]


def test_render_in_a_litany_body_is_fine():
    src = (
        "rite f():\n"
        "    litany(thrice, curse=MotiveFailure):\n"
        "        render 7\n"
        "    render 0\n"
    )
    assert run(src)["f"]() == 7


def test_a_literal_count_below_one_is_rejected():
    with pytest.raises(TechHeresy) as exc:
        compile_litany("litany(0, curse=MotiveFailure):\n    abide\n", "p.lit")
    assert "at least once" in str(exc.value)


def test_a_computed_count_below_one_is_caught_at_runtime():
    src = "n = 0\nlitany(n, curse=MotiveFailure):\n    abide\n"
    with pytest.raises(ValueError):
        exec(compile_litany(src, "prayer.lit"), {})


def test_curse_passed_positionally_is_rejected():
    with pytest.raises(TechHeresy) as exc:
        compile_litany("litany(twice, MotiveFailure):\n    abide\n", "p.lit")
    assert "keyword" in str(exc.value)


def test_a_missing_curse_is_rejected():
    with pytest.raises(TechHeresy) as exc:
        compile_litany("litany(twice):\n    abide\n", "p.lit")
    assert "curse" in str(exc.value)


def test_a_construct_keyword_after_an_annotation_colon_is_untouched():
    # NAMED REGRESSION. `match` is a legal identifier (a Python soft keyword,
    # never substituted), so `match: ...` is an annotated assignment, not a
    # block. Statement position alone would wrongly fire here.
    ns = run("rite f(litany_count):\n    render litany_count\nmatch: int = 5\n")
    assert ns["match"] == 5


def test_litany_as_a_plain_call_is_untouched():
    # NAMED REGRESSION. Somebody's function, not a construct.
    ns = run("rite litany(n):\n    render n * 2\nresult = litany(3)\n")
    assert ns["result"] == 6
