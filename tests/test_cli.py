import os
import subprocess
import sys

import pytest

from liturgy import cli


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.delenv("LITURGY_PIOUS", raising=False)


@pytest.fixture
def prayer(tmp_path):
    p = tmp_path / "hello.lit"
    p.write_text('intone("Ave Omnissiah")\n')
    return p


def run_cli(args, **env):
    return subprocess.run(
        [sys.executable, "-m", "liturgy", *args],
        capture_output=True,
        text=True,
        env={**os.environ, **env},
    )


def test_chant_runs_a_prayer(prayer):
    out = run_cli(["chant", str(prayer)])
    assert out.returncode == 0
    assert out.stdout.strip() == "Ave Omnissiah"
    assert out.stderr == ""


def test_heretical_alias_still_works(prayer):
    out = run_cli(["run", str(prayer)])
    assert out.returncode == 0
    assert out.stdout.strip() == "Ave Omnissiah"


def test_heretical_alias_rebukes_on_stderr_only(prayer):
    out = run_cli(["run", str(prayer)])
    assert "TECH-HERESY DETECTED" in out.stderr
    assert "TECH-HERESY" not in out.stdout


def test_heresy_does_not_change_the_exit_code(prayer):
    assert run_cli(["run", str(prayer)]).returncode == 0


def test_absolved_silences_the_rebuke(prayer):
    out = run_cli(["--absolved", "run", str(prayer)])
    assert "TECH-HERESY" not in out.stderr


def test_pious_zero_silences_the_rebuke(prayer):
    out = run_cli(["run", str(prayer)], LITURGY_PIOUS="0")
    assert "TECH-HERESY" not in out.stderr


def test_failing_prayer_renders_a_machine_curse(tmp_path):
    bad = tmp_path / "bad.lit"
    bad.write_text("intone(1 / 0)\n")
    out = run_cli(["chant", str(bad)])
    assert out.returncode != 0
    assert "MACHINE CURSE" in out.stderr
    assert "DivisionByTheVoid" in out.stderr


def test_profane_gives_a_plain_traceback(tmp_path):
    bad = tmp_path / "bad.lit"
    bad.write_text("intone(1 / 0)\n")
    out = run_cli(["--profane", "chant", str(bad)])
    assert "MACHINE CURSE" not in out.stderr
    assert "ZeroDivisionError" in out.stderr


def test_profane_env_var_also_gives_a_plain_traceback(tmp_path):
    bad = tmp_path / "bad.lit"
    bad.write_text("intone(1 / 0)\n")
    out = run_cli(["chant", str(bad)], LITURGY_PROFANE="1")
    assert "MACHINE CURSE" not in out.stderr
    assert "ZeroDivisionError" in out.stderr


def test_reserved_verbs_are_declared():
    # Spec III owns these; Core must not hand the names to anything else.
    # augur, transcribe, purge, forge, consecrate and prove have since
    # graduated to real subparsers, so they are no longer merely reserved.
    assert cli.RESERVED_VERBS == {"sanctify", "anoint"}
    built = ("augur", "transcribe", "purge", "forge", "consecrate", "prove")
    for verb in built:
        assert verb not in cli.RESERVED_VERBS


def test_an_unknown_verb_is_rejected(prayer):
    # RESERVED_VERBS reserves nothing mechanically; argparse does the work.
    # `sanctify` is still reserved and unbuilt, so it is the live example.
    out = run_cli(["sanctify", str(prayer)])
    assert out.returncode != 0
    assert "invalid choice" in out.stderr


def test_the_global_flags_are_offered_on_the_verbs_too():
    out = run_cli(["chant", "--help"])
    assert "--absolved" in out.stdout
    assert "--profane" in out.stdout
