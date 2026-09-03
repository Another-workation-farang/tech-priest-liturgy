import io
import token as tokmod
import tokenize

import pytest

from liturgy import transform as _t
from liturgy.constructs import (
    TechHeresy,
    carrier_pass,
    heresy,
    statement_starts,
)


def positions(src):
    """Names at statement-start position, by their text."""
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    significant = [t for t in toks if t.type not in _t._INSIGNIFICANT]
    starts = statement_starts(significant)
    return {
        significant[i].string
        for i in starts
        if significant[i].type == tokmod.NAME
    }


def test_first_token_of_a_file_is_a_statement_start():
    assert "alpha" in positions("alpha = 1\n")


def test_token_after_a_newline_is_a_statement_start():
    assert "beta" in positions("alpha = 1\nbeta = 2\n")


def test_token_after_a_semicolon_is_a_statement_start():
    assert "beta" in positions("alpha = 1; beta = 2\n")


def test_token_after_a_block_colon_is_a_statement_start():
    assert "beta" in positions("if alpha: beta = 2\n")


def test_token_inside_a_call_is_not_a_statement_start():
    assert "beta" not in positions("alpha(beta)\n")


def test_dict_value_after_a_colon_is_not_a_statement_start():
    # The colon rule must not fire inside brackets.
    assert "beta" not in positions("alpha = {1: beta}\n")


def test_slice_bound_after_a_colon_is_not_a_statement_start():
    assert "beta" not in positions("alpha = items[1:beta]\n")


def test_annotation_after_a_colon_is_not_a_statement_start():
    assert "int" not in positions("alpha: int = 1\n")


def test_indented_body_token_is_a_statement_start():
    assert "beta" in positions("if alpha:\n    beta = 2\n")


def test_bare_block_openers_are_handled():
    # `else:` and `try:` have no expression before the colon.
    assert "beta" in positions("if a:\n    pass\nelse: beta = 2\n")
    assert "beta" in positions("try: beta = 2\nexcept E:\n    pass\n")


def test_liturgy_spellings_open_blocks_too():
    # The carrier pass runs before substitution, so the token stream holds
    # whichever spelling the author used.
    assert "beta" in positions("should alpha: beta = 2\n")
    assert "beta" in positions("foreach x among y: beta = 2\n")


def test_lambda_colon_does_not_start_a_statement():
    assert "beta" not in positions("alpha = lambda: beta\n")
    assert "beta" not in positions("alpha = versicle: beta\n")


def test_heresy_carries_everything_the_curse_renderer_needs():
    exc = heresy("no", "prayer.lit", 3, 5, "consecrated X = 1\n")
    assert isinstance(exc, TechHeresy)
    assert isinstance(exc, SyntaxError)
    assert (exc.filename, exc.lineno, exc.offset) == ("prayer.lit", 3, 5)
    assert exc.text == "consecrated X = 1\n"


# --- I8: a Substitution's span must lie within one row ---------------------
#
# `_consecrated_carrier` built the keyword-swallowing span from the keyword's
# *row* and the name's *end column*. Across a line continuation those are two
# different rows, so the span reached off the end of its own line and
# `_splice` quietly cut `consecrated \` down to `ecrated \`. The author got
# `SyntaxError: invalid syntax` pointing at text they never wrote.


def test_consecrated_across_a_line_continuation_is_a_real_heresy():
    from liturgy.compiler import compile_litany

    with pytest.raises(TechHeresy) as exc:
        compile_litany("consecrated \\\n    PORT = 8080\n", "prayer.lit")
    assert "must share a line" in str(exc.value)
    assert exc.value.lineno == 1
    assert exc.value.filename == "prayer.lit"


def test_a_single_line_consecrated_is_untouched_by_the_guard():
    from liturgy.compiler import compile_litany

    ns = {}
    exec(compile_litany("consecrated PORT: int = 8080\n", "prayer.lit"), ns)
    assert ns["PORT"] == 8080


def test_splice_refuses_a_span_that_reaches_past_its_row():
    # The guard `_splice`'s newline check cannot provide: the replacement
    # text is empty, so there is nothing in it to inspect. Only the span
    # gives the breakage away.
    with pytest.raises(ValueError, match="does not lie within row"):
        _t._splice("ab\ncdefgh\n", [_t.Substitution(1, 0, 6, "")])


def test_splice_refuses_a_backwards_span():
    with pytest.raises(ValueError, match="does not lie within row"):
        _t._splice("abcdef\n", [_t.Substitution(1, 4, 2, "")])


def test_splice_still_accepts_a_span_that_ends_at_the_end_of_its_row():
    # The newline is part of the line, so col_end may reach it.
    py, _smap = _t._splice("abc\n", [_t.Substitution(1, 0, 3, "xyz")])
    assert py == "xyz\n"


# --- Spec IV: consecration travels beside the source, not through it --------
#
# `consecrated NAME = v` used to generate `NAME: __consecrated__ = v`. That
# spent the annotation slot on the machine's own bookkeeping, so a
# consecrated name could never declare an archetype -- `consecrated PORT:
# int = 8080` was a syntax error, the slot already being taken. The
# generated Python is now exactly what the author wrote minus the keyword,
# and the fact that the line was a header rides in the `ConstructFacts` the
# pass returns alongside its substitutions.


def carried(src):
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    return carrier_pass(toks)


def generated(src):
    from liturgy.compiler import _PASSES

    return _t.transform(src, _PASSES).python


def test_a_consecrated_header_generates_a_plain_assignment():
    assert generated("consecrated PORT = 8080\n") == "PORT = 8080\n"


def test_a_consecrated_header_leaves_the_annotation_slot_alone():
    assert generated("consecrated PORT: int = 8080\n") == "PORT: int = 8080\n"


def test_an_indented_header_keeps_its_indentation():
    src = "rite f():\n    consecrated INNER: int = 1\n"
    assert generated(src) == "def f():\n    INNER: int = 1\n"


def test_the_header_still_costs_no_line():
    src = "consecrated PORT: int = 8080\nintone(PORT)\n"
    assert generated(src).count("\n") == src.count("\n")


def test_the_pass_reports_the_row_column_and_name_of_the_header():
    assert carried("consecrated PORT = 8080\n").facts.consecrated == frozenset(
        {_t.Consecration(1, 12, "PORT")}
    )


def test_the_reported_column_is_the_name_not_the_keyword():
    facts = carried("rite f():\n    consecrated INNER = 1\n").facts
    assert facts.consecrated == frozenset({_t.Consecration(2, 16, "INNER")})


def test_two_headers_on_one_row_are_both_reported():
    # Why the record carries a column and not a row alone: a row can hold
    # two declarations, and -- worse -- a declaration and a rebinding of the
    # same name, which the compiler has to tell apart.
    facts = carried("consecrated A = 1; consecrated B = 2\n").facts
    assert facts.consecrated == frozenset(
        {_t.Consecration(1, 12, "A"), _t.Consecration(1, 31, "B")}
    )


def test_a_litany_that_consecrates_nothing_reports_no_facts():
    assert not carried("x = 1\nintone(x)\n").facts


# --- introit: the one macro -------------------------------------------------
#
# `introit:` is not a spelling, it is an expansion: one token becomes
# `if __name__ == "__main__"`. There is no carrier name and no AST pass --
# what it generates is already ordinary Python -- so the whole of the
# construct is the substitution these tests pin.


def test_introit_becomes_the_main_guard():
    assert generated("introit:\n    main()\n") == (
        'if __name__ == "__main__":\n    main()\n'
    )


def test_introit_costs_no_line():
    src = "introit:\n    main()\n"
    assert generated(src).count("\n") == src.count("\n")


def test_introit_keeps_its_indentation():
    src = "rite f():\n    introit:\n        main()\n"
    assert generated(src) == (
        'def f():\n    if __name__ == "__main__":\n        main()\n'
    )


def test_introit_leaves_the_colon_and_a_trailing_comment_alone():
    # The substitution stops at the word. The colon is the author's, and so
    # is anything after it -- which is how a trailing comment survives.
    assert generated("introit:  # the entrance\n    main()\n") == (
        'if __name__ == "__main__":  # the entrance\n    main()\n'
    )


def test_introit_reports_no_facts():
    # Nothing travels out of band: the generated Python says the whole of it.
    assert not carried("introit:\n    main()\n").facts


@pytest.mark.parametrize(
    "src",
    [
        "introit = 5\n",                       # a name of the author's own
        "introit: int = 5\n",                  # an annotation with a value
        "x = introit\n",                       # a load
        "obj.introit\n",                       # Rule 1: attribute position
        "f(introit=1)\n",                      # Rule 2: keyword argument
        "pattern introit:\n    abide\n",       # a class of that name
        "rite introit(x: int) -> int:\n    render x\n",
    ],
)
def test_introit_out_of_header_position_is_the_authors_own(src):
    # A construct word is only a construct in the position its header
    # occupies. Anywhere else it is an ordinary name: the word survives into
    # the generated Python and no guard is spliced in. Compared against the
    # source rather than the word alone this would fail on the two samples
    # that also contain an alias -- `rite` is `def`, `abide` is `pass`.
    py = generated(src)
    assert "introit" in py
    assert "__main__" not in py


def test_introit_cannot_be_parameterised():
    # There is nothing to parameterise: an author wanting a different
    # comparison writes the Python. A header that opens a block and is not
    # the bare word is loud rather than silently ignored.
    with pytest.raises(TechHeresy) as err:
        carried("introit(x):\n    main()\n")
    assert "takes no arguments" in str(err.value)
