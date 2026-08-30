import ast

import pytest

from liturgy.transform import Substitution, split_lines, transform


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
