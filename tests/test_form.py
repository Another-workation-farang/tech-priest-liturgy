"""The formatter behind `sanctify`, at the text level."""

from __future__ import annotations

import pytest

from liturgy.form import UnsanctifiableLitany, sanctify_text


def test_trailing_whitespace_goes():
    assert sanctify_text("x = 1   \ny = 2\t\n") == "x = 1\ny = 2\n"


def test_indentation_becomes_four_spaces():
    src = "rite f():\n  render 1\n"
    assert sanctify_text(src) == "rite f():\n    render 1\n"


def test_nested_indentation_scales_by_level():
    src = "rite f():\n  should 1:\n    render 2\n"
    assert sanctify_text(src) == "rite f():\n    should 1:\n        render 2\n"


def test_over_indentation_is_brought_back():
    src = "rite f():\n        render 1\n"
    assert sanctify_text(src) == "rite f():\n    render 1\n"


def test_a_file_missing_its_final_newline_gains_one():
    assert sanctify_text("x = 1") == "x = 1\n"


def test_a_file_with_several_final_newlines_keeps_one():
    assert sanctify_text("x = 1\n\n\n\n") == "x = 1\n"


def test_runs_of_blank_lines_are_capped_at_two():
    src = "x = 1\n\n\n\n\ny = 2\n"
    assert sanctify_text(src) == "x = 1\n\n\ny = 2\n"


def test_two_blank_lines_are_left_alone():
    src = "x = 1\n\n\ny = 2\n"
    assert sanctify_text(src) == src


# --- the three things a formatter must not touch ---------------------------


def test_a_multiline_string_interior_is_untouched():
    # Trailing spaces and odd indentation inside a string are its value.
    src = 'rite f():\n  s = """\n  interior   \n     odd\n  """\n  render s\n'
    out = sanctify_text(src)
    assert '"""\n  interior   \n     odd\n  """' in out
    assert out.startswith("rite f():\n    s =")


def test_a_standalone_comment_before_a_block_is_indented_with_the_block():
    # tokenize emits this COMMENT *before* the INDENT token, so a naive
    # depth counter would pull it out to the enclosing level.
    src = "rite f():\n  # about x\n  x = 1\n  render x\n"
    out = sanctify_text(src)
    assert out == "rite f():\n    # about x\n    x = 1\n    render x\n"


def test_a_trailing_comment_keeps_its_place_on_the_line():
    src = "x = 1  # a note\n"
    assert sanctify_text(src) == "x = 1  # a note\n"


def test_a_bracket_continuation_keeps_its_alignment():
    # There is no INDENT token for a continuation; the author's alignment
    # is a choice, not an accident.
    src = "y = [1,\n     2]\n"
    assert sanctify_text(src) == src


def test_a_blank_line_inside_a_multiline_string_is_not_capped():
    src = 's = """\n\n\n\n\n"""\n'
    assert sanctify_text(src) == src


# --- properties ------------------------------------------------------------


def test_sanctifying_twice_changes_nothing_the_second_time():
    src = "rite f():\n  # note\n  x = [1,\n     2]   \n  render x\n\n\n\n"
    once = sanctify_text(src)
    assert sanctify_text(once) == once


def test_an_already_clean_litany_is_returned_unchanged():
    src = 'rite greet(name):\n    render f"Ave {name}"\n'
    assert sanctify_text(src) == src


def test_constructs_survive():
    src = "consecrated PORT = 8080\n\nlitany(twice, curse=ValueError):\n  intone(1)\n"
    out = sanctify_text(src)
    assert "consecrated PORT = 8080" in out
    assert "litany(twice, curse=ValueError):" in out
    assert "\n    intone(1)\n" in out


def test_a_litany_that_does_not_parse_is_refused():
    with pytest.raises(UnsanctifiableLitany):
        sanctify_text("rite (:\n")


def test_a_litany_that_does_not_tokenise_is_refused():
    with pytest.raises(UnsanctifiableLitany):
        sanctify_text('s = "unterminated\n')
