import io
import json

import pytest

from liturgy.tooling import purge


def test_it_removes_pycache_directories(tmp_path):
    (tmp_path / "prayer.lit").write_text("intone(1)\n")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "prayer.cpython-312.pyc").write_bytes(b"\x00")
    nested = tmp_path / "sub" / "__pycache__"
    nested.mkdir(parents=True)
    (nested / "x.pyc").write_bytes(b"\x00")

    buf = io.StringIO()
    assert purge(root=str(tmp_path), out=buf) == 0
    assert not cache.exists() and not nested.exists()
    assert "__pycache__" in buf.getvalue()


def test_it_refuses_outside_a_liturgy_project(tmp_path):
    # No .lit file anywhere: a recursive delete here is somebody's mistake.
    (tmp_path / "__pycache__").mkdir()
    buf = io.StringIO()
    assert purge(root=str(tmp_path), out=buf) == 1
    assert (tmp_path / "__pycache__").exists()
    assert "does not look like" in buf.getvalue()


def test_it_leaves_other_directories_alone(tmp_path):
    (tmp_path / "prayer.lit").write_text("intone(1)\n")
    keep = tmp_path / "src"
    keep.mkdir()
    (keep / "thing.py").write_text("x = 1\n")
    assert purge(root=str(tmp_path), out=io.StringIO()) == 0
    assert (keep / "thing.py").exists()


def test_it_does_not_follow_symlinks(tmp_path):
    # The symlink must be NAMED __pycache__: rglob matches on name, so a
    # link called anything else is never yielded and the guard under test
    # is never reached.
    project = tmp_path / "forge"
    project.mkdir()
    (project / "prayer.lit").write_text("intone(1)\n")
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "precious.pyc").write_bytes(b"\x00")
    try:
        (project / "__pycache__").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")

    assert purge(root=str(project), out=io.StringIO()) == 0
    assert (outside / "precious.pyc").exists(), "followed a symlink"
    assert (project / "__pycache__").is_symlink(), "removed the link itself"


def test_heresies_clears_the_state_file(tmp_path, monkeypatch):
    (tmp_path / "prayer.lit").write_text("intone(1)\n")
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    from liturgy import heresy

    state = heresy.state_path()
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({"run": 3}))

    buf = io.StringIO()
    assert purge(heresies=True, root=str(tmp_path), out=buf) == 0
    assert not state.exists()
    assert str(state) in buf.getvalue(), "the full path is reported before deletion"


def test_heresies_is_quiet_when_there_is_nothing_to_clear(tmp_path, monkeypatch):
    (tmp_path / "prayer.lit").write_text("intone(1)\n")
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    assert purge(heresies=True, root=str(tmp_path), out=io.StringIO()) == 0
