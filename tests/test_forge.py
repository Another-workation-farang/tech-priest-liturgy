"""The forge verb: bytecode written ahead of the first import."""

from __future__ import annotations

import importlib.util
import io
import pathlib
import sys

import pytest

from liturgy.tooling import forge


def _cache(p: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(importlib.util.cache_from_source(str(p)))


def test_it_writes_bytecode_beside_the_litany(tmp_path):
    p = tmp_path / "prayer.lit"
    p.write_text('rite greet() -> str:\n    render "ave"\n')

    buf = io.StringIO()
    assert forge([str(tmp_path)], out=buf) == 0
    assert _cache(p).exists(), "no bytecode written"
    assert "1 litany forged" in buf.getvalue()


def test_it_does_not_execute_what_it_forges(tmp_path, capsys):
    # The whole point of forging over importing: the module's top level
    # must not run. A litany that prints would betray it.
    p = tmp_path / "loud.lit"
    p.write_text('intone("SIDE EFFECT")\n')

    buf = io.StringIO()
    assert forge([str(tmp_path)], out=buf) == 0
    assert "SIDE EFFECT" not in capsys.readouterr().out
    assert "SIDE EFFECT" not in buf.getvalue()


def test_the_forged_bytecode_is_what_import_actually_uses(tmp_path, monkeypatch):
    # A forge whose output the import system ignores is theatre. Spy on the
    # compile step: a cache hit never reaches it.
    from liturgy.loader import LiturgyLoader, install

    p = tmp_path / "cached.lit"
    p.write_text('rite greet() -> str:\n    render "ave"\n')
    assert forge([str(p)], out=io.StringIO()) == 0

    calls = []
    original = LiturgyLoader.source_to_code

    def spy(self, data, path, *, _optimize=-1):
        calls.append(path)
        return original(self, data, path, _optimize=_optimize)

    monkeypatch.setattr(LiturgyLoader, "source_to_code", spy)
    install()
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, "cached", raising=False)

    import cached

    assert cached.greet() == "ave"
    assert calls == [], "the forged bytecode was ignored and it recompiled"


def test_a_second_forge_reports_the_litany_already_current(tmp_path):
    p = tmp_path / "prayer.lit"
    p.write_text('rite greet() -> str:\n    render "ave"\n')
    assert forge([str(p)], out=io.StringIO()) == 0

    buf = io.StringIO()
    assert forge([str(p)], out=buf) == 0
    report = buf.getvalue()
    assert "1 already current" in report
    assert "1 litany forged" not in report


def test_anew_recompiles_a_litany_that_is_already_current(tmp_path):
    p = tmp_path / "prayer.lit"
    p.write_text('rite greet() -> str:\n    render "ave"\n')
    assert forge([str(p)], out=io.StringIO()) == 0

    buf = io.StringIO()
    assert forge([str(p)], anew=True, out=buf) == 0
    assert "1 litany forged" in buf.getvalue()


def test_an_edited_litany_is_forged_again(tmp_path):
    p = tmp_path / "prayer.lit"
    p.write_text('rite greet() -> str:\n    render "ave"\n')
    assert forge([str(p)], out=io.StringIO()) == 0
    # A rewrite changes size, which invalidates the cache regardless of
    # filesystem mtime granularity.
    p.write_text('rite greet() -> str:\n    render "ave, Omnissiah"\n')

    buf = io.StringIO()
    assert forge([str(p)], out=buf) == 0
    assert "1 litany forged" in buf.getvalue()


def test_a_broken_litany_is_reported_and_does_not_stop_the_others(tmp_path):
    (tmp_path / "aaa.lit").write_text('rite a() -> int:\n    render 1\n')
    (tmp_path / "mmm.lit").write_text("render 1\n")  # return outside function
    (tmp_path / "zzz.lit").write_text('rite z() -> int:\n    render 2\n')

    buf = io.StringIO()
    assert forge([str(tmp_path)], out=buf) == 1
    report = buf.getvalue()
    assert "mmm.lit" in report and "CANNOT FORGE" in report
    assert _cache(tmp_path / "aaa.lit").exists()
    assert _cache(tmp_path / "zzz.lit").exists(), "one failure ended the walk"
    assert not _cache(tmp_path / "mmm.lit").exists()


def test_it_leaves_python_files_alone(tmp_path):
    # .py -> .pyc is compileall's job; forging it would add nothing and
    # would claim ground that is not ours.
    py = tmp_path / "plain.py"
    py.write_text("x = 1\n")
    lit = tmp_path / "prayer.lit"
    lit.write_text('rite greet() -> str:\n    render "ave"\n')

    buf = io.StringIO()
    assert forge([str(tmp_path)], out=buf) == 0
    assert _cache(lit).exists()
    assert not _cache(py).exists()
    assert "1 litany forged" in buf.getvalue()


def test_it_refuses_when_the_interpreter_will_not_write_bytecode(tmp_path, monkeypatch):
    # -B / PYTHONDONTWRITEBYTECODE makes every write a silent no-op. Forging
    # would report success and produce nothing.
    p = tmp_path / "prayer.lit"
    p.write_text('rite greet() -> str:\n    render "ave"\n')
    monkeypatch.setattr(sys, "dont_write_bytecode", True)

    buf = io.StringIO()
    assert forge([str(p)], out=buf) == 1
    assert "will not write bytecode" in buf.getvalue()
    assert not _cache(p).exists()


def test_an_unreadable_litany_is_reported_not_raised(tmp_path):
    p = tmp_path / "gone.lit"
    p.symlink_to(tmp_path / "nowhere.lit")

    buf = io.StringIO()
    assert forge([str(p)], out=buf) == 1
    assert "CANNOT FORGE" in buf.getvalue()


def test_a_litany_whose_cache_cannot_be_written_is_reported(tmp_path, monkeypatch):
    p = tmp_path / "prayer.lit"
    p.write_text('rite greet() -> str:\n    render "ave"\n')

    from liturgy.loader import LiturgyLoader

    def refuse(self, *a, **k):
        raise OSError(13, "Permission denied")

    monkeypatch.setattr(LiturgyLoader, "get_code", refuse)

    buf = io.StringIO()
    assert forge([str(p)], out=buf) == 1
    assert "CANNOT FORGE" in buf.getvalue()
    assert "Permission denied" in buf.getvalue()


def test_nothing_to_forge_is_not_a_failure(tmp_path):
    buf = io.StringIO()
    assert forge([str(tmp_path)], out=buf) == 0
    assert "no litanies" in buf.getvalue()


def test_the_default_root_is_the_working_directory(tmp_path, monkeypatch):
    p = tmp_path / "prayer.lit"
    p.write_text('rite greet() -> str:\n    render "ave"\n')
    monkeypatch.chdir(tmp_path)

    buf = io.StringIO()
    assert forge([], out=buf) == 0
    assert _cache(p).exists()
