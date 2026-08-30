from liturgy.transform import transform


def py(src):
    return transform(src)[0]


# Rule 1: after a dot
def test_attribute_access_is_not_substituted():
    # template.render() must not become template.return()
    assert py("template.render()\n") == "template.render()\n"


def test_attribute_named_pattern_survives():
    assert py("m = regex.pattern\n") == "m = regex.pattern\n"


def test_method_call_on_result_survives():
    assert py("get().span(1)\n") == "get().span(1)\n"


def test_bare_name_still_substituted_alongside_attribute():
    assert py("render obj.render\n") == "return obj.render\n"


# Rule 2: keyword-argument position
def test_keyword_argument_name_is_not_substituted():
    # f(intone=True) must not become f(print=True)
    assert py("f(intone=True)\n") == "f(intone=True)\n"


def test_keyword_argument_value_is_still_substituted():
    assert py("f(mode=Sanctioned)\n") == "f(mode=True)\n"


def test_equality_comparison_is_still_substituted():
    # "==" is a single token, so it must not be mistaken for a kwarg "="
    assert py("f(measure == 1)\n") == "f(len == 1)\n"


def test_walrus_is_still_substituted():
    assert py("f(measure := 1)\n") == "f(len := 1)\n"


def test_assignment_at_module_level_is_still_substituted():
    # depth 0, so this is a real assignment, not a kwarg
    assert py("measure = 1\n") == "len = 1\n"


# Rule 3: import statements
def test_import_target_is_not_substituted():
    assert py("within jinja2 invoke render\n") == "from jinja2 import render\n"


def test_plain_import_target_is_not_substituted():
    assert py("invoke span\n") == "import span\n"


def test_as_clause_still_works_in_imports():
    assert py("invoke jinja2 styled j2\n") == "import jinja2 as j2\n"


def test_import_scope_ends_at_newline():
    assert py("invoke os\nrender measure\n") == "import os\nreturn len\n"


def test_parenthesised_import_list_is_protected():
    src = "within x invoke (render,\n    measure)\n"
    assert py(src) == "from x import (render,\n    measure)\n"


# Regression: Finding 1 — relative imports (a leading dot is not attribute
# access when it appears inside an import statement).
def test_single_dot_relative_import_still_translates_invoke():
    assert py("within . invoke x\n") == "from . import x\n"


def test_double_dot_relative_import_still_translates_invoke():
    assert py("within .. invoke y\n") == "from .. import y\n"


def test_dotted_module_path_import_still_translates_invoke():
    assert py("within a.b invoke c\n") == "from a.b import c\n"


def test_import_target_after_dotted_module_path_stays_protected():
    # "render" is not import-safe, so it must stay untranslated even though
    # it is not the token directly after the dot.
    assert py("within a.render invoke c\n") == "from a.render import c\n"


def test_attribute_access_still_protected_outside_import():
    # Rule 1 must still apply when there is no import in play.
    assert py("template.render()\n") == "template.render()\n"


# Regression: Finding 2 — import scope must end at a semicolon, not just at
# NEWLINE, so a second statement on the same line is not swallowed.
def test_import_scope_ends_at_semicolon():
    assert py("invoke os; render measure\n") == "import os; return len\n"


# Regression: Finding 3 — PEP 701 f-string debug (`{name=}`) and format-spec
# (`{name=:>10}`) syntax tokenizes a bare "=" that must not be mistaken for
# a keyword-argument name.
def test_fstring_debug_equals_value_is_still_substituted():
    assert py('intone(f"{measure=}")\n') == 'print(f"{len=}")\n'


def test_fstring_debug_equals_with_format_spec_is_still_substituted():
    assert py('intone(f"{measure=:>10}")\n') == 'print(f"{len=:>10}")\n'


def test_real_kwarg_inside_fstring_expression_stays_protected():
    # "intone" here is a genuine keyword-argument name, not f-string debug
    # syntax, so it must still be protected by Rule 2.
    assert py('intone(f"{f(intone=1)}")\n') == 'print(f"{f(intone=1)}")\n'


def test_keyword_argument_value_is_still_substituted_after_fstring_fix():
    # Existing Rule 2 behaviour must be unaffected by the f-string guard.
    assert py("f(mode=Sanctioned)\n") == "f(mode=True)\n"
