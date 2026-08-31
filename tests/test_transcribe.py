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
