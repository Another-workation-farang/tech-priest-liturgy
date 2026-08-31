import pytest

from liturgy.collisions import Collision, find_collisions


def words(src, *, liturgy=True):
    return sorted(
        (c.line, c.word, c.target)
        for c in find_collisions(src, "p.lit" if liturgy else "p.py", liturgy=liturgy)
    )


# --- clause (a): a substitution landed on a binding ---
def test_a_quiet_assignment_collides():
    assert words('span = "text range"\n') == [(1, "span", "range")]


def test_a_for_target_collides():
    assert words("foreach span among [1]:\n    abide\n") == [(1, "span", "range")]


def test_a_with_as_target_collides():
    src = "anointed unseal('f') styled measure:\n    abide\n"
    assert words(src) == [(1, "measure", "len")]


def test_a_rite_name_collides():
    assert words("rite span():\n    abide\n") == [(1, "span", "range")]


def test_a_pattern_name_collides():
    assert words("pattern measure:\n    abide\n") == [(1, "measure", "len")]


def test_an_except_as_target_collides():
    src = "attempt:\n    abide\ncurse MachineCurse styled measure:\n    abide\n"
    assert words(src) == [(3, "measure", "len")]


def test_a_walrus_target_collides():
    assert words("should (span := 1):\n    abide\n") == [(1, "span", "range")]


def test_an_unpacked_target_collides():
    assert words("span, other = 1, 2\n") == [(1, "span", "range")]


def test_a_curse_name_collides_and_is_quiet():
    # MachineCurse -> Exception is a name, not a keyword: it compiles and shadows.
    found = find_collisions("MachineCurse = 5\n", "p.lit", liturgy=True)
    assert [(c.word, c.target, c.quiet) for c in found] == [
        ("MachineCurse", "Exception", True)
    ]


# --- clause (b): the binding survived unsubstituted ---
def test_an_import_alias_collides():
    # Rule 3 protects the target from substitution, so the binding stays
    # `span` -- but every later reference to it becomes `range`.
    assert words("invoke os styled span\n") == [(1, "span", "range")]


def test_an_import_target_collides():
    assert words("within jinja2 invoke render\n") == [(1, "render", "return")]


# --- bindings _stored_names does not report, which collisions still needs ---
def test_a_parameter_name_collides():
    # def f(span) becomes def f(range).
    assert words("rite f(span):\n    render span\n") == [(1, "span", "range")]


def test_a_comprehension_target_collides():
    # [i for i in xs] with i == `span` becomes [i for i in xs] with i ==
    # `range` -- quiet, because `range` is a builtin name, not a keyword.
    #
    # The brief's original example here used `pattern` -> `class`, a
    # *keyword* target. That example is wrong: substituting a keyword into
    # a binding position always produces invalid Python (`class` cannot
    # name a comprehension target any more than `return` can name an
    # assignment target), so `ast.parse` raises before there is a tree to
    # walk -- see test_a_comprehension_target_can_be_a_loud_collision below,
    # which is the corrected form of that case.
    assert words("x = [i foreach span among xs]\n") == [(1, "span", "range")]


def test_a_comprehension_target_can_be_a_loud_collision():
    # [p for p in xs] with p == `pattern` becomes [class for class in xs]:
    # `class` is a keyword, so this is loud exactly like `render = 1` ->
    # `return = 1` -- the generated Python does not parse.
    with pytest.raises(SyntaxError):
        find_collisions(
            "x = [pattern foreach pattern among xs]\n", "p.lit", liturgy=True
        )


def test_a_universal_declaration_collides():
    src = "rite f():\n    universal span\n    span = 1\n"
    assert (2, "span", "range") in words(src)


# --- NAMED REGRESSIONS: these bind nothing and must never be reported ---
def test_attribute_access_is_not_a_collision():
    assert words("template.render()\n") == []


def test_a_keyword_argument_is_not_a_collision():
    assert words("f(intone=1)\n") == []


def test_correct_use_of_a_reserved_word_is_not_a_collision():
    assert words("intone(measure([1, 2]))\n") == []


# --- positions ---
def test_clause_a_reports_the_words_own_column():
    (c,) = find_collisions("foreach span among [1]:\n    abide\n", "p.lit", liturgy=True)
    assert (c.line, c.col) == (1, 8)


def _cols(src):
    return sorted(
        (c.line, c.col, c.word, c.target)
        for c in find_collisions(src, "p.lit", liturgy=True)
    )


def test_two_duplicate_targets_on_one_row_both_collide():
    # `span, span = 1, 2` substitutes `range` twice on the same row. Keying
    # the substitution lookup by (row, text) alone would keep only the last
    # one and both bindings would resolve to its column -- the first
    # occurrence must not disappear.
    assert _cols("span, span = 1, 2\n") == [
        (1, 0, "span", "range"),
        (1, 6, "span", "range"),
    ]


def test_a_chained_assignment_to_the_same_word_both_collide():
    # `span = span = 1` -- two targets, same statement node, same word.
    assert _cols("span = span = 1\n") == [
        (1, 0, "span", "range"),
        (1, 7, "span", "range"),
    ]


def test_an_import_alias_reports_the_bound_names_column_not_the_statements():
    # `invoke os styled span` -> `import os as span`. Rule 3 never
    # substitutes the alias, so the reported column must be where `span`
    # itself starts in the Liturgy source (17), not column 0 where the
    # `invoke`/`import` statement begins -- `ast.alias`'s own position
    # points at `os`, not the `as`-name, so that position has to be derived
    # from the alias's *end*, not just forwarded.
    (c,) = find_collisions("invoke os styled span\n", "p.lit", liturgy=True)
    assert (c.line, c.col) == (1, 17)


def test_an_import_target_reports_the_bound_names_column_not_the_statements():
    # `within jinja2 invoke render` -> `from jinja2 import render`, no
    # alias. The bound name is `render` itself, at column 21 -- not column
    # 0, where the `within`/`from` statement begins.
    (c,) = find_collisions("within jinja2 invoke render\n", "p.lit", liturgy=True)
    assert (c.line, c.col) == (1, 21)


def test_a_keyword_only_parameter_reports_its_liturgy_column():
    # `rite f(*, span=1):` -> `def f(*, span=1):` -- `rite` -> `def` is one
    # character shorter, so `span` sits at column 9 in the generated Python
    # but column 10 in the Liturgy source. The AST's own column is a
    # generated-Python column and must be mapped back through the
    # SourceMap, not reported as-is.
    #
    # (`span` survives unsubstituted here only because `transform`'s Rule 2
    # treats a parameter default like a call-site keyword argument -- a
    # pre-existing, unrelated quirk this test isn't about.)
    (c,) = find_collisions("rite f(*, span=1):\n    abide\n", "p.lit", liturgy=True)
    assert (c.line, c.col) == (1, 10)


def test_a_duplicate_after_an_earlier_substitution_on_the_same_row():
    # `foreach` -> `for` shifts every later column on the row, and the
    # `span, span` for-target pair still resolves to two distinct,
    # correctly-placed collisions -- both fixes exercised together.
    assert _cols("foreach span, span among [1, 2]:\n    abide\n") == [
        (1, 8, "span", "range"),
        (1, 14, "span", "range"),
    ]


# --- regressions: a load of the same word must not be mistaken for a bind ---
def test_a_load_before_a_bind_on_the_same_row_reports_only_the_bind():
    # A dict keyed by (row, substituted text) alone, consumed in row order,
    # cannot tell a load from a bind -- it would report the load's column
    # (7) instead of the actual bind's (14). Matching by the bind's own
    # position sidesteps the question of order entirely.
    assert _cols("intone(span); span = 1\n") == [(1, 14, "span", "range")]


def test_a_load_before_two_binds_on_the_same_row_reports_both_true_columns():
    # The load at column 7 must not consume either bind's substitution, and
    # the two binds (at 14 and 20) must not be conflated with each other or
    # with the load.
    assert _cols("intone(span); span, span = 1, 2\n") == [
        (1, 14, "span", "range"),
        (1, 20, "span", "range"),
    ]


def test_a_load_after_a_bind_on_the_same_row_reports_only_the_bind():
    assert _cols("span = span + 1\n") == [(1, 0, "span", "range")]


def test_three_binds_on_one_row_all_collide():
    assert _cols("span, span, span = 1, 2, 3\n") == [
        (1, 0, "span", "range"),
        (1, 6, "span", "range"),
        (1, 12, "span", "range"),
    ]


# --- .py files: clause (b) only ---
def test_python_bindings_of_liturgy_words_collide():
    src = "span = 5\ndef render(): pass\nx = 1\n"
    assert words(src, liturgy=False) == [(1, "span", "range"), (2, "render", "return")]


def test_clean_python_has_no_collisions():
    assert words("x = 1\nimport os\n", liturgy=False) == []


# --- constructs: the carrier pass must run too, or a construct header (still
# raw, un-rewritten Python without it) looks like a syntax error to
# `ast.parse` before any collision can be found -- on ordinary, correct code.
def test_a_consecrated_header_is_not_mistaken_for_a_syntax_error():
    assert words("consecrated PORT = 8080\nintone(PORT)\n") == []


def test_a_litany_header_is_not_mistaken_for_a_syntax_error():
    src = "calls = []\nlitany(thrice, curse=MotiveFailure):\n    calls.append(1)\n"
    assert words(src) == []


def test_an_augur_construct_header_is_not_mistaken_for_a_syntax_error():
    src = (
        "rite divide(a, b):\n"
        "    augur:\n"
        "        b be nay Void\n"
        "    render a / b\n"
    )
    assert words(src) == []


def test_a_collision_is_still_found_alongside_a_construct_header():
    assert words("consecrated PORT = 8080\nspan = 1\n") == [(2, "span", "range")]


# --- failure modes ---
def test_source_that_does_not_tokenise_raises():
    # The caller decides what to do; there is no map to scan against.
    from liturgy.transform import UnfinishedLitany

    with pytest.raises(UnfinishedLitany):
        find_collisions("x = (1, 2\n", "p.lit", liturgy=True)


def test_loud_collisions_surface_as_syntax_errors():
    # `render = 1` becomes `return = 1`. There is no tree to walk.
    with pytest.raises(SyntaxError):
        find_collisions("render = 1\n", "p.lit", liturgy=True)


# --- columns are characters, not UTF-8 bytes, in both modes ---
# `ast` counts bytes. A multi-byte character earlier on the row pushes
# `col_offset` past the character column a caret has to be drawn at, and the
# .py branch has no SourceMap to launder it through.
# Seven of them, deliberately: the byte offset has to land clear of the
# substituted word's own span in the generated Python, or a wrong column
# still falls inside it and the test cannot fail.
_MULTIBYTE = 'x = "ééééééé"; span = 1\n'


def test_a_multibyte_character_does_not_shift_the_column_in_a_py_file():
    (c,) = find_collisions(_MULTIBYTE, "p.py", liturgy=False)
    assert (c.line, c.word) == (1, "span")
    assert c.col == _MULTIBYTE.index("span")


def test_a_multibyte_character_does_not_shift_the_column_in_a_litany():
    (c,) = find_collisions(_MULTIBYTE, "p.lit", liturgy=True)
    assert (c.line, c.word) == (1, "span")
    assert c.col == _MULTIBYTE.index("span")
