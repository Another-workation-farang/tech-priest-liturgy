import importlib
import io
import json
import linecache
import os
import subprocess
import sys
import textwrap
import threading
from pathlib import Path

import pytest

from liturgy import curse, loader

BROKEN = textwrap.dedent(
    """\
    rite invoke_spirit(tome):
        render tome / 0
    """
)


@pytest.fixture(autouse=True)
def _restore_hooks():
    # install()/uninstall() mutate process-global state. Guard every test in
    # this module so a themed hook never leaks into the rest of the suite,
    # even if a test fails partway through.
    orig_excepthook = sys.excepthook
    orig_thread_hook = threading.excepthook
    yield
    sys.excepthook = orig_excepthook
    threading.excepthook = orig_thread_hook


@pytest.fixture
def broken(tmp_path, monkeypatch):
    (tmp_path / "broken.lit").write_text(BROKEN)
    monkeypatch.syspath_prepend(str(tmp_path))
    loader.install()
    import broken as mod

    return mod


def capture(exc_info):
    buf = io.StringIO()
    curse.render_curse(*exc_info, file=buf)
    return buf.getvalue()


def test_exception_name_is_themed():
    assert curse.curse_name(ZeroDivisionError) == "DivisionByTheVoid"
    assert curse.curse_name(KeyError) == "LostPattern"


def test_unmapped_exception_keeps_its_name():
    class Bespoke(Exception):
        pass

    assert curse.curse_name(Bespoke) == "Bespoke"


def test_rendered_curse_has_the_frame_and_theme(broken):
    try:
        broken.invoke_spirit(1)
    except ZeroDivisionError:
        out = capture(sys.exc_info())
    assert "++ MACHINE CURSE ++" in out
    assert "broken.lit" in out
    assert "line 2" in out
    assert "DivisionByTheVoid" in out


def test_rendered_curse_shows_liturgy_source_not_generated_python(broken):
    try:
        broken.invoke_spirit(1)
    except ZeroDivisionError:
        out = capture(sys.exc_info())
    assert "render tome / 0" in out
    assert "return tome / 0" not in out


def test_library_frames_are_not_themed(broken):
    # A frame from a .py file must render with its real path and no ++ banner
    # on that line.
    try:
        broken.invoke_spirit(1)
    except ZeroDivisionError:
        out = capture(sys.exc_info())
    assert out.count("++ MACHINE CURSE ++") == 1


def test_hook_never_raises_even_with_a_broken_map(broken, monkeypatch):
    monkeypatch.setattr(
        curse, "_map_for", lambda path: (_ for _ in ()).throw(RuntimeError())
    )
    try:
        broken.invoke_spirit(1)
    except ZeroDivisionError:
        exc_info = sys.exc_info()
    buf = io.StringIO()
    # Must not propagate; falls back to the stdlib hook (which writes to
    # sys.stderr, so buf may stay empty). The assertion is that it returns.
    curse.render_curse(*exc_info, file=buf)


def test_deleted_source_file_degrades_gracefully(tmp_path, monkeypatch):
    # Import succeeds, then the .lit file vanishes before the curse renders,
    # and -- to genuinely exercise the "nothing was recorded" fallback path
    # rather than the recorded-source fast path -- nothing was recorded for
    # it either. Everything is unavailable, so we must fall back to an
    # uncaretted frame rather than raise or print wrong columns.
    path = tmp_path / "vanishing.lit"
    path.write_text("rite boom():\n    proclaim MachineCurse('gone')\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    loader.install()
    import vanishing

    path.unlink()
    linecache.clearcache()
    curse._map_cache.clear()
    curse._source_cache.pop(str(path), None)

    try:
        vanishing.boom()
    except Exception:
        out = capture(sys.exc_info())

    assert "++ MACHINE CURSE ++" in out
    assert "MachineCurse: gone" in out


def test_modified_source_after_import_shows_the_line_that_actually_ran(
    tmp_path, monkeypatch
):
    # The ordinary edit-run-crash loop of a persistent process: import a
    # module, edit the .lit file on disk, then trigger an exception in the
    # already-compiled code. linecache.checkcache() (called internally by
    # traceback.extract_tb) would notice the mtime change and reload the
    # *current* file contents -- which is not what raised. The rendered
    # curse must show the line that was actually executed.
    path = tmp_path / "drifting.lit"
    path.write_text("rite invoke_spirit(tome):\n    render tome / 0\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    loader.install()
    import drifting

    # Rewrite with different content at a clearly later mtime, independent
    # of filesystem timestamp resolution, so linecache would actually see
    # it as stale.
    path.write_text("rite invoke_spirit(tome):\n    render 999999\n")
    later = os.path.getmtime(str(path)) + 5
    os.utime(str(path), (later, later))
    linecache.checkcache(str(path))

    try:
        drifting.invoke_spirit(1)
    except ZeroDivisionError:
        out = capture(sys.exc_info())

    assert "render tome / 0" in out
    assert "render 999999" not in out


def test_own_plumbing_frames_are_suppressed(tmp_path):
    # loader.chant()'s own exec(compile(...)) frame is Liturgy's internal
    # machinery, not user code -- it would otherwise appear above the
    # user's frames on every single failure run through chant(). This is
    # the specific case that motivated the general "drop every frame above
    # the first .lit frame" rule below; it must still be caught by it.
    script = tmp_path / "boomchant.lit"
    script.write_text("rite boom():\n    render 1 / 0\n\n\nboom()\n")

    try:
        loader.chant(str(script), [])
    except ZeroDivisionError:
        out = capture(sys.exc_info())

    assert "loader.py" not in out
    assert "exec(" not in out
    assert "boomchant.lit" in out


def test_module_invocation_has_no_runpy_frames(tmp_path):
    # `python -m liturgy chant ...` runs the script through runpy, whose
    # `_run_module_as_main`/`_run_code` frames sit above every .lit frame on
    # every single failure. They must be dropped along with everything else
    # above the user's first Liturgy frame.
    bad = tmp_path / "bad.lit"
    bad.write_text("intone(1 / 0)\n")

    result = subprocess.run(
        [sys.executable, "-m", "liturgy", "chant", str(bad)],
        capture_output=True,
        text=True,
    )

    assert "<frozen runpy>" not in result.stderr
    assert "++ MACHINE CURSE ++" in result.stderr
    assert "bad.lit" in result.stderr


def test_console_script_has_no_launcher_frame(tmp_path):
    # The ordinary invocation (`liturgy chant ...`, the installed console
    # script) has its own one-frame wrapper (`sys.exit(main())`) sitting
    # above every .lit frame. Run the real installed script rather than a
    # synthesised frame -- it's cheap, and it's what users actually run.
    console_script = Path(sys.executable).with_name("liturgy")
    assert console_script.exists(), "console script not found next to venv's python"
    bad = tmp_path / "bad.lit"
    bad.write_text("intone(1 / 0)\n")

    result = subprocess.run(
        [str(console_script), "chant", str(bad)],
        capture_output=True,
        text=True,
    )

    assert "bin/liturgy" not in result.stderr
    assert "sys.exit(main())" not in result.stderr
    assert "++ MACHINE CURSE ++" in result.stderr
    assert "bad.lit" in result.stderr


def test_stdlib_frames_after_a_lit_frame_still_render_in_full(tmp_path, monkeypatch):
    # The converse of frame-dropping: a .lit file calling into stdlib code
    # (here json.loads on bad input) has those library frames *after* its
    # own first .lit frame, and they must be left untouched.
    path = tmp_path / "jsonbad.lit"
    path.write_text("invoke json\njson.loads('not json')\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    loader.install()

    try:
        import jsonbad  # noqa: F401
    except json.JSONDecodeError:
        out = capture(sys.exc_info())

    assert "jsonbad.lit" in out
    assert "json/decoder.py" in out or "json\\decoder.py" in out
    assert "raise JSONDecodeError" in out
    assert "Expecting value" in out


def test_no_lit_frame_renders_every_frame(tmp_path):
    # If the exception never reached any Liturgy code (e.g. raised directly
    # from a REPL or a plain Python caller), there is no launcher to hide
    # relative to a .lit frame that doesn't exist. Rather than guess and
    # potentially discard the only information available, render
    # everything, exactly like an ordinary Python traceback would.
    try:
        json.loads("not json")
    except json.JSONDecodeError:
        out = capture(sys.exc_info())

    assert __file__.split("/")[-1] in out or "test_curse.py" in out
    assert "json/decoder.py" in out or "json\\decoder.py" in out
    assert "Expecting value" in out


def test_module_level_frame_does_not_claim_to_be_a_rite(tmp_path):
    script = tmp_path / "topcall.lit"
    script.write_text("rite boom():\n    render 1 / 0\n\n\nboom()\n")

    try:
        loader.chant(str(script), [])
    except ZeroDivisionError:
        out = capture(sys.exc_info())

    assert "in rite <module>" not in out


def test_install_sets_hooks_and_uninstall_restores_defaults():
    curse.install()
    assert sys.excepthook is curse.render_curse
    assert threading.excepthook is curse._thread_hook

    curse.uninstall()
    assert sys.excepthook is sys.__excepthook__
    assert threading.excepthook is threading.__excepthook__


def test_install_is_idempotent_about_repeated_calls():
    curse.install()
    curse.install()
    assert sys.excepthook is curse.render_curse
    assert threading.excepthook is curse._thread_hook


def test_form_feed_does_not_shift_the_reported_source_line(tmp_path):
    # Regression: C1, at the render end. A form feed is a conventional page
    # separator in older Python and legal anywhere; str.splitlines() breaks
    # on it and the tokenizer does not, so the recorded source must be split
    # the tokenizer's way or the curse quotes the wrong line.
    script = tmp_path / "pagebreak.lit"
    script.write_text('intone("one")\n\x0c\nrite boom():\n    render 1 / 0\n\n\nboom()\n')

    try:
        loader.chant(str(script), [])
    except ZeroDivisionError:
        out = capture(sys.exc_info())

    assert "line 4" in out
    assert "render 1 / 0" in out
    assert "boom()" in out


DRIFT_DRIVER = textwrap.dedent(
    """\
    import io, linecache, os, sys
    sys.path.insert(0, sys.argv[1])
    from liturgy import curse, loader
    loader.install()
    import drifting
    path = os.path.join(sys.argv[1], "drifting.lit")
    with open(path, "w") as fh:
        fh.write("rite invoke_spirit(tome):\\n    render 999999\\n")
    later = os.path.getmtime(path) + 5
    os.utime(path, (later, later))
    linecache.checkcache(path)
    try:
        drifting.invoke_spirit(1)
    except ZeroDivisionError:
        buf = io.StringIO()
        curse.render_curse(*sys.exc_info(), file=buf)
        sys.stdout.write(buf.getvalue())
    """
)

ORIGINAL_DRIFT = "rite invoke_spirit(tome):\n    render tome / 0\n"


def test_modified_source_still_shows_the_executed_line_on_a_warm_pycache(
    tmp_path,
):
    # Regression: I1. record_source used to be called only from
    # source_to_code, which the import system skips entirely when a valid
    # .pyc exists -- so from the second run of a program onwards nothing was
    # recorded and the whole stale-source guarantee was inert. tmp_path is
    # always cold, which is why the in-process test above passed against the
    # broken implementation too. Two real processes; the first warms the
    # .pyc.
    path = tmp_path / "drifting.lit"
    path.write_text(ORIGINAL_DRIFT)
    driver = tmp_path / "driver.py"
    driver.write_text(DRIFT_DRIVER)

    warm = subprocess.run(
        [sys.executable, "-c", f"import sys; sys.path.insert(0, {str(tmp_path)!r});"
         " from liturgy import loader; loader.install(); import drifting"],
        capture_output=True, text=True,
    )
    assert warm.returncode == 0, warm.stderr
    assert list(tmp_path.glob("__pycache__/drifting.*.pyc")), "no .pyc was written"

    # Deliberately do NOT touch the file here: rewriting it, even with
    # identical bytes, bumps the mtime and invalidates the .pyc, which would
    # send the second run back down the compile path and hide the bug. The
    # driver does the edit *after* importing, which is the real scenario.
    out = subprocess.run(
        [sys.executable, str(driver), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    assert "render tome / 0" in out.stdout
    assert "render 999999" not in out.stdout


# --- I5: SyntaxError location ----------------------------------------------

SYNTAX_CASES = {
    "unclosed": ('intone("a")\nintone(1 +\n', "never closed", 2),
    "indent": ("rite f():\nabide\n", "expected an indented block", 2),
}


@pytest.mark.parametrize("case", sorted(SYNTAX_CASES))
def test_chant_renders_a_syntax_error_with_line_source_and_caret(
    tmp_path, case
):
    # Before: no .lit frame, no source line, no caret -- and, with nothing to
    # anchor to, the full launcher plumbing came back. Strictly worse than
    # the plain Python traceback for the commonest class of error there is.
    src, fragment, lineno = SYNTAX_CASES[case]
    script = tmp_path / f"{case}.lit"
    script.write_text(src)

    try:
        loader.chant(str(script), [])
    except SyntaxError:
        out = capture(sys.exc_info())

    assert f"{case}.lit, line {lineno}" in out
    assert fragment in out
    assert "^" in out
    assert "loader.py" not in out
    assert "exec(" not in out


@pytest.mark.parametrize("case", sorted(SYNTAX_CASES))
def test_import_renders_a_syntax_error_with_line_source_and_caret(
    tmp_path, monkeypatch, case
):
    src, fragment, lineno = SYNTAX_CASES[case]
    (tmp_path / f"imp{case}.lit").write_text(src)
    monkeypatch.syspath_prepend(str(tmp_path))
    loader.install()

    try:
        importlib.import_module(f"imp{case}")
    except SyntaxError:
        out = capture(sys.exc_info())

    assert f"imp{case}.lit, line {lineno}" in out
    assert fragment in out
    # No "importlib not in out" assertion here: this test imports from a .py
    # test module, so the traceback has no .lit frame and the `anchored`
    # branch wipes every frame regardless. Asserting the absence of import
    # machinery here would pass whatever the suppression rule did. The case
    # that genuinely exercises it is the next test, where a .lit does the
    # importing and there IS a .lit frame for the plumbing to hide behind.


def test_a_litany_invoking_an_uncompilable_litany_hides_the_import_machinery(
    tmp_path,
):
    # CPython shows exactly two frames for the equivalent .py case: the
    # importing line and the fault. Everything between is import machinery it
    # hides, and so do we -- including our own loader and transform frames,
    # which sit between two .lit frames where the launcher rule cannot reach.
    # Distinct module name: `broken` is already in sys.modules from the
    # `broken` fixture above, and a cached module never re-compiles, so the
    # name would silently stop testing anything when the full suite runs.
    (tmp_path / "uncompilable.lit").write_text("x = (1, 2\n")
    outer = tmp_path / "outer.lit"
    outer.write_text('invoke uncompilable\nintone("never")\n')

    try:
        loader.chant(str(outer), [])
    except SyntaxError:
        out = capture(sys.exc_info())

    # Both ends of the story survive: what invoked, and what would not compile.
    assert "outer.lit, line 1" in out
    assert "invoke uncompilable" in out
    assert "uncompilable.lit, line 1" in out
    assert "x = (1, 2" in out
    assert "UnfinishedLitany" in out

    # Everything in between is gone.
    assert "importlib" not in out
    assert "loader.py" not in out
    assert "transform.py" not in out
    assert "exec_module" not in out


def test_hiding_import_machinery_spares_libraries_a_litany_calls_into(
    tmp_path,
):
    # The plumbing filter must not become a blanket "drop anything that is not
    # a .lit frame" -- stdlib and third-party frames below the litany are the
    # user's answer, not noise.
    script = tmp_path / "usesjson.lit"
    script.write_text(
        'invoke json\nrite parse():\n    render json.loads("{bad}")\nparse()\n'
    )

    try:
        loader.chant(str(script), [])
    except Exception:
        out = capture(sys.exc_info())

    assert "usesjson.lit, line 3" in out
    assert out.count("json/decoder.py") >= 1
    assert "importlib" not in out


def test_syntax_error_quotes_the_liturgy_line_not_the_generated_python(
    tmp_path,
):
    script = tmp_path / "shown.lit"
    script.write_text("rite f():\nabide\n")

    try:
        loader.chant(str(script), [])
    except SyntaxError:
        out = capture(sys.exc_info())

    assert "abide" in out
    assert "pass" not in out


def test_syntax_error_caret_is_mapped_back_to_liturgy_columns(tmp_path):
    # "intone(" is one column wider than "print(", so an unmapped caret would
    # sit under the "1", not under the bracket that was never closed.
    script = tmp_path / "caret.lit"
    script.write_text("intone(1 +\n")

    try:
        loader.chant(str(script), [])
    except SyntaxError:
        out = capture(sys.exc_info())

    lines = out.splitlines()
    i = next(n for n, line in enumerate(lines) if line.strip() == "intone(1 +")
    assert lines[i + 1] == "       " + " " * 6 + "^"


def test_a_mistyped_relic_has_no_launcher_frames(tmp_path):
    # Same fall-through: nothing anchored the frame-dropping, so the console
    # script wrapper, cli.main and chant's own open() all showed up.
    try:
        loader.chant(str(tmp_path / "nosuch.lit"), [])
    except FileNotFoundError:
        out = capture(sys.exc_info())

    assert "RelicNotFound" in out
    assert "loader.py" not in out
    assert "test_curse.py" not in out


def test_the_repl_reports_a_dedent_mismatch_with_a_location():
    out = subprocess.run(
        [sys.executable, "-m", "liturgy", "commune"],
        input="should Sanctioned:\n  x=1\n y=2\n",
        capture_output=True, text=True,
    )
    assert "IndentationError" in out.stdout + out.stderr


# --- I7: exception chains ---------------------------------------------------

def test_the_root_cause_of_a_raise_from_is_rendered(tmp_path):
    script = tmp_path / "chained.lit"
    script.write_text(
        "attempt:\n"
        "    intone(1/0)\n"
        "curse DivisionByTheVoid styled e:\n"
        '    proclaim MotiveFailure("rite failed") within e\n'
    )

    try:
        loader.chant(str(script), [])
    except RuntimeError:
        out = capture(sys.exc_info())

    assert "DivisionByTheVoid: division by zero" in out
    assert "MotiveFailure: rite failed" in out
    assert "intone(1/0)" in out
    assert curse.CAUSE_SEPARATOR in out
    assert out.index("DivisionByTheVoid") < out.index("MotiveFailure")


def test_an_implicit_context_is_rendered_with_its_own_separator(tmp_path):
    script = tmp_path / "ctx.lit"
    script.write_text(
        "attempt:\n"
        "    intone(1/0)\n"
        "curse DivisionByTheVoid:\n"
        '    proclaim MotiveFailure("secondary")\n'
    )

    try:
        loader.chant(str(script), [])
    except RuntimeError:
        out = capture(sys.exc_info())

    assert curse.CONTEXT_SEPARATOR in out
    assert "DivisionByTheVoid" in out


def test_a_suppressed_context_stays_suppressed(tmp_path):
    script = tmp_path / "supp.lit"
    script.write_text(
        "attempt:\n"
        "    intone(1/0)\n"
        "curse DivisionByTheVoid:\n"
        '    proclaim MotiveFailure("only me") within Void\n'
    )

    try:
        loader.chant(str(script), [])
    except RuntimeError:
        out = capture(sys.exc_info())

    assert "DivisionByTheVoid" not in out
    assert curse.CONTEXT_SEPARATOR not in out


def test_exception_group_members_are_rendered():
    try:
        raise ExceptionGroup(
            "several", [ValueError("first"), KeyError("second")]
        )
    except ExceptionGroup:
        out = capture(sys.exc_info())

    assert "ImpureOffering: first" in out
    assert "LostPattern: 'second'" in out


def test_a_self_referential_chain_terminates():
    a = ValueError("a")
    b = KeyError("b")
    a.__cause__ = b
    b.__cause__ = a
    try:
        raise a
    except ValueError:
        out = capture(sys.exc_info())
    assert "ImpureOffering: a" in out


def test_one_banner_per_curse_however_long_the_chain(tmp_path):
    script = tmp_path / "banner.lit"
    script.write_text(
        "attempt:\n"
        "    intone(1/0)\n"
        "curse DivisionByTheVoid styled e:\n"
        '    proclaim MotiveFailure("x") within e\n'
    )
    try:
        loader.chant(str(script), [])
    except RuntimeError:
        out = capture(sys.exc_info())

    assert out.count(curse.BANNER_OPEN) == 1
    assert out.count(curse.BANNER_CLOSE) == 1


# --- Minors -----------------------------------------------------------------

def test_module_not_found_is_themed_through_its_ancestor():
    # An exact __name__ lookup left the commonest import failure there is
    # rendering un-themed inside a themed curse.
    assert curse.curse_name(ModuleNotFoundError) == "ForbiddenLore"


def test_the_mro_walk_stops_short_of_the_catch_all_roots():
    # MachineCurse is the name of Exception itself, not of everything under
    # it; renaming IndentationError to MachineCurse loses more than it gains.
    assert curse.curse_name(IndentationError) == "IndentationError"
    assert curse.curse_name(PermissionError) == "PermissionError"
    assert curse.curse_name(Exception) == "MachineCurse"


def test_a_library_exception_keeps_its_own_name():
    # json.JSONDecodeError is a ValueError, but calling it ImpureOffering
    # would hide the informative half of the name.
    assert curse.curse_name(json.JSONDecodeError) == "JSONDecodeError"


def test_a_multiline_expression_still_gets_a_caret(tmp_path):
    # end_colno belongs to end_lineno, not to lineno. When the expression
    # ends further left than it began -- an indented call whose closing
    # bracket sits at column 0 -- the guard compared columns from two
    # different lines, decided end < start, and dropped the caret.
    script = tmp_path / "spread.lit"
    script.write_text(
        "rite boom(a, b):\n"
        "    render a / b\n"
        "\n"
        "\n"
        "rite outer():\n"
        "    x = boom(\n"
        "1,\n"
        "0,\n"
        ")\n"
        "    render x\n"
        "\n"
        "\n"
        "outer()\n"
    )

    try:
        loader.chant(str(script), [])
    except ZeroDivisionError:
        out = capture(sys.exc_info())

    lines = out.splitlines()
    i = next(n for n, ln in enumerate(lines) if ln.strip() == "x = boom(")
    assert lines[i + 1].strip().startswith("^"), out


def test_a_very_long_chain_is_rendered_without_recursing():
    # Recursing down the chain would trade a rendered curse for a
    # RecursionError and the fallback plain traceback.
    outermost = ValueError("0")
    for i in range(1, 3000):
        nxt = ValueError(str(i))
        nxt.__cause__ = outermost
        outermost = nxt
    buf = io.StringIO()
    curse.render_curse(ValueError, outermost, None, file=buf)
    lines = buf.getvalue().splitlines()

    assert lines[1].strip() == "ImpureOffering: 0"  # the root, rendered first
    assert lines[-2].strip() == "ImpureOffering: 2999"
