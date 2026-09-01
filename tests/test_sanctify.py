"""The sanctify verb."""

from __future__ import annotations

import io

from liturgy.tooling import sanctify

MESSY = "rite f():\n  render 1   \n\n\n\n\n"
TIDY = "rite f():\n    render 1\n"


def run(root, **kw):
    buf = io.StringIO()
    return sanctify([str(root)], out=buf, **kw), buf.getvalue()


def test_it_sets_a_litany_in_order(tmp_path):
    p = tmp_path / "prayer.lit"
    p.write_text(MESSY)
    code, out = run(tmp_path)
    assert code == 0
    assert p.read_text() == TIDY
    assert "1 sanctified" in out


def test_a_litany_already_in_order_is_left_alone(tmp_path):
    p = tmp_path / "prayer.lit"
    p.write_text(TIDY)
    before = p.stat().st_mtime_ns
    code, out = run(tmp_path)
    assert code == 0
    assert "0 sanctified, 1 already in order" in out
    assert p.stat().st_mtime_ns == before, "an unchanged file must not be rewritten"


def test_check_reports_without_writing(tmp_path):
    p = tmp_path / "prayer.lit"
    p.write_text(MESSY)
    code, out = run(tmp_path, check=True)
    assert code == 1
    assert "unclean" in out
    assert p.read_text() == MESSY, "--check must not touch the file"


def test_check_is_quiet_and_zero_when_all_is_in_order(tmp_path):
    (tmp_path / "prayer.lit").write_text(TIDY)
    code, out = run(tmp_path, check=True)
    assert code == 0
    assert "0 unclean, 1 already in order" in out


def test_python_files_are_left_to_their_own_tools(tmp_path):
    py = tmp_path / "plain.py"
    py.write_text("def f():\n  return 1   \n")
    (tmp_path / "prayer.lit").write_text(MESSY)
    code, out = run(tmp_path)
    assert code == 0
    assert py.read_text() == "def f():\n  return 1   \n"
    assert "1 sanctified" in out


def test_an_unparseable_litany_is_refused_and_untouched(tmp_path):
    p = tmp_path / "broken.lit"
    p.write_text("rite (:\n")
    code, out = run(tmp_path)
    assert code == 1
    assert "CANNOT SANCTIFY" in out
    assert p.read_text() == "rite (:\n"


def test_one_refusal_does_not_stop_the_others(tmp_path):
    (tmp_path / "aaa.lit").write_text("rite (:\n")
    (tmp_path / "zzz.lit").write_text(MESSY)
    code, out = run(tmp_path)
    assert code == 1
    assert (tmp_path / "zzz.lit").read_text() == TIDY


def test_crlf_line_endings_are_preserved(tmp_path):
    p = tmp_path / "prayer.lit"
    p.write_bytes(b"rite f():\r\n  render 1   \r\n")
    assert run(tmp_path)[0] == 0
    assert p.read_bytes() == b"rite f():\r\n    render 1\r\n"


def test_the_source_encoding_is_preserved(tmp_path):
    p = tmp_path / "prayer.lit"
    p.write_bytes("# -*- coding: latin-1 -*-\nx = 'caf\xe9'   \n".encode("latin-1"))
    assert run(tmp_path)[0] == 0
    raw = p.read_bytes()
    assert b"caf\xe9" in raw, "re-encoded as UTF-8 under a latin-1 cookie"
    assert not raw.rstrip().endswith(b"   ")


def test_nothing_to_do_is_not_a_failure(tmp_path):
    code, out = run(tmp_path)
    assert code == 0
    assert "no litanies" in out
