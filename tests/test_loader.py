import subprocess
import sys
import textwrap

import pytest

from liturgy import loader

PRAYER = textwrap.dedent(
    """\
    GREETING = "Ave Omnissiah"


    rite greet(name):
        render f"{GREETING}, {name}"
    """
)


@pytest.fixture
def prayer_dir(tmp_path, monkeypatch):
    (tmp_path / "prayer.lit").write_text(PRAYER)
    monkeypatch.syspath_prepend(str(tmp_path))
    loader.install()
    yield tmp_path


def test_imports_a_lit_module(prayer_dir):
    import prayer

    assert prayer.greet("Magos") == "Ave Omnissiah, Magos"


def test_get_source_returns_original_liturgy(prayer_dir):
    import prayer

    assert "rite greet" in prayer.__loader__.get_source("prayer")


def test_install_is_idempotent():
    before = len(sys.path_hooks)
    loader.install()
    loader.install()
    assert len(sys.path_hooks) == before


def test_normal_python_imports_still_work(tmp_path, monkeypatch):
    # Regression: a path hook registered without the default loader details
    # shadows the stdlib FileFinder and breaks every .py import.
    (tmp_path / "plain_mod.py").write_text("VALUE = 42\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    loader.install()
    import plain_mod

    assert plain_mod.VALUE == 42


def test_chant_runs_as_main(tmp_path):
    script = tmp_path / "main.lit"
    script.write_text('intone("chanted")\nintone(__name__)\n')
    out = subprocess.run(
        [sys.executable, "-c",
         f"from liturgy.loader import chant; chant({str(script)!r}, [])"],
        capture_output=True, text=True, check=True,
    )
    assert out.stdout.splitlines() == ["chanted", "__main__"]


def test_chant_passes_argv(tmp_path):
    script = tmp_path / "args.lit"
    script.write_text("invoke sys\nintone(sys.argv[1])\n")
    out = subprocess.run(
        [sys.executable, "-c",
         f"from liturgy.loader import chant; chant({str(script)!r}, ['omnissiah'])"],
        capture_output=True, text=True, check=True,
    )
    assert out.stdout.strip() == "omnissiah"
