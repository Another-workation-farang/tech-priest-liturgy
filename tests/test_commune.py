import subprocess
import sys
from pathlib import Path

from liturgy.commune import LiturgyConsole


def feed(lines):
    """Push lines through runsource; return (needs_more_flags, console)."""
    console = LiturgyConsole()
    flags = []
    buffer = []
    for line in lines:
        buffer.append(line)
        flags.append(console.runsource("\n".join(buffer)))
        if not flags[-1]:
            buffer = []
    return flags, console


def test_single_statement_executes():
    flags, console = feed(["x = 1 + 1"])
    assert flags == [False]
    assert console.locals["x"] == 2


def test_liturgy_keywords_work():
    flags, console = feed(["x = Sanctioned"])
    assert flags == [False]
    assert console.locals["x"] is True


def test_incomplete_block_requests_more_input():
    flags, _ = feed(["rite f():"])
    assert flags == [True]


def test_multiline_rite_completes():
    flags, console = feed(["rite f():", "    render 7", ""])
    assert flags[-1] is False
    assert console.locals["f"]() == 7


def test_unterminated_bracket_requests_more_input():
    # tokenize raises TokenError here; it must read as "keep reading"
    flags, _ = feed(["x = ["])
    assert flags == [True]


def test_unterminated_string_requests_more_input():
    flags, _ = feed(['x = """abc'])
    assert flags == [True]


def test_syntax_error_is_reported_not_buffered(capsys):
    # A complete, unambiguous syntax error: not incomplete input.
    flags, _ = feed(["x = = 1"])
    assert flags == [False]
    assert "SyntaxError" in capsys.readouterr().err


def test_commune_starts_and_exits_cleanly():
    out = subprocess.run(
        [sys.executable, "-m", "liturgy", "commune"],
        input="intone(measure('omnissiah'))\n",
        capture_output=True,
        text=True,
    )
    assert "9" in out.stdout


def test_dedent_mismatch_is_reported_not_buffered(capsys):
    # tokenize never raises IndentationError for genuinely incomplete
    # input -- an open block tokenizes cleanly, and incompleteness is only
    # decided later by compile() returning None. A dedent that doesn't
    # match any outer indentation level is therefore a complete,
    # unrecoverable error, not "keep reading".
    flags, _ = feed(["should Sanctioned:", "  x=1", " y=2"])
    assert flags[-1] is False
    assert "IndentationError" in capsys.readouterr().err


def test_input_after_dedent_mismatch_still_executes():
    # The property that actually matters: a reported error must not leave
    # the console wedged, silently swallowing every line that follows.
    flags, console = feed(
        ["should Sanctioned:", "  x=1", " y=2", "intone(999)"]
    )
    assert flags[-1] is False


def test_repl_recovers_after_dedent_mismatch_over_stdin():
    out = subprocess.run(
        [sys.executable, "-m", "liturgy", "commune"],
        input=(
            "should Sanctioned:\n"
            "  x=1\n"
            " y=2\n"
            "intone(999)\n"
            "intone(111)\n"
        ),
        capture_output=True,
        text=True,
    )
    assert "999" in out.stdout
    assert "111" in out.stdout


def test_repl_can_import_a_lit_module(tmp_path):
    # Regression: I4 — loader.install() was only ever called from chant(), so
    # the REPL could not import .lit modules at all. It is the natural place
    # to poke at a module you have just written.
    (tmp_path / "shrine.lit").write_text('GREETING = "ave"\n')
    out = subprocess.run(
        [sys.executable, "-m", "liturgy", "commune"],
        input="within shrine invoke GREETING\nintone(GREETING)\n",
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert "ModuleNotFoundError" not in out.stdout + out.stderr
    assert "ave" in out.stdout


def test_console_script_repl_can_import_from_the_working_directory(tmp_path):
    # The installed console script's sys.path[0] is its own bin directory,
    # not the cwd, so `liturgy commune` could not import anything the user
    # was standing next to -- the plain `python` REPL prepends the cwd.
    console_script = Path(sys.executable).with_name("liturgy")
    assert console_script.exists(), "console script not found next to venv's python"
    (tmp_path / "shrine.lit").write_text('GREETING = "ave"\n')
    out = subprocess.run(
        [str(console_script), "commune"],
        input="within shrine invoke GREETING\nintone(GREETING)\n",
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert "ave" in out.stdout


# --- Spec II constructs at the prompt --------------------------------------
#
# `runsource` used to transform with DEFAULT_PASSES, so every construct
# header reached `self.compile()` un-desugared and died as a SyntaxError
# before `compile_litany` was ever consulted. Nothing in this file mentioned
# a construct, which is why that shipped. These drive the real console over
# stdin, one construct each, plus a block typed across several lines.


def commune(*lines: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "liturgy", "commune"],
        input="".join(f"{line}\n" for line in lines),
        capture_output=True,
        text=True,
    )


def test_consecrated_works_at_the_prompt():
    out = commune("consecrated PORT = 8080", "intone(PORT)")
    assert "8080" in out.stdout
    assert "SyntaxError" not in out.stdout + out.stderr


def test_an_annotated_consecrated_works_at_the_prompt():
    # Spec IV. `visit_Interactive` is the REPL's own scope visit, and the
    # facts for the entry have to reach it or the prompt sees an ordinary
    # annotated binding.
    out = commune("consecrated PORT: int = 8080", "intone(PORT)")
    assert "8080" in out.stdout
    assert "SyntaxError" not in out.stdout + out.stderr


def test_an_annotated_rebinding_within_one_prompt_entry_is_rejected():
    out = commune("consecrated PORT: int = 8080; PORT = 9")
    assert "may not be rebound" in out.stdout + out.stderr


def test_a_rebinding_within_one_prompt_entry_is_rejected():
    # Each entry is its own compilation unit, and `commune` compiles with
    # mode="single" -- an `Interactive` node, not a `Module`. `ConstructPass`
    # had no visitor for it, so the prompt got no scope visit at all: no
    # rebinding check, and (on 3.12/3.13, where annotations are still
    # eager) not even a desugared carrier.
    out = commune("consecrated PORT = 8080; PORT = 9")
    assert "may not be rebound" in out.stdout + out.stderr


def test_a_rebinding_typed_on_a_later_line_is_not_caught():
    # Enforcement is per-compilation-unit, and the compiler has no record of
    # the earlier entry. This is a real limit of the design, documented in
    # Chapter VII; asserting it here keeps it from being mistaken for a bug
    # and "fixed" with something that cannot work.
    out = commune("consecrated PORT = 8080", "PORT = 9", "intone(PORT)")
    assert "9" in out.stdout
    assert "may not be rebound" not in out.stdout + out.stderr


def test_litany_works_at_the_prompt_typed_across_several_lines():
    out = commune(
        "tries = []",
        "litany(thrice, curse=MotiveFailure):",
        "    tries.append(1)",
        "    should measure(tries) < 2:",
        "        proclaim MotiveFailure('again')",
        "",
        "intone(measure(tries))",
    )
    assert "2" in out.stdout
    assert "SyntaxError" not in out.stdout + out.stderr


def test_augur_works_at_the_prompt():
    out = commune(
        "rite divide(a, b):",
        "    augur:",
        "        b != 0",
        "    render a / b",
        "",
        "intone(divide(6, 2))",
        "divide(1, 0)",
    )
    assert "3.0" in out.stdout
    assert "the omens forbid it -- b != 0" in out.stdout + out.stderr
