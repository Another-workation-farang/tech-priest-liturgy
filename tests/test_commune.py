import subprocess
import sys

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
