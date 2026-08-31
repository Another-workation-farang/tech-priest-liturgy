import builtins
import keyword

import pytest

from liturgy import lexicon


def test_every_python_keyword_has_exactly_one_alias():
    targets = set(lexicon.KEYWORDS.values())
    missing = set(keyword.kwlist) - targets
    assert not missing, f"unthemed keywords: {sorted(missing)}"


def test_soft_keywords_are_aliased_except_underscore():
    targets = set(lexicon.KEYWORDS.values())
    missing = (set(keyword.softkwlist) - {"_"}) - targets
    assert not missing, f"unthemed soft keywords: {sorted(missing)}"


def test_underscore_is_deliberately_unaliased():
    assert "_" not in lexicon.LEXICON.values()


def test_lexicon_is_bijective():
    assert len(lexicon.INVERSE) == len(lexicon.LEXICON)


def test_tables_do_not_overlap():
    keys = [*lexicon.KEYWORDS, *lexicon.SOFTWORDS, *lexicon.CURSES]
    assert len(keys) == len(set(keys))


def test_no_liturgy_word_is_also_a_python_keyword():
    # A Liturgy word that is itself a Python keyword would be substituted
    # into something else and break plain-Python compatibility.
    assert not (set(lexicon.LEXICON) & set(keyword.kwlist))


# I8 — nothing validated that a target actually exists. A typo'd
# `"unseal": "openn"` or `"MotiveFailure": "RuntimError"` passed the suite.
@pytest.mark.parametrize(
    "lit,target", sorted(lexicon.KEYWORDS.items()), ids=sorted(lexicon.KEYWORDS)
)
def test_every_keyword_target_is_a_real_python_keyword(lit, target):
    assert target in set(keyword.kwlist) | set(keyword.softkwlist)


@pytest.mark.parametrize(
    "lit,target", sorted(lexicon.SOFTWORDS.items()), ids=sorted(lexicon.SOFTWORDS)
)
def test_every_softword_target_is_a_real_builtin(lit, target):
    assert hasattr(builtins, target)


@pytest.mark.parametrize(
    "lit,target", sorted(lexicon.CURSES.items()), ids=sorted(lexicon.CURSES)
)
def test_every_curse_target_is_a_real_exception_class(lit, target):
    cls = getattr(builtins, target, None)
    assert isinstance(cls, type), f"{target!r} is not a builtin"
    assert issubclass(cls, BaseException)


def test_numerals_substitute_to_integer_literals():
    assert lexicon.NUMERALS == {"twice": "2", "thrice": "3"}


@pytest.mark.parametrize("lit,target", sorted(lexicon.NUMERALS.items()))
def test_every_numeral_target_is_a_decimal_integer(lit, target):
    assert target.isdigit(), f"{lit} -> {target} is not an integer literal"


def test_numerals_are_in_the_lexicon():
    # They substitute like any other alias, everywhere -- `x = thrice` is `x = 3`.
    assert lexicon.LEXICON["thrice"] == "3"


def test_construct_keywords_map_to_no_python_word():
    # They are recognised by the carrier pass, not substituted by the alias pass.
    assert not (lexicon.CONSTRUCT_KEYWORDS & set(lexicon.LEXICON))


def test_reserved_is_the_union_of_every_taken_word():
    assert lexicon.RESERVED == set(lexicon.LEXICON) | lexicon.CONSTRUCT_KEYWORDS


def test_reserved_count_is_sixty_three():
    # 38 keywords + 5 builtins + 15 curses + 2 numerals + 3 constructs.
    assert len(lexicon.RESERVED) == 63


def test_numerals_do_not_break_bijectivity():
    assert len(lexicon.INVERSE) == len(lexicon.LEXICON)
