"""Archetypes that are false, read out of mypy and mapped back.

Two halves, deliberately. "Run mypy" and "interpret what mypy said" are
separate functions so that every way of misreading a diagnostic -- and every
way of failing to get one -- is testable in an environment with no mypy at
all. Only the handful of end-to-end tests at the bottom need the real thing.
"""

from __future__ import annotations

import os
import pathlib
import sys

import pytest

from liturgy.archetypes import (
    ArchetypesUnread,
    Diagnostic,
    Finding,
    MypyFailed,
    MypyNotInstalled,
    MypyUnintelligible,
    OracleRun,
    _module_stem,
    check,
    interpret,
    mypy_available,
    mypy_oracle,
    parse_diagnostics,
    to_finding,
)
from liturgy.compiler import _PASSES
from liturgy.constructs import MACHINE_PREFIX
from liturgy.transform import UnfinishedLitany, split_lines, transform


def fake_oracle(stdout="", stderr="", status=0, seen=None):
    """An oracle that says what it is told to, and records what it was asked."""

    def run(path, cache_dir):
        if seen is not None:
            seen.append((path, cache_dir))
        return OracleRun(stdout, stderr, status)

    return run


def mapping_of(src, filename="prayer.lit"):
    """The two things `to_finding` needs, for a litany."""
    out = transform(src, _PASSES, filename=filename)
    return split_lines(out.python), out.source_map


# --- reading mypy's output -------------------------------------------------


def test_an_error_line_is_parsed_whole():
    (d,) = parse_diagnostics(
        'prayer.py:2:12: error: Incompatible return value type '
        '(got "str", expected "int")  [return-value]\n'
    )
    assert (d.path, d.line, d.col, d.severity, d.code) == (
        "prayer.py",
        2,
        12,
        "error",
        "return-value",
    )
    assert d.message == 'Incompatible return value type (got "str", expected "int")'


def test_a_note_carries_no_code():
    (d,) = parse_diagnostics(
        "prayer.py:8:17: note: This violates the Liskov substitution principle\n"
    )
    assert (d.severity, d.code) == ("note", None)
    assert d.message == "This violates the Liskov substitution principle"


def test_a_diagnostic_with_no_column_keeps_none():
    # mypy omits the column for a handful of file-level diagnostics. A
    # column is never invented for them.
    (d,) = parse_diagnostics("prayer.py:1: error: Cannot find implementation  [import]\n")
    assert d.col is None
    assert d.line == 1


def test_blank_lines_are_not_diagnostics():
    assert parse_diagnostics("\n   \n") == []


def test_output_that_cannot_be_read_is_raised_not_skipped():
    with pytest.raises(MypyUnintelligible):
        parse_diagnostics("something entirely unexpected\n")


def test_an_unreadable_line_beside_a_good_one_still_raises():
    # The unreadable line might have been the only finding there was.
    with pytest.raises(MypyUnintelligible):
        parse_diagnostics(
            "prayer.py:1:1: error: Boom  [misc]\nmypy: internal error, sorry\n"
        )


def test_brackets_inside_a_message_are_not_mistaken_for_a_code():
    (d,) = parse_diagnostics(
        'p.py:1:1: error: Value of type "list[int]" is not indexable  [index]\n'
    )
    assert d.code == "index"
    assert d.message == 'Value of type "list[int]" is not indexable'


# --- the ways mypy can fail to reach a verdict -----------------------------


def test_a_crash_is_not_a_clean_bill_of_health():
    with pytest.raises(MypyFailed) as err:
        interpret(OracleRun("", "Traceback: mypy blew up", 2), [], None)
    assert "mypy blew up" in str(err.value)


def test_errors_found_but_none_parsed_is_a_failure():
    # The silent-success hole exactly: mypy says it found errors and this
    # module saw none. Returning [] here would report a clean litany.
    with pytest.raises(MypyFailed):
        interpret(OracleRun("", "", 1), [], None)


def test_only_notes_at_status_one_is_a_failure():
    lines, smap = mapping_of("intone('ave')\n")
    with pytest.raises(MypyFailed):
        interpret(OracleRun("p.py:1:1: note: hm\n", "", 1), lines, smap)


def test_an_error_at_status_zero_is_a_failure():
    lines, smap = mapping_of("intone('ave')\n")
    with pytest.raises(MypyFailed):
        interpret(OracleRun("p.py:1:1: error: Boom  [misc]\n", "", 0), lines, smap)


def test_every_failure_is_one_kind_of_thing():
    # A caller wanting only "did the check happen" catches one exception.
    for cls in (MypyNotInstalled, MypyFailed, MypyUnintelligible):
        assert issubclass(cls, ArchetypesUnread)


def test_a_genuinely_clean_run_is_an_empty_list():
    assert interpret(OracleRun("", "", 0), [], None) == []


# --- carrier noise ---------------------------------------------------------


def test_the_litany_carrier_is_filtered():
    lines, smap = mapping_of('litany("Ave"):\n    intone("one")\n')
    out = interpret(
        OracleRun('p.py:1:6: error: Name "__litany__" is not defined  [name-defined]\n', "", 1),
        lines,
        smap,
    )
    assert out == []


def test_the_augur_carrier_is_filtered():
    lines, smap = mapping_of("augur:\n    intone('two')\n")
    out = interpret(
        OracleRun('p.py:1:6: error: Name "__augur__" is not defined  [name-defined]\n', "", 1),
        lines,
        smap,
    )
    assert out == []


def test_a_carrier_this_module_never_heard_of_is_filtered_too():
    # The filter asks `constructs.is_machine_name`, not a list of strings
    # written down here. A carrier added later must not leak because nobody
    # remembered to update this module.
    name = f"{MACHINE_PREFIX}future"
    out = interpret(
        OracleRun(f'p.py:1:1: error: Name "{name}" is not defined  [name-defined]\n', "", 1),
        [""],
        None,
    )
    assert out == []


def test_notes_belonging_to_a_filtered_error_go_with_it():
    stdout = (
        'p.py:1:6: error: Name "__litany__" is not defined  [name-defined]\n'
        "p.py:1:6: note: did you forget to import it\n"
    )
    lines, smap = mapping_of('litany("Ave"):\n    intone("one")\n')
    assert interpret(OracleRun(stdout, "", 1), lines, smap) == []


def test_a_note_at_another_position_survives_a_filtered_error():
    stdout = (
        'p.py:1:6: error: Name "__litany__" is not defined  [name-defined]\n'
        'p.py:2:1: error: Boom  [misc]\n'
        "p.py:2:1: note: because of this\n"
    )
    lines, smap = mapping_of('litany("Ave"):\n    intone("one")\n')
    out = interpret(OracleRun(stdout, "", 1), lines, smap)
    assert [(f.line, f.severity) for f in out] == [(2, "error"), (2, "note")]


def test_an_ordinary_undefined_name_is_not_filtered():
    lines, smap = mapping_of("intone(nowhere)\n")
    out = interpret(
        OracleRun('p.py:1:7: error: Name "nowhere" is not defined  [name-defined]\n', "", 1),
        lines,
        smap,
    )
    assert [f.message for f in out] == ['Name "nowhere" is not defined']


def test_a_carrier_named_in_another_kind_of_error_is_kept():
    # Only `name-defined` is noise. Anything else naming a carrier is a
    # genuine surprise and must be seen.
    lines, smap = mapping_of("intone('ave')\n")
    out = interpret(
        OracleRun('p.py:1:1: error: "__litany__" has no attribute "x"  [attr-defined]\n', "", 1),
        lines,
        smap,
    )
    assert len(out) == 1


def test_a_run_that_is_all_carrier_noise_is_an_honest_empty_list():
    stdout = (
        'p.py:1:6: error: Name "__litany__" is not defined  [name-defined]\n'
        'p.py:4:6: error: Name "__augur__" is not defined  [name-defined]\n'
    )
    src = 'litany("Ave"):\n    intone("one")\n\naugur:\n    intone("two")\n'
    lines, smap = mapping_of(src)
    assert interpret(OracleRun(stdout, "", 1), lines, smap) == []


# --- mapping back to the litany --------------------------------------------


def test_the_line_needs_no_mapping_at_all():
    src = "rite greet(name: str) -> int:\n    render name\n"
    lines, smap = mapping_of(src)
    d = Diagnostic("prayer.py", 2, 12, "error", "Incompatible return value type", "return-value")
    assert to_finding(d, lines, smap).line == 2


def test_the_column_comes_back_through_the_substitutions():
    # `intone(` is seven characters and `print(` is six, so the litany's
    # column is one further right than the generated Python's.
    src = 'intone(PORT + "nine")\n'
    lines, smap = mapping_of(src)
    d = Diagnostic("p.py", 1, 14, "error", "Unsupported operand types", "operator")
    assert to_finding(d, lines, smap).col == 14
    assert src.splitlines()[0][14:] == '"nine")'


def test_a_one_based_column_becomes_zero_based():
    lines, smap = mapping_of("intone(nowhere)\n")
    # mypy's column 7 is the generated `print(nowhere)`'s 0-based 6, which
    # `to_lit` carries across the one-character-wider `intone`.
    d = Diagnostic("p.py", 1, 7, "error", 'Name "nowhere" is not defined', "name-defined")
    finding = to_finding(d, lines, smap)
    assert finding.col == 7
    assert "intone(nowhere)"[7:] == "nowhere)"


def test_mypy_counts_bytes_and_the_finding_counts_characters():
    # mypy's columns are UTF-8 byte offsets, like `ast`'s and `traceback`'s.
    # A multi-byte name earlier on the row would otherwise skew the caret.
    src = 'intone("ζζζζ", nowhere)\n'
    lines, smap = mapping_of(src)
    py = lines[0]
    byte_col = len(py[: py.index("nowhere")].encode("utf-8")) + 1
    assert byte_col != py.index("nowhere") + 1  # the trap is real
    d = Diagnostic("p.py", 1, byte_col, "error", 'Name "nowhere" is not defined', "name-defined")
    assert to_finding(d, lines, smap).col == src.index("nowhere")


def test_a_missing_column_stays_missing():
    d = Diagnostic("p.py", 1, None, "error", "Cannot find implementation", "import")
    assert to_finding(d, [""], None).col is None


def test_a_finding_is_frozen_and_slotted():
    f = Finding(1, 0, "m", "misc", "error")
    with pytest.raises(Exception):
        f.line = 2
    assert not hasattr(f, "__dict__")


# --- what `check` hands the oracle -----------------------------------------


def test_the_temp_file_keeps_the_litany_s_name():
    seen = []
    check("intone('ave')\n", "/where/ever/prayer.lit", oracle=fake_oracle(seen=seen))
    (path, _cache), = seen
    assert path.name == "prayer.py"


def test_the_cache_lives_under_the_temp_directory_not_the_project():
    seen = []
    check("intone('ave')\n", "prayer.lit", oracle=fake_oracle(seen=seen))
    (path, cache), = seen
    assert cache.parent == path.parent
    assert pathlib.Path.cwd() not in cache.parents


def test_the_temp_directory_is_gone_afterwards():
    seen = []
    check("intone('ave')\n", "prayer.lit", oracle=fake_oracle(seen=seen))
    (path, _cache), = seen
    assert not path.parent.exists()


def test_the_oracle_is_handed_the_generated_python():
    written = {}

    def run(path, cache_dir):
        written["text"] = path.read_text(encoding="utf-8")
        return OracleRun("", "", 0)

    check("intone('ave')\n", "prayer.lit", oracle=run)
    assert written["text"] == "print('ave')\n"


@pytest.mark.parametrize(
    "filename,stem",
    [
        ("prayer.lit", "prayer"),
        ("<litany>", "litany"),
        ("/a/b/c.lit", "c"),
        (".hidden.lit", "hidden"),
        ("odd name!.lit", "odd_name"),
        ("...", "litany"),
    ],
)
def test_the_module_name_is_the_litany_s_own_where_it_can_be(filename, stem):
    assert _module_stem(filename) == stem


# --- a litany that is not code at all --------------------------------------


def refuse(path, cache_dir):
    raise AssertionError("mypy must not be run on a litany that does not parse")


def test_a_litany_that_does_not_parse_is_not_a_type_finding():
    # This tokenises and substitutes cleanly -- `intone` becomes `print`
    # -- and is only rejected once something parses it. mypy would call it
    # `Invalid syntax`; a syntax error naming the substitution is the
    # better report, and it is not a type finding either way.
    with pytest.raises(SyntaxError):
        check("intone(1 2)\n", "prayer.lit", oracle=refuse)


def test_a_litany_the_tokeniser_rejects_is_not_a_type_finding():
    # A dedent matching no outer level -- `transform` never gets as far as
    # producing Python for this one.
    with pytest.raises(IndentationError):
        check("rite greet():\n        pass\n    pass\n", "prayer.lit", oracle=refuse)


def test_an_unfinished_litany_is_not_a_type_finding():
    with pytest.raises(UnfinishedLitany):
        check("intone('ave'\n", "prayer.lit", oracle=refuse)


# --- the oracle itself -----------------------------------------------------


def test_an_interpreter_without_mypy_refuses_before_running_anything():
    oracle = mypy_oracle(sys.executable if not mypy_available() else "/no/such/python")
    with pytest.raises(MypyNotInstalled):
        check("intone('ave')\n", "prayer.lit", oracle=oracle)


def test_an_interpreter_that_does_not_exist_cannot_run_mypy():
    assert mypy_available("/no/such/python") is False


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
def test_a_false_archetype_lands_on_the_right_line_and_column():
    src = (
        "rite greet(name: str) -> int:\n"
        "    render name\n"
        "\n"
        "rite add(a: int, b: int) -> int:\n"
        "    render a + b\n"
        "\n"
        'intone(add("one", 2))\n'
    )
    findings = check(src, "prayer.lit", oracle=mypy_oracle(MYPY))
    assert [(f.line, f.col, f.code) for f in findings] == [
        (2, 11, "return-value"),
        (7, 11, "arg-type"),
    ]
    lines = src.splitlines()
    assert lines[1][11:] == "name"
    assert lines[6][11:] == '"one", 2))'


@needs_mypy
def test_a_true_litany_yields_nothing():
    src = "rite add(a: int, b: int) -> int:\n    render a + b\n\nintone(add(1, 2))\n"
    assert check(src, "prayer.lit", oracle=mypy_oracle(MYPY)) == []


@needs_mypy
def test_the_real_carriers_are_filtered_from_a_real_run():
    src = (
        'litany("Ave"):\n'
        '    intone("one")\n'
        "\n"
        "augur:\n"
        '    intone("two")\n'
        "\n"
        "consecrated PORT: int = 8080\n"
        'intone(PORT + "nine")\n'
    )
    findings = check(src, "prayer.lit", oracle=mypy_oracle(MYPY))
    assert [(f.line, f.col, f.code) for f in findings] == [(8, 14, "operator")]
    assert src.splitlines()[7][14:] == '"nine")'


@needs_mypy
def test_the_message_is_mypy_s_own_words_for_now():
    # Task 3 translates these. Until then they arrive verbatim.
    src = "rite greet(name: str) -> int:\n    render name\n"
    (finding,) = check(src, "prayer.lit", oracle=mypy_oracle(MYPY))
    assert finding.message == (
        'Incompatible return value type (got "str", expected "int")'
    )
    assert finding.severity == "error"
