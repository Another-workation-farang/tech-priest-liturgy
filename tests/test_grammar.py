"""The VS Code grammar cannot drift from the lexicon.

A TextMate grammar is a hand-written approximation of the transform's rules,
and hand-written lists rot. These tests hold the two ends together the same
way the live-`keyword.kwlist` test holds the lexicon to CPython: a word added
to the lexicon without joining the grammar fails the suite loudly.
"""

import json
import pathlib
import re

from liturgy.constructs import MACHINE_NAMES, MACHINE_PREFIX
from liturgy.lexicon import CONSTRUCT_KEYWORDS, LEXICON

EXTENSION = pathlib.Path(__file__).parent.parent / "editors" / "vscode-liturgy"


def load(name):
    return json.loads((EXTENSION / name).read_text())


def grammar_text():
    return (EXTENSION / "syntaxes" / "liturgy.tmLanguage.json").read_text()


def test_the_extension_files_are_well_formed_json():
    load("package.json")
    load("language-configuration.json")
    load("syntaxes/liturgy.tmLanguage.json")


def test_the_package_claims_the_lit_suffix():
    package = load("package.json")
    languages = package["contributes"]["languages"]
    assert any(".lit" in lang.get("extensions", []) for lang in languages)


def test_the_grammar_is_wired_to_the_language():
    package = load("package.json")
    grammar = load("syntaxes/liturgy.tmLanguage.json")
    contributed = package["contributes"]["grammars"][0]
    assert contributed["scopeName"] == grammar["scopeName"]
    assert contributed["language"] == package["contributes"]["languages"][0]["id"]


def test_every_reserved_word_appears_in_the_grammar():
    text = grammar_text()
    missing = [
        word
        for word in (*LEXICON, *CONSTRUCT_KEYWORDS)
        if not re.search(rf"\b{re.escape(word)}\b", text)
    ]
    assert not missing, f"words absent from the grammar: {missing}"


def test_the_machine_names_appear_in_the_grammar():
    text = grammar_text()
    for name in MACHINE_NAMES:
        assert name in text, f"{name} absent from the grammar"
    assert MACHINE_PREFIX in text


def test_every_grammar_regex_compiles():
    """A typo in a TextMate regex fails silently in the editor; not here.

    Python's `re` is not Oniguruma, but every pattern this grammar uses is
    in their shared dialect -- except an `end` that backreferences its
    `begin` (\\1, \\2), which has no meaning as a standalone pattern and is
    skipped.
    """
    grammar = load("syntaxes/liturgy.tmLanguage.json")

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("match", "begin") and isinstance(value, str):
                    yield value
                elif key == "end" and isinstance(value, str) and not re.search(
                    r"\\\d", value
                ):
                    yield value
                else:
                    yield from walk(value)
        elif isinstance(node, list):
            for item in node:
                yield from walk(item)

    for pattern in walk(grammar):
        re.compile(pattern)
