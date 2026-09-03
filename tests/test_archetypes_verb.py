"""`augur --archetypes`: the third check, and the one that is asked for.

Most of these need no mypy at all. `check` takes an oracle, so a canned
mypy transcript exercises every rendering path -- including the ones a real
mypy is hard to provoke into, like a diagnostic with no column and a run
that crashes. The handful marked `needs_mypy` are the end-to-end proof that
the canned transcripts describe the real thing.
"""

import io
import os
import sys

import pytest

from liturgy.archetypes import (
    MypyFailed,
    MypyUnintelligible,
    OracleRun,
    mypy_available,
)
from liturgy.cli import main
from liturgy.tooling import augur

FALSE = (
    "rite greet(name: str) -> int:\n"
    "    render name\n"
    "\n"
    "rite add(a: int, b: int) -> int:\n"
    "    render a + b\n"
    "\n"
    'intone(add("one", 2))\n'
)

TRUE = "rite add(a: int, b: int) -> int:\n    render a + b\n\nintone(add(1, 2))\n"


def speaking(*lines, status=1):
    """An oracle that says `lines`, whatever it is handed."""

    def oracle(path, cache_dir):
        return OracleRun("".join(f"{line}\n" for line in lines), "", status)

    return oracle


def raising(err):
    def oracle(path, cache_dir):
        raise err

    return oracle


def run(tmp_path, files, *, plain=False, archetypes=True, oracle=None, paths=None):
    for name, src in files.items():
        (tmp_path / name).write_text(src)
        last = tmp_path / name
    targets = [str(tmp_path / p) for p in paths] if paths else [str(last)]
    buf = io.StringIO()
    code = augur(
        targets, plain=plain, archetypes=archetypes, oracle=oracle, out=buf
    )
    return code, buf.getvalue()


# --- refusing, when mypy is not there --------------------------------------

no_mypy = pytest.mark.skipif(
    mypy_available(), reason="this interpreter has mypy; the refusal cannot happen"
)


@no_mypy
def test_without_mypy_the_verb_refuses_and_says_how_to_fix_it(tmp_path):
    code, out = run(tmp_path, {"p.lit": TRUE})
    assert code == 1
    assert "++ CANNOT READ ARCHETYPES: mypy is not installed ++" in out
    assert "pip install 'liturgy[archetypes]'" in out


@no_mypy
def test_the_refusal_comes_before_the_walk_and_reads_nothing(tmp_path):
    # Not "no findings" plus a footnote: nothing was read, and the output
    # must not carry a single omen suggesting otherwise.
    code, out = run(tmp_path, {"q.lit": 'span = "text range"\n'})
    assert code == 1
    assert "THE OMENS ARE TROUBLED" not in out
    assert "span" not in out


@no_mypy
def test_the_refusal_is_the_flag_s_alone(tmp_path):
    # Without the flag the missing extra is nobody's business.
    code, out = run(tmp_path, {"p.lit": TRUE}, archetypes=False)
    assert code == 0
    assert out == ""


@no_mypy
def test_the_cli_flag_reaches_the_verb(tmp_path, capsys):
    p = tmp_path / "p.lit"
    p.write_text(TRUE)
    assert main(["augur", "--archetypes", str(p)]) == 1
    assert "CANNOT READ ARCHETYPES" in capsys.readouterr().out
    assert main(["augur", str(p)]) == 0


# --- the two standing checks are untouched ---------------------------------


def test_the_flag_changes_nothing_about_the_other_two_checks(tmp_path):
    src = 'span = "text range"\nrite f(x: int) -> int:\n    render "no"\n'
    plain_run = run(tmp_path, {"q.lit": src}, plain=True, archetypes=False)
    with_flag = run(
        tmp_path,
        {"q.lit": src},
        plain=True,
        oracle=speaking("q.py:3:12: error: Incompatible return value type  [x]"),
    )
    assert with_flag[1].startswith(plain_run[1])
    assert plain_run[0] == with_flag[0] == 1


def test_a_true_litany_with_the_flag_is_silent(tmp_path):
    code, out = run(tmp_path, {"p.lit": TRUE}, oracle=speaking(status=0))
    assert code == 0
    assert out == ""


# --- rendering -------------------------------------------------------------


def test_a_finding_wears_the_house_style_with_a_caret(tmp_path):
    code, out = run(
        tmp_path,
        {"p.lit": FALSE},
        oracle=speaking(
            'p.py:2:12: error: Incompatible return value type (got "str", '
            'expected "int")  [return-value]'
        ),
    )
    assert code == 1
    assert "++ THE OMENS ARE TROUBLED ++" in out
    assert "line 2" in out
    # The caret line, and the source line it sits under. Found by shape
    # rather than by words: the message itself is the checker's to phrase.
    lines = out.splitlines()
    at = next(i for i, line in enumerate(lines) if set(line.strip()) == {"^"})
    body = lines[at - 1]
    assert body.strip() == "render name"
    assert lines[at].index("^") == body.index("name")
    assert "[return-value]" in out


def test_plain_findings_are_machine_readable_with_one_based_columns(tmp_path):
    code, out = run(
        tmp_path,
        {"p.lit": FALSE},
        plain=True,
        # mypy's column is 1-based and counts the *generated* Python:
        # `print(add("one", 2))`, where 11 is the opening quote. `intone` is
        # a character longer than `print`, so the litany's own column is 12.
        oracle=speaking('p.py:7:11: error: Argument 1 to "add"  [arg-type]'),
    )
    assert code == 1
    # One line, and the coordinates are this verb's to get right; the words
    # between them belong to the checker.
    (line,) = out.splitlines()
    assert line.startswith(f'{tmp_path / "p.lit"}:7:12: ')
    assert line.endswith("[arg-type]")
    assert FALSE.splitlines()[6][11] == '"'


def test_a_finding_without_a_column_gets_no_caret_and_no_invented_column(tmp_path):
    code, out = run(
        tmp_path,
        {"p.lit": FALSE},
        oracle=speaking("p.py:2: error: Something file-shaped  [misc]"),
    )
    assert code == 1
    assert "Something file-shaped" in out
    assert "^" not in out
    assert "render name" not in out


def test_a_note_explains_the_error_above_it_rather_than_announcing_a_fault(tmp_path):
    code, out = run(
        tmp_path,
        {"p.lit": FALSE},
        oracle=speaking(
            'p.py:7:12: error: Argument 1 to "add"  [arg-type]',
            "p.py:7:12: note: consider a cast",
        ),
    )
    assert code == 1
    assert out.count("++ THE OMENS ARE TROUBLED ++") == 1
    assert "   note: consider a cast" in out


def test_a_note_with_no_error_before_it_is_marked_as_a_note(tmp_path):
    code, out = run(
        tmp_path,
        {"p.lit": FALSE},
        oracle=speaking("p.py:2:12: note: standing on its own", status=0),
    )
    assert code == 1
    assert "note: standing on its own" in out


def test_an_untranslated_message_is_attributed_to_the_checker(tmp_path):
    # `Finding.translated` is False for anything the checker's words could
    # not be confidently rendered into Liturgy, and the reader is told
    # whose words they are rather than left to wonder why a litany is
    # suddenly being lectured about Python.
    code, out = run(
        tmp_path,
        {"p.lit": FALSE},
        plain=True,
        oracle=speaking("p.py:2:12: error: Something Python-shaped  [misc]"),
    )
    assert code == 1
    assert "mypy's own words: Something Python-shaped  [misc]" in out


def test_a_translated_message_is_not_attributed_to_the_checker(tmp_path):
    code, out = run(
        tmp_path,
        {"p.lit": FALSE},
        plain=True,
        oracle=speaking(
            'p.py:2:12: error: Incompatible return value type (got "str", '
            'expected "int")  [return-value]'
        ),
    )
    assert code == 1
    assert "mypy" not in out


# --- unread is never clean -------------------------------------------------


@pytest.mark.parametrize(
    "err",
    [
        MypyFailed("mypy did not finish within 120s"),
        MypyUnintelligible("cannot read mypy's output: 'what?'"),
    ],
)
def test_a_checker_that_reached_no_verdict_says_so_and_is_not_silence(tmp_path, err):
    code, out = run(tmp_path, {"p.lit": TRUE}, oracle=raising(err))
    assert code == 1
    assert "archetypes unread" in out
    assert str(err) in out


def test_an_unread_litany_does_not_end_the_walk(tmp_path):
    # The rule augur was reviewed into: one bad file is reported and the
    # walk goes on. A checker that dies on the third file of forty is no
    # checker.
    seen = []

    def oracle(path, cache_dir):
        seen.append(path.name)
        if path.stem == "a":
            raise MypyFailed("mypy crashed")
        return OracleRun("b.py:2:12: error: still read  [misc]\n", "", 1)

    code, out = run(
        tmp_path,
        {"a.lit": TRUE, "b.lit": FALSE},
        oracle=oracle,
        paths=["."],
        plain=True,
    )
    assert code == 1
    assert seen == ["a.py", "b.py"]
    assert "archetypes unread: mypy crashed" in out
    assert "still read" in out


def test_a_litany_that_does_not_compile_is_not_handed_to_the_checker(tmp_path):
    # An unsanctioned parameter passes the collision scan -- which suppresses
    # the archetype rule -- and fails the compile, which is the one path that
    # reaches the third check with a litany `check` would only raise on
    # again. The heresy is already reported, in better words than a
    # re-raised SyntaxError, and "archetypes unread" on top of it would name
    # a second fault that does not exist.
    called = []
    code, out = run(
        tmp_path,
        {"bad.lit": "rite f(x):\n    render x\n"},
        oracle=lambda p, c: called.append(p) or OracleRun("", "", 0),
    )
    assert code == 1
    assert "TechHeresy" in out
    assert called == []
    assert "archetypes unread" not in out


# --- what is read, and what is not -----------------------------------------


def test_python_files_are_not_read_for_archetypes(tmp_path):
    # Documented in `augur`: a .py file has no substitutions and so no
    # SourceMap, and running mypy on Python is mypy's own job.
    called = []
    code, out = run(
        tmp_path,
        {"plain.py": "def f(x: int) -> int:\n    return 'no'\n"},
        oracle=lambda p, c: called.append(p) or OracleRun("", "", 0),
    )
    assert called == []
    # ...but not in silence. An empty report and exit 0 would be a clean
    # bill of health for a check that never ran.
    assert code == 1
    assert "++ NO ARCHETYPES WERE READ: no litany was given ++" in out


def test_asking_for_archetypes_and_getting_none_is_never_silent(tmp_path):
    # The shape the module docstring calls the worst outcome available:
    # asked for, never run, reported as nothing found.
    code, out = run(
        tmp_path, {"plain.py": "x = 1\n"}, oracle=lambda p, c: OracleRun("", "", 0)
    )
    assert code == 1
    assert "NO ARCHETYPES WERE READ" in out
    assert "only .lit files" in out


def test_the_flag_unasked_says_nothing_about_python_files(tmp_path):
    # Without `--archetypes` a clean .py is clean and silent, exactly as
    # before: the notice belongs to the flag, not to the walk.
    code, out = run(tmp_path, {"plain.py": "x = 1\n"}, archetypes=False)
    assert code == 0
    assert out == ""


def test_a_python_file_beside_a_litany_is_skipped_without_a_word(tmp_path):
    # The documented, harmless case. The litany *was* read, so nothing was
    # silently missed and there is nothing to announce.
    code, out = run(
        tmp_path,
        {"plain.py": "x = 1\n", "p.lit": TRUE},
        oracle=lambda p, c: OracleRun("", "", 0),
        paths=["."],
    )
    assert code == 0
    assert out == ""


def test_a_filesystem_that_will_not_stage_the_copy_does_not_end_the_walk(
    tmp_path, monkeypatch
):
    # A missing TMPDIR is ordinary on CI and after a macOS reboot. `augur`
    # promises an int; "archetypes unread" is the designed answer and a
    # traceback out of a reading verb is not.
    import tempfile

    def boom(*a, **k):
        raise FileNotFoundError(2, "No such file or directory")

    monkeypatch.setattr(tempfile, "TemporaryDirectory", boom)
    code, out = run(tmp_path, {"p.lit": TRUE}, plain=True, oracle=lambda p, c: None)
    assert code == 1
    assert "archetypes unread: the litany could not be staged for mypy" in out


# --- end to end, with a real mypy ------------------------------------------


def _mypy_python():
    if mypy_available():
        return sys.executable
    named = os.environ.get("LITURGY_MYPY_PYTHON")
    if named and mypy_available(named):
        return named
    return None


MYPY = _mypy_python()
needs_mypy = pytest.mark.skipif(
    MYPY is None,
    reason="no mypy: install liturgy[archetypes], or set LITURGY_MYPY_PYTHON",
)


@needs_mypy
def test_a_real_false_archetype_reaches_the_reader(tmp_path):
    from liturgy.archetypes import mypy_oracle

    code, out = run(
        tmp_path, {"p.lit": FALSE}, plain=True, oracle=mypy_oracle(MYPY)
    )
    assert code == 1
    lit = tmp_path / "p.lit"
    # The words belong to the checker (Task 3 translates them); the
    # coordinates and the code belong to this verb.
    assert f"{lit}:2:12:" in out
    assert f"{lit}:7:12:" in out
    assert "[return-value]" in out and "[arg-type]" in out


@needs_mypy
def test_a_real_true_litany_is_silent_and_exits_clean(tmp_path):
    from liturgy.archetypes import mypy_oracle

    code, out = run(tmp_path, {"p.lit": TRUE}, oracle=mypy_oracle(MYPY))
    assert code == 0
    assert out == ""
