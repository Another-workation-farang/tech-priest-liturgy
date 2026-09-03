import pytest

from liturgy.compiler import _PASSES
from liturgy.reverse import to_liturgy
from liturgy.transform import transform


def test_keywords_are_reversed():
    assert to_liturgy("def f():\n    return 1\n") == "rite f():\n    render 1\n"


def test_builtins_are_reversed():
    assert to_liturgy("print(len(x))\n") == "intone(measure(x))\n"


def test_attribute_names_are_left_alone():
    # The same exemption as the forward direction: obj.return is not a thing,
    # and obj.render is somebody's method.
    assert to_liturgy("template.render()\n") == "template.render()\n"


def test_keyword_arguments_are_left_alone():
    assert to_liturgy("f(print=1)\n") == "f(print=1)\n"


def test_import_targets_are_left_alone():
    assert to_liturgy("from jinja2 import render\n") == "within jinja2 invoke render\n"


def test_the_line_count_is_preserved():
    src = "def f():\n    if x:\n        return 1\n    return 2\n"
    assert to_liturgy(src).count("\n") == src.count("\n")


def test_it_round_trips_through_transform():
    src = "class C:\n    def m(self):\n        return [i for i in range(3)]\n"
    assert transform(to_liturgy(src)).python == src


# --- the one phrase rule ----------------------------------------------------
#
# Every other rule here is word-for-word. `introit` is a macro, so its
# reversal reads a token sequence and collapses it; these pin exactly which
# shapes it claims and which it leaves as Python. `to_liturgy`'s docstring
# is the prose version of the same list.


def test_the_main_guard_becomes_an_introit():
    assert to_liturgy('if __name__ == "__main__":\n    main()\n') == (
        "introit:\n    main()\n"
    )


def test_the_guards_if_is_not_also_reversed_to_should():
    # The alias pass wants this `if`; the phrase rule wants the whole span.
    # Two substitutions over the same columns splice into nonsense, so the
    # phrase has to win and the word-for-word one has to be dropped.
    lit = to_liturgy('if __name__ == "__main__":\n    main()\n')
    assert "should" not in lit


def test_an_indented_guard_becomes_an_introit():
    src = 'def f():\n    if __name__ == "__main__":\n        main()\n'
    assert to_liturgy(src) == "rite f():\n    introit:\n        main()\n"


def test_a_trailing_comment_survives_the_phrase_rule():
    assert to_liturgy('if __name__ == "__main__":  # go\n    main()\n') == (
        "introit:  # go\n    main()\n"
    )


@pytest.mark.parametrize(
    "src",
    [
        "if __name__ == '__main__':\n    main()\n",       # single quotes
        'if __name__=="__main__":\n    main()\n',         # no spaces
        'if  __name__ == "__main__":\n    main()\n',      # extra whitespace
        'if __name__ == "__main__" and r:\n    main()\n',  # a longer condition
        'if __name__ == "__main__": main()\n',            # a one-line body
        'if x:\n    pass\nelif __name__ == "__main__":\n    main()\n',
        'x = 1 if __name__ == "__main__" else 2\n',       # a ternary
    ],
)
def test_the_shapes_the_phrase_rule_deliberately_leaves_as_python(src):
    # None of these can be spelled `introit:` and put back exactly as found,
    # and a reversal that does not round-trip is worse than no reversal.
    # Leaving them is safe: Liturgy is a superset of Python.
    assert "introit" not in to_liturgy(src)
    assert transform(to_liturgy(src), _PASSES).python == src


def test_the_guard_round_trips_through_the_compilers_passes():
    src = 'def main():\n    return 0\n\n\nif __name__ == "__main__":\n    main()\n'
    assert transform(to_liturgy(src), _PASSES).python == src
