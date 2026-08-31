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


# --- .py files: clause (b) only ---
def test_python_bindings_of_liturgy_words_collide():
    src = "span = 5\ndef render(): pass\nx = 1\n"
    assert words(src, liturgy=False) == [(1, "span", "range"), (2, "render", "return")]


def test_clean_python_has_no_collisions():
    assert words("x = 1\nimport os\n", liturgy=False) == []


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
