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


def test_chant_restores_main_module_and_argv_on_success(tmp_path):
    # In-process (unlike the subprocess tests above), so it actually
    # exercises whether chant leaves process-global state clean afterwards.
    script = tmp_path / "quiet.lit"
    script.write_text("VALUE = 1\n")
    before_main = sys.modules.get("__main__")
    before_argv = list(sys.argv)

    loader.chant(str(script), ["ignored"])

    assert sys.modules.get("__main__") is before_main
    assert sys.argv == before_argv


def test_chant_restores_main_module_and_argv_after_exception(tmp_path):
    # Same as above, but confirms the cleanup also happens when the prayer
    # raises, and that the exception is not swallowed along the way.
    script = tmp_path / "boom.lit"
    script.write_text("raise ValueError('boom')\n")
    before_main = sys.modules.get("__main__")
    before_argv = list(sys.argv)

    with pytest.raises(ValueError):
        loader.chant(str(script), [])

    assert sys.modules.get("__main__") is before_main
    assert sys.argv == before_argv


# Regression: I2 — chant and the import hook must decode a file the same way.
# A UTF-8 BOM and a PEP 263 `coding:` cookie both imported fine and both
# refused to chant, because chant read the bytes as plain UTF-8.
ENCODED: list[tuple[str, bytes, str]] = [
    ("bom", 'intone("bom ok")\n'.encode("utf-8-sig"), "bom ok"),
    (
        "cookie",
        '# -*- coding: latin-1 -*-\nintone("caf\xe9")\n'.encode("latin-1"),
        "caf\xe9",
    ),
]


@pytest.mark.parametrize("name,data,expected", ENCODED, ids=[e[0] for e in ENCODED])
def test_chant_decodes_like_the_import_hook(tmp_path, name, data, expected):
    script = tmp_path / f"{name}.lit"
    script.write_bytes(data)
    out = subprocess.run(
        [sys.executable, "-c",
         f"from liturgy.loader import chant; chant({str(script)!r}, [])"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == expected


@pytest.mark.parametrize("name,data,expected", ENCODED, ids=[e[0] for e in ENCODED])
def test_import_decodes_bom_and_coding_cookie(tmp_path, name, data, expected):
    (tmp_path / f"{name}_imp.lit").write_bytes(data)
    out = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, {str(tmp_path)!r});"
         f" from liturgy import loader; loader.install(); import {name}_imp"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == expected


# Regression: I3 — `python file.py` prepends the script's directory to
# sys.path and chant must too, or a multi-file Liturgy program cannot be run
# through the console script from anywhere but its own directory.
def test_chant_puts_the_script_directory_on_sys_path(tmp_path):
    shrine = tmp_path / "shrine"
    shrine.mkdir()
    (shrine / "relic.lit").write_text('GREETING = "ave"\n')
    (shrine / "main.lit").write_text(
        "within relic invoke GREETING\nintone(GREETING)\n"
    )
    out = subprocess.run(
        [sys.executable, "-m", "liturgy", "chant", "shrine/main.lit"],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "ave"


def test_chant_restores_sys_path(tmp_path):
    script = tmp_path / "quiet2.lit"
    script.write_text("VALUE = 1\n")
    before = list(sys.path)

    loader.chant(str(script), [])

    assert sys.path == before


# Regression: I6 — an unclosed bracket must reach both callers as a located
# SyntaxError, not as a raw tokenize.TokenError with no filename.
def test_chant_reports_an_unclosed_bracket_as_a_located_syntax_error(tmp_path):
    script = tmp_path / "synerr.lit"
    script.write_text('intone("a")\nintone(1 +\n')
    with pytest.raises(SyntaxError) as info:
        loader.chant(str(script), [])
    assert info.value.filename == str(script)
    assert info.value.lineno == 2
    assert "never closed" in info.value.msg


def test_import_reports_an_unclosed_bracket_as_a_located_syntax_error(
    tmp_path, monkeypatch
):
    (tmp_path / "synerrimp.lit").write_text("x = [1,\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    loader.install()
    with pytest.raises(SyntaxError) as info:
        import synerrimp  # noqa: F401
    assert info.value.filename.endswith("synerrimp.lit")
    assert "never closed" in info.value.msg
