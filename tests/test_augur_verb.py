import io

import pytest

from liturgy.tooling import augur


def run(tmp_path, name, src, *, plain=False):
    p = tmp_path / name
    p.write_text(src)
    buf = io.StringIO()
    code = augur([str(p)], plain=plain, out=buf)
    return code, buf.getvalue()


def test_a_clean_litany_passes(tmp_path):
    code, out = run(tmp_path, "clean.lit", "intone(measure([1, 2]))\n")
    assert code == 0
    assert "troubled" not in out


def test_a_quiet_collision_is_reported(tmp_path):
    code, out = run(tmp_path, "quiet.lit", 'span = "text range"\n')
    assert code == 1
    assert "span" in out and "range" in out


def test_plain_output_is_machine_readable(tmp_path):
    code, out = run(tmp_path, "quiet.lit", 'span = "text range"\n', plain=True)
    assert code == 1
    assert out.strip().startswith(str(tmp_path / "quiet.lit") + ":1:1:")


def test_plain_columns_are_one_based(tmp_path):
    # Collision.col is 0-based; editors and CI expect 1-based.
    _, out = run(tmp_path, "q.lit", "foreach span among [1]:\n    abide\n", plain=True)
    assert ":1:9:" in out


def test_a_litany_that_does_not_compile_reports_the_failure(tmp_path):
    # Tokenises cleanly (balanced brackets) but is not valid grammar, so
    # this is a genuine parse/compile failure, not an unfinished litany.
    code, out = run(tmp_path, "bad.lit", "rite f(x x):\n    abide\n")
    assert code == 1
    assert "SyntaxError" in out or "ill-written" in out


def test_a_litany_that_does_not_tokenise_says_the_omens_are_unread(tmp_path):
    # No SourceMap means nothing to scan; reporting "clean" would lie.
    code, out = run(tmp_path, "unfinished.lit", "x = (1, 2\n")
    assert code == 1
    assert "omens unread" in out


def test_a_python_file_is_scanned_for_transcribability(tmp_path):
    code, out = run(tmp_path, "legacy.py", "span = 5\n")
    assert code == 1
    assert "span" in out


def test_a_clean_python_file_passes(tmp_path):
    code, out = run(tmp_path, "fine.py", "x = 1\nimport os\n")
    assert code == 0


def test_a_directory_is_walked(tmp_path):
    (tmp_path / "a.lit").write_text("intone(1)\n")
    (tmp_path / "b.lit").write_text("span = 5\n")
    (tmp_path / "notes.txt").write_text("span = 5\n")  # not ours
    buf = io.StringIO()
    assert augur([str(tmp_path)], out=buf) == 1
    assert "b.lit" in buf.getvalue() and "notes.txt" not in buf.getvalue()


def test_a_missing_path_is_an_error_not_a_pass(tmp_path):
    buf = io.StringIO()
    assert augur([str(tmp_path / "nope.lit")], out=buf) == 1
    assert "nope.lit" in buf.getvalue()
