import pathlib
import subprocess
import sys

EXAMPLES = pathlib.Path(__file__).parent.parent / "examples"


def test_fibonacci_example_runs():
    out = subprocess.run(
        [sys.executable, "-m", "liturgy", "chant", str(EXAMPLES / "fibonacci.lit")],
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stderr
    assert "55" in out.stdout


def test_bad_example_raises_division_curse():
    out = subprocess.run(
        [sys.executable, "-m", "liturgy", "chant", str(EXAMPLES / "bad.lit")],
        capture_output=True,
        text=True,
    )
    assert out.returncode != 0
    assert "MACHINE CURSE" in out.stderr
    assert "DivisionByTheVoid" in out.stderr


def test_constructs_example_runs():
    out = subprocess.run(
        [sys.executable, "-m", "liturgy", "chant",
         str(EXAMPLES / "constructs.lit")],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    assert "the omens forbid it" in out.stdout
    assert "attempts: 3" in out.stdout


def test_augur_catches_the_quiet_shadowing_the_docs_warn_about(tmp_path):
    # Chapter XI names `span = ...` as the quiet trap. This is the verb
    # that finds it, so the two must actually agree.
    p = tmp_path / "quiet.lit"
    p.write_text('span = "text range"\nintone(span)\n')
    out = subprocess.run(
        [sys.executable, "-m", "liturgy", "augur", "--plain", str(p)],
        capture_output=True, text=True,
    )
    assert out.returncode == 1
    assert "span is reserved" in out.stdout
