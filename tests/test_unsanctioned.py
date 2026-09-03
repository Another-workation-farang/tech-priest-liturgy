"""`unsanctioned`: the word, the splice, and what it records.

The modifier has no Python spelling at all -- it generates nothing and is
cut out of the line. Everything it means therefore has to travel in
`ConstructFacts`, and everything that could go wrong with it is either a
heresy or a broken line invariant. Task 3's enforcement rule is not tested
here; a litany using the word must compile and run exactly as if the word
were absent, and that is what these tests hold.
"""

import ast
import io
import subprocess
import sys
import tokenize

import pytest

from liturgy import transform as _t
from liturgy.compiler import _PASSES
from liturgy.constructs import TechHeresy, carrier_pass
from liturgy.lexicon import CONSTRUCT_KEYWORDS, LEXICON, RESERVED
from liturgy.rewrite import ConstructPass
from liturgy.transform import Consecration, Exemption, split_lines, transform


def carried(src):
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    return carrier_pass(toks)


def result(src):
    return transform(src, _PASSES)


def generated(src):
    return result(src).python


def facts(src):
    return result(src).facts


def run(src):
    """Compile and execute a litany the whole way, returning its globals."""
    from liturgy.compiler import compile_litany

    code = compile_litany(src, "prayer.lit")
    ns = {"__name__": "__prayer__"}
    exec(code, ns)
    return ns


# --- the word itself -------------------------------------------------


def test_unsanctioned_is_a_construct_keyword():
    assert "unsanctioned" in CONSTRUCT_KEYWORDS


def test_unsanctioned_has_no_python_spelling():
    # A modifier, not an alias: nothing in the lexicon may map to or from it.
    assert "unsanctioned" not in LEXICON
    assert "unsanctioned" not in LEXICON.values()


def test_unsanctioned_is_reserved():
    assert "unsanctioned" in RESERVED


def test_sanctioned_and_unsanctioned_are_different_words():
    # Recorded rather than discovered later: `Sanctioned` is already `True`,
    # and the two are separated by case and by the table they live in.
    assert LEXICON["Sanctioned"] == "True"
    assert "Sanctioned" not in CONSTRUCT_KEYWORDS
    assert "unsanctioned" not in LEXICON
    # Neither is a case-fold of the other, so no lookup that lowercases a
    # token could ever land on the wrong one.
    assert "unsanctioned".casefold() != "Sanctioned".casefold()
    assert generated("x = Sanctioned\n") == "x = True\n"


# --- the three shapes ------------------------------------------------


def test_a_marked_rite_generates_the_bare_rite():
    assert generated("unsanctioned rite legacy(x):\n    render x\n") == (
        "def legacy(x):\n    return x\n"
    )


def test_a_marked_consecrated_generates_the_bare_binding():
    assert generated("unsanctioned consecrated PORT = 8080\n") == "PORT = 8080\n"


def test_a_marked_consecrated_still_leaves_the_annotation_slot_alone():
    assert generated("unsanctioned consecrated PORT: int = 8080\n") == (
        "PORT: int = 8080\n"
    )


def test_the_bare_form_leaves_an_empty_line():
    assert generated("unsanctioned\nintone(1)\n") == "\nprint(1)\n"


def test_a_marked_remote_rite_generates_an_async_def():
    assert generated("unsanctioned remote rite fetch(x):\n    render x\n") == (
        "async def fetch(x):\n    return x\n"
    )


# --- indentation and the line invariant ------------------------------


def test_an_indented_marked_method_keeps_its_indentation():
    # The hazard the splice exists to avoid: cutting only the word would
    # leave its trailing space and shove the method right of its siblings.
    src = (
        "pattern Cogitator:\n"
        "    unsanctioned rite go(self, n):\n"
        "        render n + 1\n"
    )
    assert generated(src) == (
        "class Cogitator:\n"
        "    def go(self, n):\n"
        "        return n + 1\n"
    )


def test_an_indented_marked_consecrated_keeps_its_indentation():
    src = "pattern Cogitator:\n    unsanctioned consecrated LIMIT = 9\n"
    assert generated(src) == "class Cogitator:\n    LIMIT = 9\n"


def test_extra_whitespace_after_the_word_is_swallowed_too():
    assert generated("unsanctioned    consecrated PORT = 1\n") == "PORT = 1\n"


@pytest.mark.parametrize(
    "src",
    [
        "unsanctioned rite f(x):\n    render x\n",
        "unsanctioned consecrated PORT = 1\n",
        "unsanctioned\nrite f(x):\n    render x\n",
        "pattern C:\n    unsanctioned rite go(self):\n        abide\n",
    ],
    ids=["rite", "consecrated", "bare", "method"],
)
def test_the_modifier_costs_no_line(src):
    assert generated(src).count("\n") == src.count("\n")
    assert len(split_lines(generated(src))) == len(split_lines(src))


def test_no_substitution_ever_spans_a_newline():
    # `_splice` refuses one, but only if the pass hands it one to refuse.
    for sub in carried("unsanctioned rite f(x):\n    render x\n").subs:
        assert "\n" not in sub.text


# --- what is recorded ------------------------------------------------


def test_a_marked_rite_is_recorded_at_the_column_of_rite():
    assert facts("unsanctioned rite f(x):\n    render x\n").unsanctioned == (
        frozenset({Exemption(1, 13, "rite")})
    )


def test_a_marked_remote_rite_is_recorded_at_the_column_of_remote():
    # The word that becomes `async` is where the AST node starts.
    got = facts("unsanctioned remote rite f(x):\n    render x\n").unsanctioned
    assert got == frozenset({Exemption(1, 13, "rite")})


def test_a_marked_consecrated_is_recorded_at_the_column_of_the_name():
    # `consecrated` is spliced away too, so the name is the first surviving
    # token -- and the column the matching `Consecration` already carries.
    got = facts("unsanctioned consecrated PORT = 1\n")
    assert got.unsanctioned == frozenset({Exemption(1, 25, "consecrated")})
    assert got.consecrated == frozenset({Consecration(1, 25, "PORT")})


def test_the_bare_form_sets_the_file_flag_and_records_no_statement():
    got = facts("unsanctioned\nrite f(x):\n    render x\n")
    assert got.unsanctioned_file is True
    assert got.unsanctioned == frozenset()


def test_an_unmarked_litany_records_nothing():
    got = facts("rite f(x):\n    render x\n")
    assert got.unsanctioned == frozenset()
    assert got.unsanctioned_file is False


def test_row_alone_cannot_identify_a_marked_binding():
    # The reason `Exemption` carries a column. Two bindings on one row, one
    # marked and one not.
    got = facts("unsanctioned consecrated A = 1; consecrated B = 2\n")
    assert got.unsanctioned == frozenset({Exemption(1, 25, "consecrated")})
    assert {c.name for c in got.consecrated} == {"A", "B"}


def test_facts_merge_carries_both_halves():
    a = _t.ConstructFacts(unsanctioned=frozenset({Exemption(1, 0, "rite")}))
    b = _t.ConstructFacts(unsanctioned_file=True)
    merged = a.merge(b)
    assert merged.unsanctioned == a.unsanctioned
    assert merged.unsanctioned_file is True


def test_facts_are_truthy_when_only_unsanctioned_is_set():
    # The corpus sweep asserts `not carried.facts` for every stdlib file; a
    # `__bool__` that ignored the new fields would make that check blind.
    assert _t.ConstructFacts(unsanctioned_file=True)
    assert _t.ConstructFacts(unsanctioned=frozenset({Exemption(1, 0, "rite")}))
    assert not _t.ConstructFacts()


# --- the contract Task 3 relies on -----------------------------------


def _lit_cols(src):
    """Every rite and binding's Liturgy column, as `rewrite` computes it."""
    out = result(src)
    tree = ast.parse(out.python)
    pass_ = ConstructPass(
        "prayer.lit",
        split_lines(src),
        out.source_map,
        split_lines(out.python),
        out.facts,
    )
    found = set()
    for node in ast.walk(tree):  # a test, not `src/`: no scope question here
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.add(Exemption(node.lineno, pass_._lit_col(node), "rite"))
        elif isinstance(node, ast.Assign) and isinstance(
            node.targets[0], ast.Name
        ):
            found.add(
                Exemption(
                    node.lineno, pass_._lit_col(node.targets[0]), "consecrated"
                )
            )
    return found


@pytest.mark.parametrize(
    "src",
    [
        "unsanctioned rite f(x):\n    render x\n",
        "unsanctioned remote rite f(x):\n    render x\n",
        "unsanctioned consecrated PORT = 1\n",
        "pattern C:\n    unsanctioned rite go(self):\n        abide\n",
        "pattern C:\n    unsanctioned consecrated LIMIT = 9\n",
        "unsanctioned consecrated A = 1; consecrated B = 2\n",
    ],
    ids=["rite", "remote", "consecrated", "method", "class-attr", "semicolons"],
)
def test_every_recorded_exemption_is_findable_from_the_ast(src):
    """The whole point of the record: an AST pass can match it back.

    An `Exemption` whose column no statement node resolves to would exempt
    nothing at all, silently -- the failure mode the record's column exists
    to prevent, and the one Task 3's rule would inherit.
    """
    recorded = facts(src).unsanctioned
    assert recorded
    assert recorded <= _lit_cols(src)


def test_an_annotated_marked_binding_is_findable_too():
    src = "unsanctioned consecrated PORT: int = 1\n"
    out = result(src)
    tree = ast.parse(out.python)
    pass_ = ConstructPass(
        "prayer.lit", split_lines(src), out.source_map,
        split_lines(out.python), out.facts,
    )
    node = tree.body[0]
    assert isinstance(node, ast.AnnAssign)
    assert Exemption(
        node.lineno, pass_._lit_col(node.target), "consecrated"
    ) in out.facts.unsanctioned


# --- it changes nothing about what runs ------------------------------


def test_a_marked_rite_runs_exactly_as_if_the_word_were_absent():
    marked = "unsanctioned rite twice_over(x):\n    render x * 2\n"
    plain = "rite twice_over(x):\n    render x * 2\n"
    assert generated(marked) == generated(plain)
    assert run(marked)["twice_over"](21) == 42


def test_a_marked_consecrated_is_still_sealed():
    from liturgy.constructs import TechHeresy as _TH

    with pytest.raises(_TH):
        run("unsanctioned consecrated PORT = 1\nPORT = 2\n")


def test_the_bare_form_runs_the_litany_beneath_it():
    ns = run("unsanctioned\n\nrite f(a):\n    render a + 1\n")
    assert ns["f"](1) == 2


# --- misplacement is a heresy ----------------------------------------


@pytest.mark.parametrize(
    "src",
    [
        'unsanctioned intone("nope")\n',
        "unsanctioned x = 1\n",
        "unsanctioned pattern C:\n    abide\n",
        "unsanctioned litany(3):\n    abide\n",
        "unsanctioned unsanctioned rite f():\n    abide\n",
        "unsanctioned remote anointed x:\n    abide\n",
        "unsanctioned = 1\n",
        "x = unsanctioned\n",
        "x = unsanctioned + 1\n",
        "intone(unsanctioned)\n",
        "rite f(unsanctioned):\n    abide\n",
        "unsanctioned;\n",
        "rite f():\n    unsanctioned\n",
        "unsanctioned \\\n    rite f():\n        abide\n",
    ],
    ids=[
        "before-a-call", "before-an-assignment", "before-a-pattern",
        "before-a-litany", "doubled", "remote-without-rite", "bound",
        "read", "mid-expression", "as-an-argument", "as-a-parameter",
        "bare-then-semicolon", "indented-and-alone", "continued",
    ],
)
def test_misplaced_unsanctioned_is_a_heresy(src):
    with pytest.raises(TechHeresy):
        result(src)


def test_the_heresy_is_located_at_the_word():
    with pytest.raises(TechHeresy) as exc:
        result('intone(1)\nunsanctioned intone("nope")\n')
    assert exc.value.lineno == 2
    assert exc.value.offset == 1
    assert "unsanctioned" in str(exc.value)


def test_the_mid_statement_heresy_points_at_the_stray_word():
    with pytest.raises(TechHeresy) as exc:
        result("x = 1 + unsanctioned\n")
    assert exc.value.lineno == 1
    assert exc.value.offset == 9
    assert "mid-statement" in str(exc.value)


def test_the_first_fault_in_the_file_is_the_one_reported():
    # Two faults, one per line. The header loop visits statement starts and
    # the stray-word scan visits everything, so without one ordered walk the
    # line-1 fault is blamed on line 2.
    with pytest.raises(TechHeresy) as exc:
        result("unsanctioned = 5\nintone(unsanctioned)\n")
    assert exc.value.lineno == 1
    assert "marks a rite or a consecrated name" in str(exc.value)


def test_an_indented_bare_marker_says_it_must_stand_at_the_margin():
    with pytest.raises(TechHeresy) as exc:
        result("rite f():\n    unsanctioned\n")
    assert "margin" in str(exc.value)


def test_the_curse_renders_the_heresy_with_a_caret(tmp_path):
    """House style, end to end: the real CLI, not a captured exception."""
    path = tmp_path / "prayer.lit"
    path.write_text('intone("before")\nunsanctioned intone("nope")\n')
    proc = subprocess.run(
        [sys.executable, "-m", "liturgy", "chant", str(path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1
    out = proc.stdout + proc.stderr
    assert "MACHINE CURSE" in out
    assert "unsanctioned intone(" in out
    assert "TechHeresy: unsanctioned marks a rite or a consecrated name" in out


# --- the two spared positions ----------------------------------------


def test_attribute_position_is_spared():
    # Rule 1's reasoning: another object's attributes are its own affair.
    assert generated("x = obj.unsanctioned\n") == "x = obj.unsanctioned\n"


def test_keyword_argument_position_is_spared():
    # Rule 2's reasoning, and what keeps the corpus sweep able to hand
    # `transform` a stdlib file that calls `f(unsanctioned=1)`.
    assert generated("f(unsanctioned=1)\n") == "f(unsanctioned=1)\n"
