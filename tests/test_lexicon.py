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
