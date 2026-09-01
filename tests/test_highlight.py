"""The Pygments lexer: the real transform decides what is Liturgy.

Highlighting is not a linter -- `span = 1` still paints `span` as the
builtin it becomes -- but it must respect the three prohibitions and the
construct-header rules exactly, because a word those rules exempt is not
Liturgy and colouring it as Liturgy lies about what will run.
"""

import pytest

pygments = pytest.importorskip("pygments")

from pygments.token import (  # noqa: E402
    Error,
    Keyword,
    Name,
    Number,
    Operator,
    String,
)

from liturgy.highlight import LiturgyLexer  # noqa: E402


def tokens_of(src):
    """[(token_type, value), ...] with whitespace dropped."""
    return [
        (tok, value)
        for _, tok, value in LiturgyLexer().get_tokens_unprocessed(src)
        if value.strip()
    ]


def token_for(src, word):
    matches = [tok for tok, value in tokens_of(src) if value == word]
    assert matches, f"{word!r} not tokenized in {src!r}"
    assert len(set(matches)) == 1, f"{word!r} tokenized inconsistently"
    return matches[0]


# -- the lexicon, painted --------------------------------------------------


def test_ritual_keywords_are_keywords():
    src = "rite f(x):\n    should x:\n        render x\n"
    assert token_for(src, "rite") in Keyword
    assert token_for(src, "should") in Keyword
    assert token_for(src, "render") in Keyword


def test_python_spellings_still_highlight():
    src = "def f(x):\n    if x:\n        return x\n"
    assert token_for(src, "def") in Keyword
    assert token_for(src, "return") in Keyword


def test_truth_and_void_are_constants():
    src = "x = Sanctioned\ny = Heretical\nz = Void\n"
    for word in ("Sanctioned", "Heretical", "Void"):
        assert token_for(src, word) in Keyword.Constant


def test_word_operators_match_their_python_kin():
    src = "x = a likewise b elsewise nay c\ny = a be b\nz = a among b\n"
    for word in ("likewise", "elsewise", "nay", "be", "among"):
        assert token_for(src, word) in Operator.Word


def test_builtin_aliases_are_builtins():
    src = "intone(measure(span(3)))\n"
    for word in ("intone", "measure", "span"):
        assert token_for(src, word) in Name.Builtin


def test_curse_names_are_exceptions():
    src = "proclaim MachineCurse(ImpureOffering)\n"
    assert token_for(src, "MachineCurse") in Name.Exception
    assert token_for(src, "ImpureOffering") in Name.Exception


def test_numerals_are_numbers():
    src = "x = twice + thrice\n"
    assert token_for(src, "twice") in Number
    assert token_for(src, "thrice") in Number


# -- the three prohibitions -------------------------------------------------


def test_attribute_position_is_not_liturgy():
    src = "x = template.render()\n"
    assert token_for(src, "render") not in Keyword


def test_keyword_argument_position_is_not_liturgy():
    src = "f(intone=1)\n"
    assert token_for(src, "intone") not in Name.Builtin


def test_import_targets_are_not_liturgy():
    src = "within json invoke loads styled parse_json\n"
    assert token_for(src, "within") in Keyword
    assert token_for(src, "invoke") in Keyword
    assert token_for(src, "styled") in Keyword
    assert token_for(src, "loads") not in Keyword


def test_fstring_interiors_are_liturgy():
    src = 'x = [1]\nintone(f"{measure(x)}")\n'
    assert token_for(src, "measure") in Name.Builtin


# -- constructs: a construct word is only a construct in header position ----


def test_construct_headers_are_keywords():
    src = (
        "consecrated PORT = 8080\n"
        "litany(thrice, curse=MachineCurse):\n"
        "    abide\n"
    )
    assert token_for(src, "consecrated") in Keyword
    assert token_for(src, "litany") in Keyword


def test_a_consecrated_name_is_the_authors_own():
    # The carrier rewrites the name too; the paint must not follow it.
    src = "consecrated PORT = 8080\n"
    assert token_for(src, "PORT") not in Keyword


def test_augur_header_is_a_keyword():
    src = "rite f(x):\n    augur:\n        x > 0\n    render x\n"
    assert token_for(src, "augur") in Keyword


def test_a_construct_word_elsewhere_is_a_plain_name():
    src = "litany = 5\nx = augur\n"
    assert token_for(src, "litany") not in Keyword
    assert token_for(src, "augur") not in Keyword


# -- the machine's own names ------------------------------------------------


def test_machine_names_are_errors():
    src = "x = __litany__\n"
    assert token_for(src, "__litany__") in Error


def test_machine_names_after_a_dot_are_left_alone():
    src = "x = spirit.__litany__\n"
    assert token_for(src, "__litany__") not in Error


# -- what highlighting must never touch --------------------------------------


def test_strings_and_comments_are_untouched():
    src = '# render nothing\nx = "render"\n'
    toks = tokens_of(src)
    assert all(
        tok not in Keyword for tok, value in toks if "render" in value
    )
    assert any(
        tok in String for tok, value in toks if "render" in value
    )


def test_broken_source_still_highlights():
    # Mid-edit source that will not tokenize must degrade, never crash;
    # the fallback paints by word alone.
    src = "rite f(:\n    render ]\n"
    assert token_for(src, "rite") in Keyword


def test_the_lexer_is_registered_by_entry_point():
    from pygments.lexers import get_lexer_by_name

    assert isinstance(get_lexer_by_name("liturgy"), LiturgyLexer)
