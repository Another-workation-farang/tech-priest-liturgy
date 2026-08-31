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


def test_a_consecrated_construct_used_correctly_passes(tmp_path):
    # Regression: find_collisions used to transform with the alias pass
    # alone, so a construct header was still raw Python and ast.parse
    # rejected it -- augur failed on ordinary, correct code.
    code, out = run(tmp_path, "ok.lit", "consecrated PORT = 8080\nintone(PORT)\n")
    assert code == 0


def test_a_litany_construct_used_correctly_passes(tmp_path):
    src = "calls = []\nlitany(thrice, curse=MotiveFailure):\n    calls.append(1)\n"
    code, out = run(tmp_path, "ok.lit", src)
    assert code == 0


def test_an_augur_construct_used_correctly_passes(tmp_path):
    # The Spec II `augur` construct, not the verb under test here.
    src = (
        "rite divide(a, b):\n"
        "    augur:\n"
        "        b be nay Void\n"
        "    render a / b\n"
    )
    code, out = run(tmp_path, "ok.lit", src)
    assert code == 0


def test_a_consecrated_rebinding_reports_the_real_heresy(tmp_path):
    # Once find_collisions runs the carrier pass, this reaches compile_litany
    # and surfaces the real TechHeresy at its true line -- not a generic
    # SyntaxError at line 1.
    src = "consecrated PORT = 8080\nintone(PORT)\nPORT = 99\n"
    code, out = run(tmp_path, "bad.lit", src)
    assert code == 1
    assert "TechHeresy" in out
    assert "consecrated and may not be rebound" in out
    assert ", line 3" in out


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


def test_a_symlinked_subdirectory_is_named_not_silently_skipped(tmp_path):
    # rglob lists a symlinked directory but does not descend into it, so a
    # .lit file reachable only that way is invisible to a plain walk.
    # Reporting the tree clean regardless would be a linter lying about
    # what it read.
    real = tmp_path / "real"
    real.mkdir()
    (real / "bad.lit").write_text("span = 1\n")
    (tmp_path / "linked").symlink_to(real, target_is_directory=True)

    buf = io.StringIO()
    code = augur([str(tmp_path)], out=buf)
    out = buf.getvalue()
    assert code == 1
    # Assert on the report's own words, not on the link's name: pytest's
    # tmp_path basename is this test's name truncated, and "symlinked"
    # contains both "symlink" and "linked", so a name-based assertion is
    # satisfied by the path alone and cannot fail.
    assert "not descended into" in out
    assert str(tmp_path / "linked") in out


def test_a_symlinked_top_level_directory_is_scanned_normally(tmp_path):
    # The gap is only for a symlink met partway through a walk -- the path
    # the caller names directly is always walked from, symlink or not.
    real = tmp_path / "real"
    real.mkdir()
    (real / "bad.lit").write_text("span = 1\n")
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)

    buf = io.StringIO()
    code = augur([str(linked)], out=buf)
    assert code == 1
    assert "bad.lit" in buf.getvalue()


# --- Encoding: augur must read a file the way chant and the import path
# read it. `read_text(encoding="utf-8")` did not, and UnicodeDecodeError is
# a ValueError, so it escaped an `-> int` contract as well.


def test_a_latin1_source_with_a_coding_cookie_is_read_not_crashed_on(tmp_path):
    p = tmp_path / "cookie.py"
    p.write_bytes(b'# -*- coding: latin-1 -*-\nx = "caf\xe9"\nspan = 1\n')
    buf = io.StringIO()
    code = augur([str(p)], plain=True, out=buf)
    out = buf.getvalue()
    assert code == 1
    assert "span is reserved" in out
    assert "cannot be decoded" not in out


def test_an_undecodable_file_does_not_end_the_walk(tmp_path):
    # aaa/zzz bracket the bad file alphabetically, so a scan that stops on
    # the first unreadable file reports aaa and never reaches zzz.
    (tmp_path / "aaa.py").write_text("span = 1\n")
    (tmp_path / "mmm.py").write_bytes(b'x = "\xff\xfe"\n')
    (tmp_path / "zzz.py").write_text("span = 2\n")
    buf = io.StringIO()
    code = augur([str(tmp_path)], plain=True, out=buf)
    out = buf.getvalue()
    assert code == 1
    assert "aaa.py:1:1: span is reserved" in out
    assert "zzz.py:1:1: span is reserved" in out
    assert "mmm.py" in out and "cannot be decoded" in out


def test_a_bom_reports_the_real_collision_not_a_fabricated_syntax_error(tmp_path):
    # read_text leaves the BOM in the string and the parser rejects it as a
    # non-printable character; decode_source strips it, as every other
    # reader of this file does.
    p = tmp_path / "bom.py"
    p.write_bytes(b"\xef\xbb\xbfspan = 1\n")
    buf = io.StringIO()
    code = augur([str(p)], plain=True, out=buf)
    out = buf.getvalue()
    assert code == 1
    assert "span is reserved" in out
    assert "SyntaxError" not in out


def test_augur_agrees_with_chant_on_a_bom_prefixed_litany(tmp_path, capfd):
    from liturgy.loader import chant

    p = tmp_path / "bom.lit"
    p.write_bytes(b'\xef\xbb\xbfintone("ave")\n')
    assert chant(str(p), []) == 0
    assert capfd.readouterr().out == "ave\n"

    buf = io.StringIO()
    assert augur([str(p)], plain=True, out=buf) == 0
    assert buf.getvalue() == ""


def test_augur_agrees_with_chant_on_a_latin1_litany(tmp_path, capfd):
    from liturgy.loader import chant

    p = tmp_path / "cookie.lit"
    p.write_bytes(b'# -*- coding: latin-1 -*-\nintone("caf\xe9")\n')
    assert chant(str(p), []) == 0
    assert capfd.readouterr().out == "café\n"

    buf = io.StringIO()
    assert augur([str(p)], plain=True, out=buf) == 0
    assert buf.getvalue() == ""


def test_a_dangling_lit_symlink_is_named_not_silently_dropped(tmp_path):
    # `is_file()` is False for a broken link, so it fell out of the walk
    # entirely -- the same silent skip the symlinked-directory report exists
    # to prevent, for a path that is spelled `.lit` just as plainly.
    (tmp_path / "ok.lit").write_text("intone(1)\n")
    (tmp_path / "dangling.lit").symlink_to(tmp_path / "nowhere.lit")

    buf = io.StringIO()
    code = augur([str(tmp_path)], plain=True, out=buf)
    out = buf.getvalue()
    assert code == 1
    assert "dangling.lit" in out and "cannot be read" in out


def test_a_symlinked_directory_is_reported_once_not_also_as_a_file(tmp_path):
    # A symlinked directory named `linked.lit` is already covered by the
    # unscanned-directories report; it must not also be opened as a file.
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "linked.lit").symlink_to(real, target_is_directory=True)

    buf = io.StringIO()
    code = augur([str(tmp_path)], plain=True, out=buf)
    out = buf.getvalue()
    assert code == 1
    assert out.count("linked.lit") == 1
    assert "not descended into" in out


def test_a_heresy_is_reported_alone_and_still_exits_one(tmp_path):
    # The collision scan runs through the same transform(), so the carrier
    # pass raises before any collision is returned: line 1's `span` surfaces
    # only once the heresy on line 2 is fixed. The exit code is 1 either
    # way, which is the half CI turns on. The spec says so now.
    src = "span = 5\nlitany bad:\n    abide\n"
    code, out = run(tmp_path, "both.lit", src, plain=True)
    assert code == 1
    assert "TechHeresy" in out
    assert "span is reserved" not in out

    fixed = "span = 5\nlitany(thrice):\n    abide\n"
    code, out = run(tmp_path, "fixed.lit", fixed, plain=True)
    assert code == 1
    assert "span is reserved" in out
