import ast

import pytest

from liturgy.lexicon import LEXICON
from liturgy.transform import (
    Substitution,
    UnfinishedLitany,
    split_lines,
    transform,
)


def py(src):
    return transform(src)[0]


def test_substitutes_a_keyword():
    assert py("rite f():\n    abide\n") == "def f():\n    pass\n"


def test_leaves_plain_python_untouched():
    src = "def f(x):\n    return x + 1\n"
    assert py(src) == src


def test_never_touches_string_contents():
    assert py('x = "rite abide"\n') == 'x = "rite abide"\n'


def test_never_touches_comments():
    assert py("x = 1  ## rite abide\n") == "x = 1  ## rite abide\n"


def test_substitutes_inside_fstring_replacement_fields():
    # 3.12+ tokenizes f-string internals as real NAME tokens, so this IS code.
    assert py('rite f():\n    render f"{measure(x)}"\n') == (
        'def f():\n    return f"{len(x)}"\n'
    )


def test_does_not_touch_fstring_literal_text():
    assert py('x = f"rite {y}"\n') == 'x = f"rite {y}"\n'


def test_preserves_line_count():
    src = "rite f():\n    should x:\n        render 1\n    render 2\n"
    assert py(src).count("\n") == src.count("\n")


def test_output_parses():
    src = "rite f(n):\n    should n < 2:\n        render n\n    render f(n - 1)\n"
    ast.parse(py(src))


def test_multiline_string_bodies_are_untouched():
    src = 'x = """\nrite abide\n"""\n'
    assert py(src) == src


@pytest.mark.parametrize(
    "src",
    [
        "x = 1\n",
        "class A:\n    def m(self):\n        return [i for i in range(3)]\n",
        "with open('f') as fh:\n    data = fh.read()\n",
        "async def go():\n    await thing()\n",
    ],
)
def test_identity_on_python_without_liturgy_words(src):
    assert py(src) == src


def test_columns_map_back_to_original():
    src = "should x:\n    abide\n"
    out, smap = transform(src)
    assert out == "if x:\n    pass\n"
    # "x" sits at python col 3, liturgy col 7
    assert smap.to_lit(1, 3) == 7


# Regression: C1 — str.splitlines() breaks on \x0b \x0c \x1c \x1d \x1e \x85
#    , but CPython's tokenizer breaks only on "\n". Splicing on the
# former desynchronises the line list from the token rows, and every
# substitution after the first such character lands on the wrong line.
def test_form_feed_between_statements_does_not_shift_substitutions():
    src = 'intone("before")\n\x0c\nintone("after")\n'
    assert py(src) == 'print("before")\n\x0c\nprint("after")\n'


def test_line_separator_inside_a_string_literal_does_not_shift_lines():
    # \x1c inside a string is legal Python and must not be read as a break.
    src = 's = "a\x1cb"\nrite f():\n    abide\n'
    assert py(src) == 's = "a\x1cb"\ndef f():\n    pass\n'


@pytest.mark.parametrize("sep", ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85"])
def test_splitting_matches_the_tokenizer_for_every_str_line_break(sep):
    src = f'x = "{sep}"\nrender measure\n'
    assert py(src) == f'x = "{sep}"\nreturn len\n'


def test_split_lines_is_lossless():
    for src in ["", "a", "a\n", "a\n\nb", "\x0c\n", "a\x0cb\nc"]:
        assert "".join(split_lines(src)) == src


def test_a_pass_that_adds_a_line_is_rejected_loudly():
    # No shipped pass can do this, but Spec II's CarrierPass is precisely
    # the pass that will, and a silent line shift is unrecoverable.
    def bad_pass(toks):
        return [Substitution(1, 0, 1, "a\nb")]

    with pytest.raises(ValueError, match="would add a line"):
        transform("x = 1\n", passes=(bad_pass,))


def test_splice_span_guard_excludes_the_trailing_newline():
    # `lines[row - 1]` keeps its trailing "\n" (see `split_lines`), so a
    # guard that measures against the raw line length lets a span that
    # reaches one column past the real text through -- [0, 6) is not a
    # valid span within "abcde" even though "abcde\n" is 6 characters long.
    # Letting it through would silently splice two lines together.
    def swallows_the_newline(toks):
        return [Substitution(1, 0, 6, "")]

    with pytest.raises(ValueError, match=r"does not lie within row"):
        transform("abcde\n", passes=(swallows_the_newline,))


def test_splice_span_guard_allows_the_full_line_up_to_the_newline():
    # The boundary case just inside the guard: a span reaching exactly the
    # end of the line's text, not its newline, is legitimate.
    def replaces_the_whole_line(toks):
        return [Substitution(1, 0, 5, "fghij")]

    out, _ = transform("abcde\n", passes=(replaces_the_whole_line,))
    assert out == "fghij\n"


# Regression: I6 — transform's failure contract. tokenize.TokenError is not
# a SyntaxError and carries no filename, so an unclosed bracket -- the
# commonest typo -- escaped chant raw.
def test_unclosed_bracket_raises_a_located_syntax_error():
    with pytest.raises(UnfinishedLitany) as info:
        transform('intone("a")\nintone(1 +\n', filename="synerr.lit")
    err = info.value
    assert isinstance(err, SyntaxError)
    assert err.filename == "synerr.lit"
    assert err.lineno == 2
    assert "never closed" in err.msg
    assert err.offset == 6  # the "(" in the generated `print(1 +`


def test_unterminated_string_raises_a_located_syntax_error():
    with pytest.raises(UnfinishedLitany) as info:
        transform('x = """abc\n', filename="strerr.lit")
    assert "unterminated" in info.value.msg
    assert info.value.filename == "strerr.lit"


def test_unfinished_litany_carries_a_usable_column_map():
    # The map for everything that did tokenise, so the curse can still put a
    # caret on the failure. "intone" -> "print" shifts columns by one.
    with pytest.raises(UnfinishedLitany) as info:
        transform("intone(1 +\n", filename="c.lit")
    assert info.value.sourcemap is not None
    assert info.value.sourcemap.to_lit(1, 5) == 6


def test_a_real_tokenizer_syntax_error_keeps_its_type_and_gains_a_filename():
    # A dedent matching no outer level is complete and unrecoverable, not
    # unfinished: it must not be reported as an UnfinishedLitany.
    with pytest.raises(IndentationError) as info:
        transform("should Sanctioned:\n  x=1\n y=2\n", filename="dedent.lit")
    assert not isinstance(info.value, UnfinishedLitany)
    assert info.value.filename == "dedent.lit"


def test_the_default_filename_is_used_when_none_is_given():
    with pytest.raises(UnfinishedLitany) as info:
        transform("x = [\n")
    assert info.value.filename == "<litany>"


# I8 — the spec requires transform tests "table-driven across every lexicon
# entry". Without this, 25 of the 58 entries appeared in no test at all, and
# a typo'd target ("unseal": "openn") passed the whole suite.
@pytest.mark.parametrize(
    "lit,target", sorted(LEXICON.items()), ids=sorted(LEXICON)
)
def test_every_lexicon_entry_substitutes(lit, target):
    assert py(f"x = {lit}\n") == f"x = {target}\n"


@pytest.mark.parametrize(
    "lit,target", sorted(LEXICON.items()), ids=sorted(LEXICON)
)
def test_no_lexicon_entry_substitutes_in_attribute_position(lit, target):
    assert py(f"x = obj.{lit}\n") == f"x = obj.{lit}\n"
