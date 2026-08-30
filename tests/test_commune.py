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
