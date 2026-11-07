import io
import os
import shutil
import subprocess

import pytest
from conftest import OMENS, chant_run, normalise

from liturgy import tooling

EXE = "hymn.exe" if os.name == "nt" else "hymn"


def fake_build(calls):
    def build(entry, output):
        calls.append((entry, output, sorted(p.name for p in entry.parent.iterdir())))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"MZ")
        return 0
    return build


def test_refuses_without_nuitka(monkeypatch, codex):
    monkeypatch.setattr(tooling, "nuitka_available", lambda: False)
    buf = io.StringIO()
    assert tooling.anoint(str(codex / "hymn.lit"), out=buf) == 1
    assert buf.getvalue() == ("++ CANNOT ANOINT: nuitka is not installed ++\n"
                              "   anointing needs it:  pip install 'liturgy[anoint]'\n")


def test_writes_the_executable_beside_the_litany_and_nothing_else(codex):
    before = sorted(p.name for p in codex.iterdir())
    calls = []
    assert tooling.anoint(str(codex / "hymn.lit"), out=io.StringIO(), build=fake_build(calls)) == 0
    assert sorted(p.name for p in codex.iterdir()) == sorted(before + [EXE])
    assert "__liturgy_curse.py" in calls[0][2] and calls[0][0].name == "hymn.py"
    assert not calls[0][0].parent.exists()  # staging removed


def test_out_flag_places_it_elsewhere(codex, tmp_path):
    (tmp_path / "bin").mkdir()
    dest = tmp_path / "bin" / "x"
    assert tooling.anoint(str(codex / "hymn.lit"), str(dest), out=io.StringIO(), build=fake_build([])) == 0
    assert dest.read_bytes() == b"MZ"
    assert not (codex / EXE).exists()


def test_reanointing_replaces_the_old_executable(codex):
    dest = codex / EXE
    dest.write_bytes(b"old")
    assert tooling.anoint(str(codex / "hymn.lit"), out=io.StringIO(), build=fake_build([])) == 0
    assert dest.read_bytes() == b"MZ"


def test_relative_entry_from_another_cwd(codex, monkeypatch):
    monkeypatch.chdir(codex.parent)
    assert tooling.anoint(f"{codex.name}/hymn.lit", out=io.StringIO(), build=fake_build([])) == 0
    assert (codex / EXE).read_bytes() == b"MZ"


def test_an_uncompilable_litany_anywhere_refuses(codex):
    (codex / "bad.lit").write_text("rite (:\n")
    buf = io.StringIO()
    assert tooling.anoint(str(codex / "hymn.lit"), out=buf, build=fake_build([])) == 1
    assert "CANNOT ANOINT: bad.lit line 1" in buf.getvalue()
    assert not (codex / EXE).exists()


def test_a_failed_build_refuses_and_cleans_up(codex):
    staged = []

    def build(entry, output):
        staged.append(entry.parent)
        return 2

    buf = io.StringIO()
    assert tooling.anoint(str(codex / "hymn.lit"), out=buf, build=build) == 1
    assert "nuitka failed (exit 2)" in buf.getvalue()
    assert not (codex / EXE).exists()
    assert not staged[0].exists()


def test_a_build_that_writes_nothing_refuses(codex):
    buf = io.StringIO()
    assert tooling.anoint(str(codex / "hymn.lit"), out=buf, build=lambda e, o: 0) == 1
    assert "nuitka failed (exit 0)" in buf.getvalue()


def test_refuses_a_missing_file_and_a_python_file(tmp_path):
    py = tmp_path / "a.py"
    py.write_text("")
    for path, msg in ((tmp_path / "nope.lit", "does not exist"), (py, "is not a litany")):
        buf = io.StringIO()
        assert tooling.anoint(str(path), out=buf, build=fake_build([])) == 1
        assert buf.getvalue() == f"++ CANNOT ANOINT: {path} {msg} ++\n"


def test_a_missing_output_directory_refuses(codex, tmp_path):
    buf = io.StringIO()
    dest = tmp_path / "nowhere" / "x"
    assert tooling.anoint(str(codex / "hymn.lit"), str(dest), out=buf, build=fake_build([])) == 1
    assert buf.getvalue() == f"++ CANNOT ANOINT: {dest.parent} does not exist ++\n"


def test_status_lines(codex):
    buf = io.StringIO()
    assert tooling.anoint(str(codex / "hymn.lit"), out=buf, build=fake_build([])) == 0
    lines = buf.getvalue().splitlines()
    assert lines[0] == "++ ANOINTING hymn.lit ++"
    assert lines[1].endswith(" litanies rendered; the machine tongue is being forged")
    assert lines[2] == f"++ hymn.lit IS ANOINTED: {codex / EXE} ++"


needs_nuitka = pytest.mark.skipif(
    not tooling.nuitka_available() and not os.environ.get("LITURGY_REQUIRE_NUITKA"),
    reason="needs liturgy[anoint]")


@needs_nuitka
@pytest.mark.slow
def test_an_anointed_executable_curses_like_chant(codex, tmp_path):
    expected = {o: normalise(chant_run(codex, o).stderr, codex) for o in OMENS}
    clean = chant_run(codex, "").stdout
    shipped = tmp_path / "elsewhere"
    shipped.mkdir()
    dest = shipped / EXE
    assert tooling.anoint(str(codex / "hymn.lit"), str(dest)) == 0
    shutil.rmtree(codex)  # the sources are gone; only the executable remains
    for omen in OMENS:
        assert subprocess.run([str(dest), omen], cwd=shipped, capture_output=True, text=True).stderr == expected[omen]
    run = subprocess.run([str(dest), ""], cwd=shipped, capture_output=True, text=True)
    assert run.returncode == 0 and run.stdout == clean
