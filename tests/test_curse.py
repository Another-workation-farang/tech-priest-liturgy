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
