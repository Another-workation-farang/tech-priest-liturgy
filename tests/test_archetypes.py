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
    translate,
)
from liturgy.compiler import _PASSES
from liturgy.constructs import MACHINE_PREFIX
from liturgy.lexicon import INVERSE
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
    assert [f.message for f in out] == ["nothing named nowhere is known here"]


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


# --- translation -----------------------------------------------------------
#
# Pure string work, so all of it runs with no mypy installed. Every message
# below was printed by a real mypy first; the shapes are transcribed, not
# imagined.


TRANSLATED = [
    (
        "return-value",
        'Incompatible return value type (got "str", expected "int")',
        "this rite renders a str where it declared an int",
    ),
    (
        "return-value",
        "No return value expected",
        "this rite renders a value where it declared Void",
    ),
    (
        "return",
        "Missing return statement",
        "this rite declares an archetype it never renders",
    ),
    (
        "arg-type",
        'Argument 1 to "add" has incompatible type "str"; expected "int"',
        "argument 1 to add is a str where add declares an int",
    ),
    (
        "arg-type",
        'Argument "b" to "add" has incompatible type "str"; expected "int"',
        "argument b to add is a str where add declares an int",
    ),
    (
        "arg-type",
        'Argument 1 to "add" of "Forge" has incompatible type "str"; '
        'expected "int"',
        "argument 1 to add of Forge is a str where add declares an int",
    ),
    (
        "assignment",
        'Incompatible types in assignment (expression has type "str", '
        'variable has type "int")',
        "this binds a str to a name declared an int",
    ),
    (
        "assignment",
        'Incompatible types in assignment (expression has type "str", '
        'base class "A" defined the type as "int")',
        "this binds a str where the pattern A declared an int",
    ),
    (
        "operator",
        'Unsupported operand types for + ("int" and "str")',
        "an int and a str cannot be joined by +",
    ),
    (
        "operator",
        'Unsupported operand types for > ("str" and "int")',
        "a str and an int cannot be joined by >",
    ),
    (
        "name-defined",
        'Name "nowhere" is not defined',
        "nothing named nowhere is known here",
    ),
    (
        "attr-defined",
        '"str" has no attribute "shout"',
        "a str bears no attribute shout",
    ),
    (
        "call-arg",
        'Too many arguments for "add"',
        "add is given more arguments than it declares",
    ),
    (
        "call-arg",
        'Missing positional argument "b" in call to "add"',
        "add is called without its argument b",
    ),
    (
        "call-arg",
        'Missing positional arguments "b", "c" in call to "add"',
        "add is called without its arguments b, c",
    ),
    (
        "call-arg",
        'Unexpected keyword argument "c" for "add"',
        "add declares no parameter c",
    ),
]


@pytest.mark.parametrize("code,mypy_says,liturgy_says", TRANSLATED)
def test_a_shape_this_module_knows_is_said_in_liturgy(code, mypy_says, liturgy_says):
    assert translate(mypy_says, code) == (liturgy_says, True)


def test_no_translated_message_still_speaks_python():
    # The half-translated diagnostic is the failure this module exists to
    # avoid: a Python keyword surviving inside a Liturgy sentence.
    python_words = ("def ", "return", "class ", "argument type", "None")
    for _code, _before, after in TRANSLATED:
        assert not any(word in after for word in python_words), after


PASSED_THROUGH = [
    # A known code whose shape this module does not recognise. mypy appends
    # a hint here, and the anchored pattern must miss rather than drop it.
    ("attr-defined", '"int" has no attribute "__iter__"; maybe "__int__"? (not iterable)'),
    # The unary form of an operator error, worded differently from the
    # binary one.
    ("operator", 'Unsupported operand type for unary - ("str")'),
    # A word operator. `in` is `among` in Liturgy, but the sentence around
    # it would still be half Python, so the whole message passes through.
    # mypy really does say this: `"x" in (n for n in range(3))`.
    ("operator", 'Unsupported operand types for in ("str" and "Generator[int, None, None]")'),
    ("operator", 'Unsupported right operand type for in ("int")'),
    # The variant mypy prints when it has been told not to name types.
    ("operator", "Unsupported operand types for + (likely involving Union)"),
    # A module attribute, where the owner is not a quoted type at all.
    ("attr-defined", 'Module has no attribute "nope"'),
    # Codes outside the translated set entirely.
    ("var-annotated", 'Need type annotation for "xs" (hint: "xs: list[<type>] = ...")'),
    ("union-attr", 'Item "None" of "str | None" has no attribute "upper"'),
    ("no-redef", 'Name "go" already defined on line 1'),
    ("index", 'Value of type "int" is not indexable'),
    ("list-item", 'List item 1 has incompatible type "str"; expected "int"'),
    ("type-arg", '"list" expects 1 type argument, but 2 given'),
    ("call-overload", 'No overload variant of "fspath" matches argument type "int"'),
    ("truthy-function", 'Function "len" could always be true in boolean context'),
]


@pytest.mark.parametrize("code,mypy_says", PASSED_THROUGH)
def test_a_shape_this_module_does_not_know_passes_through_unharmed(code, mypy_says):
    assert translate(mypy_says, code) == (mypy_says, False)


def test_a_note_is_never_translated():
    # A note continues the error above it and reads as a fragment alone. It
    # is the checker's commentary on its own reasoning, so it stays the
    # checker's words.
    assert translate("This violates the Liskov substitution principle", None, "note") == (
        "This violates the Liskov substitution principle",
        False,
    )


def test_a_note_carrying_python_source_is_not_rewritten():
    note = "    def fspath(path: str) -> str"
    assert translate(note, None, "note") == (note, False)


def test_a_type_name_is_never_substituted():
    # `archetype` is Liturgy's word for `type`, but `int` is still `int`,
    # and `ValueError` inside a type name is not certainly `ImpureOffering`
    # -- a litany may spell either. Type names are copied, never rewritten.
    text, ok = translate(
        'Incompatible return value type (got "ValueError", expected "int")',
        "return-value",
    )
    assert ok
    assert "ValueError" in text
    assert "ImpureOffering" not in text


def test_a_composite_type_name_survives_whole():
    text, ok = translate(
        'Incompatible return value type (got "dict[str, ValueError]", '
        'expected "list[int]")',
        "return-value",
    )
    assert ok
    assert "dict[str, ValueError]" in text
    assert "list[int]" in text


def test_an_identifier_the_lexicon_knows_is_left_alone():
    # `print` is `intone`'s Python spelling. Here it is a name the author
    # chose, in a name position, and rewriting it would report a fault in
    # code nobody wrote.
    assert translate('Name "print" is not defined', "name-defined") == (
        "nothing named print is known here",
        True,
    )


def test_a_callee_named_for_a_reserved_word_is_left_alone():
    text, ok = translate(
        'Argument 1 to "type" has incompatible type "str"; expected "int"',
        "arg-type",
    )
    assert ok
    assert text == "argument 1 to type is a str where type declares an int"


@pytest.mark.parametrize(
    "python,code,mypy_says",
    [
        ("def", "return-value", 'Incompatible return value type (got "str", expected "int")'),
        ("return", "return-value", 'Incompatible return value type (got "str", expected "int")'),
        ("None", "return-value", "No return value expected"),
        ("type", "return", "Missing return statement"),
        (
            "class",
            "assignment",
            'Incompatible types in assignment (expression has type "str", '
            'base class "A" defined the type as "int")',
        ),
    ],
)
def test_the_liturgy_words_come_from_the_lexicon(monkeypatch, python, code, mypy_says):
    # Rename the word in the lexicon and the diagnostic renames with it.
    # A word spelled out in `archetypes` instead would ignore this and the
    # test would go red -- which is the point of renaming rather than
    # asserting the current spelling.
    monkeypatch.setitem(INVERSE, python, "ANOTHERWORD")
    text, ok = translate(mypy_says, code)
    assert ok
    assert "ANOTHERWORD" in text


def test_a_note_that_somehow_carries_a_code_is_still_not_translated():
    # mypy does not put codes on notes today. If it starts, a note must
    # still not be read as a statement about the litany.
    assert translate("Missing return statement", "return", "note") == (
        "Missing return statement",
        False,
    )


@pytest.mark.parametrize(
    "archetype,article",
    [("int", "an"), ("str", "a"), ("object", "an"), ("float", "a"), ("Any", "an")],
)
def test_the_article_agrees_with_the_type_name(archetype, article):
    text, ok = translate(
        f'Incompatible return value type (got "{archetype}", expected "bytes")',
        "return-value",
    )
    assert ok
    assert f"{article} {archetype}" in text


def test_a_diagnostic_with_no_code_at_all_passes_through():
    assert translate("something mypy said", None) == ("something mypy said", False)


def test_a_finding_says_whose_words_it_carries():
    lines, smap = mapping_of("rite greet(name: str) -> int:\n    render name\n")
    out = interpret(
        OracleRun(
            'p.py:2:12: error: Incompatible return value type '
            '(got "str", expected "int")  [return-value]\n'
            'p.py:2:12: error: Value of type "int" is not indexable  [index]\n',
            "",
            1,
        ),
        lines,
        smap,
    )
    assert [(f.translated, f.message) for f in out] == [
        (True, "this rite renders a str where it declared an int"),
        (False, 'Value of type "int" is not indexable'),
    ]


def test_an_untranslated_finding_is_the_honest_default():
    # A `Finding` built without the flag claims nothing about whose words it
    # carries, which is the safe half of the claim.
    assert Finding(1, 0, "m", "misc", "error").translated is False


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
def test_a_real_diagnostic_arrives_in_liturgy():
    src = "rite greet(name: str) -> int:\n    render name\n"
    (finding,) = check(src, "prayer.lit", oracle=mypy_oracle(MYPY))
    assert finding.message == "this rite renders a str where it declared an int"
    assert finding.translated is True
    assert finding.severity == "error"


@needs_mypy
def test_a_real_diagnostic_this_module_does_not_know_arrives_whole():
    # `var-annotated` is not in the translated set, and its message carries a
    # parenthesised hint written in Python. It reaches the reader as mypy
    # wrote it, marked the checker's own.
    src = "rite go() -> Void:\n    xs = []\n"
    (finding,) = check(src, "prayer.lit", oracle=mypy_oracle(MYPY))
    assert finding.message == (
        'Need type annotation for "xs" (hint: "xs: list[<type>] = ...")'
    )
    assert finding.translated is False


@needs_mypy
def test_a_real_note_is_never_translated():
    src = (
        "pattern A:\n"
        "    rite f(self, a: int) -> Void:\n"
        "        abide\n"
        "\n"
        "pattern B(A):\n"
        "    rite f(self, a: str) -> Void:\n"
        "        abide\n"
    )
    findings = check(src, "prayer.lit", oracle=mypy_oracle(MYPY))
    notes = [f for f in findings if f.severity == "note"]
    assert notes
    assert all(f.translated is False for f in notes)
    assert notes[0].message == "This violates the Liskov substitution principle"
