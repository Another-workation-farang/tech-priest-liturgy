# tests/test_sourcemap.py
from liturgy.sourcemap import SourceMap, Span


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
