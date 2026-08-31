# tests/test_sourcemap.py
from liturgy.sourcemap import SourceMap, Span, char_offset


def build(*spans):
    m = SourceMap()
    for s in spans:
        m.add(1, s)
    m.freeze()
    return m


def test_absent_line_is_identity():
    m = SourceMap()
    m.freeze()
    assert m.to_lit(7, 12) == 12


def test_column_before_any_substitution_is_unchanged():
    # "should x"  ->  "if x": span py[0,2) <- lit[0,6)
    m = build(Span(0, 2, 0, 6))
    assert m.to_lit(1, 0) == 0


def test_column_inside_substitution_points_at_token_start():
    m = build(Span(0, 2, 0, 6))
    assert m.to_lit(1, 1) == 0


def test_column_after_substitution_shifts_by_delta():
    # python col 3 is one past "if ", lit col 7 is one past "should "
    m = build(Span(0, 2, 0, 6))
    assert m.to_lit(1, 3) == 7


def test_deltas_accumulate_across_multiple_substitutions():
    # "should intone"  ->  "if print"
    #   span A: py[0,2) <- lit[0,6)   delta +4
    #   span B: py[3,8) <- lit[7,13)  delta +1  (cumulative +5)
    m = build(Span(0, 2, 0, 6), Span(3, 8, 7, 13))
    assert m.to_lit(1, 8) == 13


def test_spans_may_be_added_out_of_order():
    m = build(Span(3, 8, 7, 13), Span(0, 2, 0, 6))
    assert m.to_lit(1, 8) == 13


def test_mapping_is_monotonic_within_a_line():
    m = build(Span(0, 2, 0, 6), Span(3, 8, 7, 13))
    cols = [m.to_lit(1, c) for c in range(0, 20)]
    assert cols == sorted(cols)


def test_columns_before_first_span_are_identity():
    # Span starts at py[3], so columns 0-2 are before any substitution
    m = build(Span(3, 8, 7, 13))
    assert m.to_lit(1, 0) == 0
    assert m.to_lit(1, 2) == 2


# --- char_offset: the one door byte offsets come through --------------------
#
# `ast.col_offset`/`end_col_offset` and `traceback`'s `colno`/`end_colno`
# count UTF-8 bytes. Every column `SourceMap` speaks is a character offset.


def test_char_offset_is_the_identity_on_ascii():
    line = "x = 1 // 0\n"
    for i in range(len(line) + 1):
        assert char_offset(line, i) == i


def test_char_offset_discounts_the_extra_bytes_of_earlier_characters():
    line = 'sigil = "✠✠"; boom\n'   # two 3-byte characters
    assert line.index("boom") == 14
    assert line.encode("utf-8").index(b"boom") == 18
    assert char_offset(line, 18) == 14


def test_char_offset_passes_through_when_there_is_no_line_to_measure():
    # An unfinished litany keeps its column map but loses the generated text.
    # "No text" must mean "leave the offset alone", not "collapse it to 0".
    assert char_offset("", 12) == 12


def test_char_offset_of_a_byte_past_the_end_is_the_whole_line():
    line = "✠✠\n"
    assert char_offset(line, 999) == len(line)
