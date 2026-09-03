"""The prove verb: pytest, with the hook installed and .lit collected."""

from __future__ import annotations

import io
import subprocess
import sys

import pytest

from liturgy.tooling import prove

PASSING = "rite test_pleased() -> Void:\n    attest 1 + 1 == 2\n"
FAILING = "rite test_displeased() -> Void:\n    attest measure('cog') == 99\n"


def run_cli(cwd, *args):
    return subprocess.run(
        [sys.executable, "-m", "liturgy", "prove", *args],
        cwd=cwd, capture_output=True, text=True,
    )


def test_it_collects_and_passes_a_litany_of_trials(tmp_path):
    (tmp_path / "test_rites.lit").write_text(PASSING)
    r = run_cli(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "1 passed" in r.stdout


def test_a_failing_trial_fails_the_run(tmp_path):
    (tmp_path / "test_rites.lit").write_text(FAILING)
    r = run_cli(tmp_path)
    assert r.returncode == 1
    assert "1 failed" in r.stdout


def test_the_failure_quotes_liturgy_not_generated_python(tmp_path):
    # The whole reason the hook does not override get_source. If this ever
    # shows `def` or `return`, the traceback story has broken.
    (tmp_path / "test_rites.lit").write_text(FAILING)
    r = run_cli(tmp_path)
    assert "rite test_displeased" in r.stdout
    assert "attest measure('cog') == 99" in r.stdout
    assert "test_rites.lit:2" in r.stdout
    assert "def test_displeased" not in r.stdout


def test_it_needs_no_conftest(tmp_path):
    (tmp_path / "test_rites.lit").write_text(PASSING)
    assert not (tmp_path / "conftest.py").exists()
    r = run_cli(tmp_path)
    assert r.returncode == 0, "the whole point: no boilerplate"


def test_a_litany_that_is_not_a_trial_is_not_collected(tmp_path):
    (tmp_path / "helper.lit").write_text("rite test_looks_like_one() -> Void:\n    attest 0\n")
    (tmp_path / "test_rites.lit").write_text(PASSING)
    r = run_cli(tmp_path)
    assert r.returncode == 0
    assert "1 passed" in r.stdout


def test_python_trials_still_run_alongside(tmp_path):
    (tmp_path / "test_rites.lit").write_text(PASSING)
    (tmp_path / "test_plain.py").write_text("def test_plain():\n    assert True\n")
    r = run_cli(tmp_path)
    assert "2 passed" in r.stdout


def test_a_trial_may_import_a_litany(tmp_path):
    # Proof the hook is installed, not just that .lit files are collected.
    (tmp_path / "helper.lit").write_text('rite greet() -> str:\n    render "ave"\n')
    (tmp_path / "test_rites.lit").write_text(
        "invoke helper\n\nrite test_imported() -> Void:\n    attest helper.greet() == 'ave'\n"
    )
    r = run_cli(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_arguments_are_passed_through_to_pytest(tmp_path):
    (tmp_path / "test_rites.lit").write_text(
        PASSING + "\nrite test_other() -> Void:\n    attest 1\n"
    )
    r = run_cli(tmp_path, "-k", "pleased")
    assert r.returncode == 0
    assert "1 passed" in r.stdout and "1 deselected" in r.stdout


def test_a_named_path_is_honoured(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "test_rites.lit").write_text(PASSING)
    (tmp_path / "test_other.lit").write_text(FAILING)
    r = run_cli(tmp_path, "sub")
    assert r.returncode == 0, "only the named path should have run"


def test_no_trials_found_is_reported_not_a_crash(tmp_path):
    r = run_cli(tmp_path)
    # pytest's own "no tests ran" code, passed through rather than flattened.
    assert r.returncode == 5
    assert "no trials" in r.stdout.lower() or "no tests ran" in r.stdout


def test_it_refuses_cleanly_when_pytest_is_absent(monkeypatch):
    # pytest is an optional extra; the verb must say so rather than
    # tracebacking on the import.
    import builtins

    real = builtins.__import__

    def no_pytest(name, *a, **k):
        if name == "pytest":
            raise ImportError("No module named 'pytest'")
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_pytest)
    buf = io.StringIO()
    assert prove([], out=buf) == 1
    report = buf.getvalue()
    assert "CANNOT PROVE" in report
    assert "pytest" in report
    assert "liturgy[trials]" in report
