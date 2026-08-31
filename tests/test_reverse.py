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
    assert transform(to_liturgy(src))[0] == src
