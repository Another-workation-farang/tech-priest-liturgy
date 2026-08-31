import io

import pytest

from liturgy.tooling import transcribe


def run(tmp_path, src, *, name="legacy.py", dest=None):
    p = tmp_path / name
    p.write_text(src)
    buf = io.StringIO()
    code = transcribe(str(p), dest, out=buf)
    return code, buf.getvalue()


def test_a_clean_file_is_transcribed_to_stdout(tmp_path):
    code, out = run(tmp_path, "def f():\n    return 1\n")
    assert code == 0
    assert "rite f():" in out and "render 1" in out


def test_it_writes_to_a_destination_when_given_one(tmp_path):
    dest = tmp_path / "out.lit"
    code, out = run(tmp_path, "print(len(x))\n", dest=str(dest))
    assert code == 0
    assert dest.read_text() == "intone(measure(x))\n"
    assert "transcribed" in out


def test_a_collision_refuses_the_whole_file(tmp_path):
    code, out = run(tmp_path, "span = 5\nprint(span)\n")
    assert code == 1
    assert "CANNOT TRANSCRIBE" in out
    # Nothing partial is emitted.
    assert "intone" not in out


def test_every_collision_is_listed_not_just_the_first(tmp_path):
    src = "span = 5\npattern = 6\ndef render(): pass\n"
    code, out = run(tmp_path, src)
    assert code == 1
    for word in ("span", "pattern", "render"):
        assert word in out


def test_a_refusal_names_lines(tmp_path):
    code, out = run(tmp_path, "x = 1\nspan = 5\n")
    assert code == 1
    assert ":2" in out or "line 2" in out


def test_nothing_is_written_when_it_refuses(tmp_path):
    dest = tmp_path / "out.lit"
    code, _ = run(tmp_path, "span = 5\n", dest=str(dest))
    assert code == 1
    assert not dest.exists()


def test_it_verifies_its_own_output_before_writing(tmp_path, monkeypatch):
    # A reverse pass that produces something not round-tripping must be
    # caught here rather than written to disk.
    import liturgy.tooling as tooling

    monkeypatch.setattr(tooling, "to_liturgy", lambda src: "intone('wrong')\n")
    dest = tmp_path / "out.lit"
    code, out = run(tmp_path, "print(1)\n", dest=str(dest))
    assert code == 1
    assert "does not round-trip" in out
    assert not dest.exists()


def test_a_missing_source_is_an_error(tmp_path):
    buf = io.StringIO()
    assert transcribe(str(tmp_path / "nope.py"), None, out=buf) == 1
    assert "nope.py" in buf.getvalue()


def test_a_syntactically_invalid_source_is_refused(tmp_path):
    code, out = run(tmp_path, "def f(:\n")
    assert code == 1
    assert "SyntaxError" in out


def test_a_destination_that_is_a_directory_refuses_cleanly(tmp_path):
    src = tmp_path / "legacy.py"
    src.write_text("def f():\n    return 1\n")
    dest = tmp_path / "adir"
    dest.mkdir()
    buf = io.StringIO()
    code = transcribe(str(src), str(dest), out=buf)
    assert code == 1
    assert "adir" in buf.getvalue()
    # The refusal is reported, not raised -- and the directory is untouched.
    assert dest.is_dir()


def test_a_missing_destination_parent_refuses_cleanly(tmp_path):
    src = tmp_path / "legacy.py"
    src.write_text("def f():\n    return 1\n")
    dest = tmp_path / "nope" / "out.lit"
    buf = io.StringIO()
    code = transcribe(str(src), str(dest), out=buf)
    assert code == 1
    assert "out.lit" in buf.getvalue()
    assert not dest.parent.exists()


def test_a_latin1_source_with_a_coding_cookie_is_transcribed(tmp_path):
    src = tmp_path / "legacy.py"
    src.write_bytes(b"# -*- coding: latin-1 -*-\nx = \"caf\xe9\"\n")
    buf = io.StringIO()
    code = transcribe(str(src), None, out=buf)
    assert code == 0
    assert "café" in buf.getvalue()


def test_a_bom_prefixed_source_is_transcribed(tmp_path):
    src = tmp_path / "legacy.py"
    src.write_bytes(b"\xef\xbb\xbfx = 1\n")
    buf = io.StringIO()
    code = transcribe(str(src), None, out=buf)
    assert code == 0
    assert "x = 1" in buf.getvalue()


def test_crlf_line_endings_are_preserved_in_the_output(tmp_path):
    src = tmp_path / "legacy.py"
    src.write_bytes(b"def f():\r\n    return 1\r\n")
    dest = tmp_path / "out.lit"
    buf = io.StringIO()
    code = transcribe(str(src), str(dest), out=buf)
    assert code == 0
    written = dest.read_bytes()
    assert written == b"rite f():\r\n    render 1\r\n"
    # Every line ending survived as CRLF, not just some of them: counting
    # bare \n (which also matches the \n half of \r\n) against \r\n pairs
    # catches a partial conversion that the exact-bytes check might not.
    assert written.count(b"\r\n") == written.count(b"\n")
