import io
import linecache
import os
import sys
import textwrap
import threading

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
    # user's frames on every single failure run through chant().
    script = tmp_path / "boomchant.lit"
    script.write_text("rite boom():\n    render 1 / 0\n\n\nboom()\n")

    try:
        loader.chant(str(script), [])
    except ZeroDivisionError:
        out = capture(sys.exc_info())

    assert "loader.py" not in out
    assert "exec(" not in out
    assert "boomchant.lit" in out


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
