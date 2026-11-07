import ast
import io
import pathlib
import traceback

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


TABLES = {
    "hymn.py": ("hymn.lit", {3: 7, 4: 9}, ["", "", "", "", "", "", "rite main() -> Void:", "", "    divide(1, 0)"]),
    "helpers/util.py": ("helpers/util.lit", {1: 1, 2: 2}, ["rite whisper() -> Void:", "    proclaim LostPattern('x')"]),
    "other/util.py": ("other/util.lit", {1: 1}, ["rite shout() -> str:"]),
}


def _frame(path, line, name="main"):
    return traceback.FrameSummary(path, line, name, lookup_line=False)


def test_table_seer_maps_generated_lines_to_litany_lines(tmp_path):
    seer = rubric.TableSeer(TABLES, str(tmp_path))
    assert seer.place(_frame(str(tmp_path / "hymn.py"), 4)) == ("hymn.lit", 9, "    divide(1, 0)", None)


def test_unmapped_line_falls_back_to_the_nearest_mapped_line_above(tmp_path):
    seer = rubric.TableSeer(TABLES, str(tmp_path))
    assert seer.place(_frame(str(tmp_path / "hymn.py"), 5))[1] == 9


def test_frame_above_every_mapped_line_keeps_its_number_without_source(tmp_path):
    seer = rubric.TableSeer(TABLES, str(tmp_path))
    assert seer.place(_frame(str(tmp_path / "hymn.py"), 1)) == ("hymn.lit", 1, "", None)


def test_same_stem_in_two_packages_is_kept_apart(tmp_path):
    seer = rubric.TableSeer(TABLES, str(tmp_path))
    assert seer.place(_frame(str(tmp_path / "helpers" / "util.py"), 2))[0] == "helpers/util.lit"


def test_files_outside_the_tables_are_not_litanies(tmp_path):
    seer = rubric.TableSeer(TABLES, str(tmp_path))
    assert not seer.is_litany(str(tmp_path / "helper.py"))
    assert not seer.is_litany("/usr/lib/python3/threading.py")


def test_syntax_errors_and_plumbing(tmp_path):
    seer = rubric.TableSeer(TABLES, str(tmp_path))
    exc = SyntaxError("bad", (str(tmp_path / "hymn.py"), 3, 1, "x", 3, 2))
    assert seer.place_syntax(exc) == ("hymn.lit", 7, "rite main() -> Void:", None)
    assert seer.is_plumbing(_frame("<frozen importlib._bootstrap>", 1))
    assert not seer.is_plumbing(_frame(str(tmp_path / "hymn.py"), 1))
