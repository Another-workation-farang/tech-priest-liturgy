import io
import token as tokmod
import tokenize

import pytest

from liturgy import transform as _t
from liturgy.constructs import TechHeresy, heresy, statement_starts


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
    assert "beta" not in positions("alpha = servitor: beta\n")


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
    exec(compile_litany("consecrated PORT = 8080\n", "prayer.lit"), ns)
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
