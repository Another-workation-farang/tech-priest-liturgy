"""Spec IV: the declaration of archetypes.

Every rite must declare an archetype for each of its parameters and for
what it renders; every consecrated name must declare one too. This is
**presence, not correctness** -- nothing here checks that an annotation is
true, and `rite f(x: str) -> str: render 1` compiles happily. Liturgy has
no runtime and no type checker, and a test asserting otherwise would be
asserting a promise the language does not make.

The rule lives in `rewrite.ConstructPass`, on the compile path, so `chant`,
`augur` and `prove` cannot disagree about it.
"""

import ast
import io

import pytest

from liturgy.commune import LiturgyConsole
from liturgy.compiler import _PASSES, compile_litany
from liturgy.constructs import TechHeresy
from liturgy.rewrite import ConstructPass
from liturgy.transform import split_lines, transform

PARAM = "every parameter must declare its archetype"
RENDERS = "a rite must declare what it renders"
SEAL = "a consecrated name must declare its archetype"


def run(src):
    ns = {}
    exec(compile_litany(src, "prayer.lit"), ns)
    return ns


def refuse(src):
    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    return exc.value


# --- what is required ------------------------------------------------------


def test_an_unannotated_parameter_is_refused():
    err = refuse("rite greet(name):\n    render name\n")
    assert str(err.msg) == f"name is unsanctioned; {PARAM}"
    assert err.lineno == 1
    assert err.filename == "prayer.lit"


def test_a_missing_return_archetype_is_refused():
    err = refuse("rite greet(name: str):\n    render name\n")
    assert str(err.msg) == f"greet is unsanctioned; {RENDERS}"


def test_a_bare_consecrated_binding_is_refused():
    err = refuse("consecrated PORT = 8080\n")
    assert str(err.msg) == f"PORT is unsanctioned; {SEAL}"


def test_a_fully_declared_rite_is_accepted():
    ns = run("rite greet(name: str) -> str:\n    render f'ave, {name}'\n")
    assert ns["greet"]("Magos") == "ave, Magos"


def test_a_declared_consecrated_binding_is_accepted():
    assert run("consecrated PORT: int = 8080\n")["PORT"] == 8080


def test_the_parameter_is_reported_before_the_return():
    # Reading order. A rite missing both gets the first fault a reader's
    # eye lands on, not the last.
    err = refuse("rite greet(name):\n    render name\n")
    assert PARAM in str(err.msg)


def test_the_second_parameter_is_reported_when_the_first_is_declared():
    err = refuse("rite f(a: int, b) -> int:\n    render a\n")
    assert str(err.msg) == f"b is unsanctioned; {PARAM}"


def test_presence_is_not_correctness():
    # The archetypes here are all lies and every one of them compiles.
    # Liturgy cannot check them and this test records that it does not try.
    ns = run("rite f(n: str) -> str:\n    render n + 1\n")
    assert ns["f"](1) == 2


# --- every parameter kind --------------------------------------------------


@pytest.mark.parametrize(
    "header,offender",
    [
        ("rite f(a, /) -> Void:", "a"),
        ("rite f(a: int, b, /) -> Void:", "b"),
        ("rite f(a) -> Void:", "a"),
        ("rite f(*, a) -> Void:", "a"),
        ("rite f(*args) -> Void:", "args"),
        ("rite f(**kwargs) -> Void:", "kwargs"),
        ("rite f(a: int, *args) -> Void:", "args"),
        ("rite f(*args: int, **kwargs) -> Void:", "kwargs"),
        ("rite f(a: int, /, b: int, *c, d: int, **e) -> Void:", "c"),
    ],
    ids=[
        "posonly", "posonly-second", "plain", "kwonly", "vararg", "kwarg",
        "vararg-after-plain", "kwarg-after-vararg", "every-kind-at-once",
    ],
)
def test_no_parameter_kind_escapes_the_rule(header, offender):
    # `*args`/`**kwargs` are annotatable in Python, so they are not exempt;
    # positional-only and keyword-only parameters are ordinary parameters.
    err = refuse(f"{header}\n    abide\n")
    assert str(err.msg) == f"{offender} is unsanctioned; {PARAM}"


def test_every_parameter_kind_declared_is_accepted():
    src = (
        "rite f(a: int, /, b: int, *c: int, d: int = 1, **e: int) -> tuple:\n"
        "    render (a, b, c, d, e)\n"
    )
    assert run(src)["f"](1, 2, 3, d=4, x=5) == (1, 2, (3,), 4, {"x": 5})


def test_a_rite_with_no_parameters_still_needs_a_return_archetype():
    err = refuse("rite f():\n    abide\n")
    assert str(err.msg) == f"f is unsanctioned; {RENDERS}"


# --- exempt by construction ------------------------------------------------


@pytest.mark.parametrize("receiver", ["self", "cls"])
def test_the_first_parameter_may_be_self_or_cls(receiver):
    src = (
        "pattern Cog:\n"
        f"    rite tick({receiver}, n: int) -> int:\n"
        "        render n\n"
    )
    assert run(src)["Cog"].tick.__name__ == "tick"


@pytest.mark.parametrize("receiver", ["self", "cls"])
def test_self_or_cls_is_exempt_only_in_the_first_slot(receiver):
    # A later parameter wearing the name is an ordinary parameter. Every
    # type checker's `--disallow-untyped-defs` draws the line here too.
    err = refuse(f"rite f(a: int, {receiver}) -> Void:\n    abide\n")
    assert str(err.msg) == f"{receiver} is unsanctioned; {PARAM}"


def test_a_vararg_named_self_is_not_the_receiver():
    err = refuse("rite f(*self) -> Void:\n    abide\n")
    assert str(err.msg) == f"self is unsanctioned; {PARAM}"


def test_a_receiver_outside_a_pattern_is_exempt_too():
    # The rule is positional, not contextual: nothing in the AST says
    # whether a rite will be bound as a method, and guessing would reject
    # a receiver assigned onto a pattern after the fact.
    assert run("rite tick(self) -> Void:\n    abide\n")["tick"](None) is None


def test_a_servitor_is_exempt_entirely():
    # Python has no syntax for annotating a lambda's parameters --
    # `servitor x: int = 1` is a syntax error -- so a rule requiring it
    # would forbid the construct outright.
    assert run("f = servitor x: x + 1\nresult = f(1)\n")["result"] == 2


def test_a_servitor_inside_a_declared_rite_is_exempt_too():
    src = (
        "rite outer(n: int) -> int:\n"
        "    inner = servitor x: x * n\n"
        "    render inner(2)\n"
    )
    assert run(src)["outer"](3) == 6


def test_a_plain_assignment_is_not_touched():
    # Idiomatic Python does not annotate these, and enforcing them would
    # make the language unusable rather than strict.
    ns = run("x = 1\nfor_each = [i foreach i among span(2)]\n")
    assert ns["x"] == 1 and ns["for_each"] == [0, 1]


def test_the_prompt_does_not_enforce():
    # `commune` compiles with mode="single": every entry is its own unit,
    # so there is nowhere to put an `unsanctioned` that is still in force
    # on the next line, and a prompt refusing `rite f(x):` is unusable.
    console = LiturgyConsole()
    assert console.runsource("rite f(x):") is True
    assert console.runsource("rite f(x):\n    render x\n") is False
    assert console.locals["f"](3) == 3


def test_the_prompt_does_not_enforce_consecrated_either():
    console = LiturgyConsole()
    assert console.runsource("consecrated PORT = 8080\n") is False
    assert console.locals["PORT"] == 8080


# --- exempt by declaration -------------------------------------------------


def test_unsanctioned_exempts_one_rite():
    src = "unsanctioned rite legacy(x):\n    render x\n"
    assert run(src)["legacy"](4) == 4


def test_unsanctioned_exempts_one_consecrated_binding():
    assert run("unsanctioned consecrated PORT = 8080\n")["PORT"] == 8080


def test_unsanctioned_exempts_the_rite_it_marks_and_no_other():
    src = (
        "unsanctioned rite legacy(x):\n"
        "    render x\n"
        "rite modern(x):\n"
        "    render x\n"
    )
    err = refuse(src)
    assert str(err.msg) == f"x is unsanctioned; {PARAM}"
    assert err.lineno == 3


def test_unsanctioned_is_per_statement_not_per_row():
    # Two bindings on one row: the modifier marks the first only. Row alone
    # would exempt both, which is why `Exemption` carries a column.
    err = refuse("unsanctioned consecrated A = 1; consecrated B = 2\n")
    assert str(err.msg) == f"B is unsanctioned; {SEAL}"
    assert err.lineno == 1


def test_a_bare_unsanctioned_exempts_the_whole_litany():
    src = (
        "unsanctioned\n"
        "\n"
        "consecrated PORT = 8080\n"
        "rite one(a):\n"
        "    render a\n"
        "rite two(b):\n"
        "    render b\n"
        "pattern Cog:\n"
        "    rite tick(self, n):\n"
        "        render n\n"
    )
    ns = run(src)
    assert ns["one"](1) == 1 and ns["two"](2) == 2 and ns["PORT"] == 8080


def test_an_exempt_rite_may_still_declare_archetypes():
    # The modifier lifts the requirement; it does not forbid the thing.
    src = "unsanctioned rite legacy(x: int) -> int:\n    render x\n"
    assert run(src)["legacy"](4) == 4


# --- inheritance: an exempt rite exempts what is nested inside it ----------


def test_exemption_is_inherited_by_a_nested_rite():
    # THE RULING, and the docstring on `ConstructPass._scope` records it: a
    # reader who exempted the outer rite did not mean to be nagged about a
    # closure three lines inside it.
    src = (
        "unsanctioned rite outer(x):\n"
        "    rite inner(y):\n"
        "        render y + 1\n"
        "    render inner(x)\n"
    )
    assert run(src)["outer"](1) == 2


def test_exemption_is_inherited_two_scopes_deep():
    src = (
        "unsanctioned rite outer(x):\n"
        "    pattern Cog:\n"
        "        rite tick(self, n):\n"
        "            render n\n"
        "    render Cog().tick(x)\n"
    )
    assert run(src)["outer"](5) == 5


def test_a_consecrated_inside_an_exempt_rite_is_exempt_too():
    src = (
        "unsanctioned rite outer(x):\n"
        "    consecrated INNER = x\n"
        "    render INNER\n"
    )
    assert run(src)["outer"](7) == 7


def test_exemption_does_not_leak_to_a_sibling_rite():
    src = (
        "unsanctioned rite outer(x):\n"
        "    render x\n"
        "rite sibling(y):\n"
        "    render y\n"
    )
    assert refuse(src).lineno == 3


def test_exemption_does_not_leak_out_of_the_rite_that_holds_it():
    # `_scope` restores the flag on the way back up, so a statement after
    # the exempt rite is judged normally even at the same nesting.
    src = (
        "rite outer(x: int) -> int:\n"
        "    unsanctioned rite exempt(a):\n"
        "        render a\n"
        "    rite strict(b):\n"
        "        render b\n"
        "    render x\n"
    )
    err = refuse(src)
    assert str(err.msg) == f"b is unsanctioned; {PARAM}"
    assert err.lineno == 4


def test_a_nested_rite_in_a_declared_rite_is_not_exempt():
    src = (
        "rite outer(x: int) -> int:\n"
        "    rite inner(y):\n"
        "        render y\n"
        "    render inner(x)\n"
    )
    assert refuse(src).lineno == 2


# --- every shape a rite comes in -------------------------------------------


def test_a_remote_rite_is_covered_identically():
    err = refuse("remote rite go(x):\n    render x\n")
    assert str(err.msg) == f"x is unsanctioned; {PARAM}"


def test_a_remote_rite_missing_only_its_return_is_covered():
    err = refuse("remote rite go(x: int):\n    render x\n")
    assert str(err.msg) == f"go is unsanctioned; {RENDERS}"


def test_a_declared_remote_rite_is_accepted():
    ns = run("remote rite go(x: int) -> int:\n    render x\n")
    assert ns["go"].__name__ == "go"


def test_unsanctioned_exempts_a_remote_rite():
    # The modifier's recorded column is that of `remote`, not of `rite`.
    ns = run("unsanctioned remote rite go(x):\n    render x\n")
    assert ns["go"].__name__ == "go"


def test_a_patterns_methods_are_rites_and_are_covered():
    err = refuse("pattern Cog:\n    rite tick(self, n):\n        render n\n")
    assert str(err.msg) == f"n is unsanctioned; {PARAM}"
    assert err.lineno == 2


def test_a_decorated_rite_is_covered():
    src = (
        "invoke functools\n"
        "@functools.cache\n"
        "rite f(n):\n"
        "    render n\n"
    )
    err = refuse(src)
    assert err.lineno == 3


def test_a_rite_inside_a_block_is_covered():
    err = refuse("should Sanctioned:\n    rite f(n):\n        render n\n")
    assert err.lineno == 2


def test_a_consecrated_inside_a_block_is_covered():
    err = refuse("should Sanctioned:\n    consecrated PORT = 1\n")
    assert str(err.msg) == f"PORT is unsanctioned; {SEAL}"
    assert err.lineno == 2


# --- the rule does not displace the older ones -----------------------------


def test_a_loop_consecration_is_still_a_loop_fault():
    # The archetype rule runs last, so a scope that is wrong in an older
    # way is still reported that way.
    src = "foreach i among span(3):\n    consecrated X = i\n"
    with pytest.raises(TechHeresy, match="loop"):
        compile_litany(src, "prayer.lit")


def test_a_rebinding_is_still_a_rebinding_fault():
    src = "consecrated PORT: int = 1\nPORT = 2\n"
    with pytest.raises(TechHeresy, match="may not be rebound"):
        compile_litany(src, "prayer.lit")


def test_an_exempt_rite_still_gets_the_augury_rule():
    src = (
        "unsanctioned rite f(x):\n"
        "    y = x\n"
        "    augur:\n"
        "        x > 0\n"
        "    render y\n"
    )
    with pytest.raises(TechHeresy, match="opening"):
        compile_litany(src, "prayer.lit")


# --- where the caret lands -------------------------------------------------


def _offsets(src, filename="prayer.lit"):
    """The heresy's (offset, end_offset) mapped back to Liturgy columns."""
    err = refuse(src)
    out = transform(src, _PASSES, filename=filename)
    start = out.source_map.to_lit(err.lineno, err.offset - 1)
    end = out.source_map.to_lit(err.lineno, err.end_offset - 1)
    return start, end


def test_the_caret_underlines_the_offending_parameter():
    line = "rite greet(name):"
    assert _offsets(f"{line}\n    render name\n") == (
        line.index("name"), line.index("name") + len("name")
    )


def test_the_caret_underlines_the_rites_own_name():
    line = "rite greet(name: str):"
    assert _offsets(f"{line}\n    render name\n") == (
        line.index("greet"), line.index("greet") + len("greet")
    )


def test_the_caret_finds_a_rite_whose_name_hides_inside_def():
    # `rite f(f):` generates `def f(f):`, whose first `f` is the one in
    # `def`. Searching the line for the name would underline that.
    line = "rite f(f: int):"
    assert _offsets(f"{line}\n    render f\n") == (
        line.index("f("), line.index("f(") + 1
    )


def test_the_caret_underlines_a_remote_rites_name():
    line = "remote rite go(x: int):"
    assert _offsets(f"{line}\n    render x\n") == (
        line.index("go"), line.index("go") + len("go")
    )


def test_the_caret_underlines_the_consecrated_name():
    line = "consecrated PORT = 8080"
    assert _offsets(f"{line}\n") == (
        line.index("PORT"), line.index("PORT") + len("PORT")
    )


def test_the_caret_counts_characters_not_bytes():
    # `ast` hands over UTF-8 byte offsets; every column downstream counts
    # characters. A multi-byte character earlier on the line would slide
    # the caret right by its extra bytes.
    # Keyword-only, so an undefaulted parameter may follow a defaulted one.
    line = 'rite f(*, a: str = "✠✠✠✠✠", b) -> Void:'
    assert _offsets(f"{line}\n    abide\n") == (
        line.index(", b") + 2, line.index(", b") + 3
    )


def test_the_rendered_curse_shows_the_liturgy_line_and_the_caret(tmp_path):
    import os
    import subprocess
    import sys

    script = tmp_path / "prayer.lit"
    script.write_text("rite greet(name):\n    render name\n")
    proc = subprocess.run(
        [sys.executable, "-m", "liturgy", "chant", str(script)],
        capture_output=True, text=True,
        env={**os.environ, "XDG_STATE_HOME": str(tmp_path)},
    )
    rendered = proc.stdout + proc.stderr
    assert proc.returncode != 0
    # The Liturgy line, not the generated Python, and four carets under the
    # parameter -- which stands at column 11 of a line indented by none.
    assert "\n       rite greet(name):\n" in rendered
    assert "\n" + " " * (7 + 11) + "^" * 4 + "\n" in rendered
    assert f"TechHeresy: name is unsanctioned; {PARAM}" in rendered


# --- the rule is on the compile path, so every verb sees it ----------------


def test_augur_reports_an_unannotated_rite(tmp_path):
    from liturgy.tooling import augur

    p = tmp_path / "legacy.lit"
    p.write_text("rite f(x):\n    render x\n")
    buf = io.StringIO()
    assert augur([str(p)], out=buf) == 1
    assert PARAM in buf.getvalue()


def test_augur_passes_a_declared_litany(tmp_path):
    from liturgy.tooling import augur

    p = tmp_path / "ok.lit"
    p.write_text("rite f(x: int) -> int:\n    render x\n")
    buf = io.StringIO()
    assert augur([str(p)], out=buf) == 0


# --- the facts the rule reads ----------------------------------------------


def test_the_rule_reads_the_exemption_column_not_the_row():
    # Guards the coupling between `transform.Exemption` and
    # `ConstructPass._lit_col`: if either moves, an `unsanctioned` in an
    # indented block stops matching and the modifier silently does nothing.
    src = (
        "pattern Cog:\n"
        "    unsanctioned rite tick(self, n):\n"
        "        render n\n"
    )
    assert run(src)["Cog"]().tick(3) == 3


def test_the_pass_can_be_driven_directly_with_hand_made_facts():
    # The rule is a property of `ConstructPass`, not of the CLI: given
    # facts that say the file is unsanctioned, the same tree compiles.
    src = "rite f(x):\n    render x\n"
    out = transform(src, _PASSES, filename="prayer.lit")
    tree = ast.parse(out.python, "prayer.lit", "exec")
    facts = type(out.facts)(unsanctioned_file=True)
    ConstructPass(
        "prayer.lit", split_lines(src), out.source_map,
        split_lines(out.python), facts,
    ).visit(tree)


# --- the one caller allowed to compile without the rule --------------------


def test_sanction_false_suppresses_the_archetype_rule():
    # `transcribe`'s backstop, and nothing that chants a litany. A rule
    # `chant` enforced and `augur` did not would be the one disagreement
    # Spec II forbids, so this is a keyword on the compiler and never a
    # flag on a verb that runs code.
    src = "rite f(x):\n    render x\n"
    refuse(src)
    ns = {}
    exec(compile_litany(src, "prayer.lit", sanction=False), ns)
    assert ns["f"](3) == 3


def test_sanction_false_suppresses_the_seal_rule_too():
    ns = {}
    exec(compile_litany("consecrated PORT = 1\n", "p.lit", sanction=False), ns)
    assert ns["PORT"] == 1


@pytest.mark.parametrize(
    "src,fault",
    [
        ("consecrated PORT: int = 1\nPORT = 2\n", "may not be rebound"),
        ("foreach i among span(2):\n    consecrated X: int = i\n", "loop"),
        ("augur:\n    Sanctioned\n", "rite"),
        ("consecrated PORT: int\n", "not bound to a single value"),
        (
            "rite f(x: int) -> int:\n    y = x\n    augur:\n        x > 0\n"
            "    render y\n",
            "opening",
        ),
        ("litany(2, curse=MotiveFailure):\n    cease\n", "cease in a litany"),
    ],
    ids=["rebinding", "loop", "stray-augury", "unsealed", "late-augury", "cease"],
)
def test_sanction_false_suppresses_nothing_else(src, fault):
    # Every other rejection is a property of well-formed Liturgy, not a
    # policy about what an author declares, and the backstop must keep
    # catching all of them.
    with pytest.raises(TechHeresy, match=fault):
        compile_litany(src, "prayer.lit", sanction=False)


def test_sanction_defaults_to_on():
    # Nothing that chants may opt out by accident.
    with pytest.raises(TechHeresy):
        compile_litany("rite f(x):\n    render x\n", "prayer.lit")
