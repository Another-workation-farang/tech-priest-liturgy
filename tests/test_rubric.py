import ast
import io
import pathlib

from liturgy import rubric


def test_rubric_imports_nothing_from_liturgy():
    tree = ast.parse(pathlib.Path(rubric.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):  # a test, not src/
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0 and not (node.module or "").startswith("liturgy")
        if isinstance(node, ast.Import):
            assert not any(a.name.startswith("liturgy") for a in node.names)


def test_unencodable_source_is_replaced_not_lost():
    class Seer:  # minimal litany seer
        def is_litany(self, f): return f == "x.lit"
        def is_plumbing(self, fr): return False
        def place(self, fr): return ("x.lit", 1, 'intone("⚙")', None)
        def place_syntax(self, e): raise AssertionError
    raw = io.BytesIO()
    file = io.TextIOWrapper(raw, encoding="cp1252")
    try:
        exec(compile("1/0", "x.lit", "exec"))
    except ZeroDivisionError as e:
        rubric.render(type(e), e, e.__traceback__, seer=Seer(), names={"ZeroDivisionError": "DivisionByTheVoid"}, file=file)
    file.flush()
    text = raw.getvalue().decode("cp1252")
    assert rubric.BANNER_OPEN in text and "DivisionByTheVoid: division by zero" in text
    assert 'intone("?")' in text
