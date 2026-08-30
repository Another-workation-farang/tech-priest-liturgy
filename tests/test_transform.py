import ast

import pytest

from liturgy.transform import transform


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
