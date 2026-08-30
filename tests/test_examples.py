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
