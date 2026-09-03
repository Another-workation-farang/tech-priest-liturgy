import importlib.util
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


def test_a_latin1_destination_is_written_in_latin1_not_utf8(tmp_path):
    # The cookie says latin-1, so "café" must survive on disk as the single
    # 0xe9 byte latin-1 uses, not the two-byte UTF-8 sequence. Asserting the
    # decoded string alone cannot see this bug -- both encodings decode
    # back to the same text -- only the raw bytes on disk can.
    src = tmp_path / "legacy.py"
    src.write_bytes(b"# -*- coding: latin-1 -*-\nx = \"caf\xe9\"\n")
    dest = tmp_path / "out.lit"
    buf = io.StringIO()
    code = transcribe(str(src), str(dest), out=buf)
    assert code == 0
    written = dest.read_bytes()
    assert b"caf\xe9" in written
    assert b"caf\xc3\xa9" not in written  # the UTF-8 mis-encoding
    assert importlib.util.decode_source(written) == (
        "# -*- coding: latin-1 -*-\nx = \"café\"\n"
    )


def test_a_bom_destination_keeps_the_bom(tmp_path):
    src = tmp_path / "legacy.py"
    src.write_bytes(b"\xef\xbb\xbfx = 1\n")
    dest = tmp_path / "out.lit"
    buf = io.StringIO()
    code = transcribe(str(src), str(dest), out=buf)
    assert code == 0
    written = dest.read_bytes()
    assert written.startswith(b"\xef\xbb\xbf")
    assert importlib.util.decode_source(written) == "x = 1\n"


def test_a_plain_utf8_destination_is_unchanged(tmp_path):
    # Regression guard: no cookie, no BOM -- the common case must keep
    # writing exactly as before.
    dest = tmp_path / "out.lit"
    code, out = run(tmp_path, "print(len(x))\n", dest=str(dest))
    assert code == 0
    written = dest.read_bytes()
    assert not written.startswith(b"\xef\xbb\xbf")
    assert written == b"intone(measure(x))\n"


def test_it_verifies_the_bytes_it_is_about_to_write_not_just_the_text(
    tmp_path, monkeypatch
):
    # The text-level check compares two `str`s, neither of which ever meets
    # an encoding, so it cannot see bytes that are wrong for the encoding
    # their own cookie declares. Make the destination encoding disagree with
    # the cookie the output carries: the text round-trip still passes, the
    # encode still succeeds, and only the byte-level check can catch it.
    import liturgy.tooling as tooling

    monkeypatch.setattr(tooling, "_source_encoding", lambda raw: "utf-8")
    src = tmp_path / "legacy.py"
    src.write_bytes(b'# -*- coding: latin-1 -*-\nx = "caf\xe9"\n')
    dest = tmp_path / "out.lit"
    buf = io.StringIO()
    code = transcribe(str(src), str(dest), out=buf)
    assert code == 1
    assert "does not round-trip" in buf.getvalue()
    assert not dest.exists()


# --- the output is what augur will read, so warn about it here ---
# `to_liturgy` can bind a reserved word the Python never did: `input`
# becomes `hearken`. The file is correct and chants, so this warns; it must
# not become a refusal.
_INTRODUCES = 'def encode(self, input, errors="strict"):\n    return input\n'


def test_a_collision_introduced_by_transcription_is_warned_about(tmp_path):
    dest = tmp_path / "out.lit"
    code, out = run(tmp_path, _INTRODUCES, dest=str(dest))
    assert code == 0
    assert dest.exists()
    assert "transcribed" in out
    assert "hearken" in out and "input" in out
    assert "augur will flag these" in out


def test_the_warning_is_not_a_refusal(tmp_path):
    # The input itself is clean, so nothing here may raise the exit code or
    # withhold the file.
    dest = tmp_path / "out.lit"
    code, out = run(tmp_path, _INTRODUCES, dest=str(dest))
    assert code == 0
    assert "CANNOT TRANSCRIBE" not in out
    assert "hearken" in dest.read_text()


def test_a_clean_output_is_not_warned_about(tmp_path):
    dest = tmp_path / "out.lit"
    code, out = run(tmp_path, "print(1)\n", dest=str(dest))
    assert code == 0
    assert "COLLISION" not in out


def test_the_stdout_payload_stays_clean_and_the_warning_goes_to_stderr(
    tmp_path, capsys
):
    # Piping `transcribe x.py > x.lit` must not splice a report into the
    # file. Everything transcribe prints to `out` here is the litany.
    code, out = run(tmp_path, _INTRODUCES)
    assert code == 0
    assert "COLLISION" not in out
    assert out == "rite encode(self, hearken, errors=\"strict\"):\n    render hearken\n"
    assert "hearken" in capsys.readouterr().err


# --- Spec IV: transcribed Python is unannotated by definition --------------
#
# Python does not require annotations, so a transcription never carries
# them. The backstop compiles with the archetype rule suppressed -- asking
# "is this a program?", not "does this meet the annotation policy?" -- and
# the omens say plainly that the output needs archetypes before it chants.
# Refusing instead refused every real Python file with a function in it.

_UNANNOTATED = "def greet(name):\n    return name\n"
_ANNOTATED = "def greet(name: str) -> str:\n    return name\n"


def test_a_function_without_annotations_is_still_transcribed(tmp_path):
    dest = tmp_path / "out.lit"
    code, out = run(tmp_path, _UNANNOTATED, dest=str(dest))
    assert code == 0
    assert "CANNOT TRANSCRIBE" not in out
    assert dest.read_text() == "rite greet(name):\n    render name\n"


def test_the_output_is_warned_to_need_archetypes(tmp_path):
    dest = tmp_path / "out.lit"
    _, out = run(tmp_path, _UNANNOTATED, dest=str(dest))
    assert "WILL NOT CHANT AS WRITTEN" in out
    # The exact fault and its line, so the reader need not go looking.
    assert "name is unsanctioned" in out
    assert ":1" in out
    # And what to do about it, in both scopes.
    assert "unsanctioned" in out and "archetype" in out


def test_nothing_is_prepended_to_the_output(tmp_path):
    # An `unsanctioned` line ahead of the litany was the obvious fix and it
    # is wrong: it breaks transcribe's own round-trip self-check, which is
    # the guarantee that makes the verb trustworthy.
    dest = tmp_path / "out.lit"
    run(tmp_path, _UNANNOTATED, dest=str(dest))
    assert not dest.read_text().startswith("unsanctioned")


def test_a_source_that_was_annotated_in_python_is_not_warned_about(tmp_path):
    # The warning is earned, not blanket: annotated Python transcribes to a
    # litany that chants as written, and saying otherwise would be a lie.
    dest = tmp_path / "out.lit"
    code, out = run(tmp_path, _ANNOTATED, dest=str(dest))
    assert code == 0
    assert "WILL NOT CHANT" not in out
    assert dest.read_text() == "rite greet(name: str) -> str:\n    render name\n"


def test_the_archetype_warning_goes_to_stderr_in_stdout_mode(tmp_path, capsys):
    code, out = run(tmp_path, _UNANNOTATED)
    assert code == 0
    assert out == "rite greet(name):\n    render name\n"
    assert "WILL NOT CHANT" in capsys.readouterr().err


def test_the_backstop_still_refuses_a_structural_impossibility(tmp_path):
    # Suppressing the archetype rule must suppress nothing else. These are
    # shapes that are not Liturgy at all -- no annotation saves them -- and
    # the backstop exists for exactly them.
    for source in ("consecrated = 5\n", "def __litany__(n):\n    return n\n"):
        code, out = run(tmp_path, source)
        assert code == 1, source
        assert "CANNOT TRANSCRIBE" in out


def test_the_transcribe_then_augur_workflow_names_the_archetypes(tmp_path):
    # `augur` is how the user finds out, and it is unchanged: the rule lives
    # on the compile path, so the verb reports it without a line of its own.
    from liturgy.tooling import augur

    dest = tmp_path / "out.lit"
    assert run(tmp_path, _UNANNOTATED, dest=str(dest))[0] == 0
    buf = io.StringIO()
    assert augur([str(dest)], out=buf) == 1
    assert "every parameter must declare its archetype" in buf.getvalue()


def test_augur_is_content_once_the_archetypes_are_declared(tmp_path):
    from liturgy.tooling import augur

    dest = tmp_path / "out.lit"
    assert run(tmp_path, _ANNOTATED, dest=str(dest))[0] == 0
    buf = io.StringIO()
    assert augur([str(dest)], out=buf) == 0
