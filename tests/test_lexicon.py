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
    # T1: NUMERALS belongs here too. LEXICON merges all four with `**`, so a
    # word appearing in two tables is silently resolved by merge order rather
    # than reported -- and the numerals were the one table never checked.
    keys = [
        *lexicon.KEYWORDS,
        *lexicon.SOFTWORDS,
        *lexicon.CURSES,
        *lexicon.NUMERALS,
    ]
    assert len(keys) == len(set(keys))


def test_no_liturgy_word_is_also_a_python_keyword():
    # A Liturgy word that is itself a Python keyword would be substituted
    # into something else and break plain-Python compatibility.
    assert not (set(lexicon.LEXICON) & set(keyword.kwlist))


# I8: nothing validated that a target actually exists. A typo'd
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


def test_reserved_count_is_sixty_five():
    # 38 keywords + 5 builtins + 15 curses + 2 numerals + 5 constructs.
    assert len(lexicon.RESERVED) == 65


def test_numerals_do_not_break_bijectivity():
    # M11: this was byte-identical to test_lexicon_is_bijective and so
    # asserted nothing about numerals at all. The property that actually
    # matters here is that the numerals survive the inversion -- their
    # targets are integer literals, not names, and a target colliding with
    # any other table's would drop one of the two from INVERSE silently.
    assert lexicon.INVERSE["3"] == "thrice"
    assert lexicon.INVERSE["2"] == "twice"
    assert set(lexicon.NUMERALS.values()) <= set(lexicon.INVERSE)


def test_introit_is_a_macro_not_a_spelling():
    # Every other reserved word is one word standing for one word. `introit`
    # stands for `if __name__ == "__main__"` -- a comparison against a
    # particular string -- so it has no Python *spelling* to be a table
    # entry, and `test_lexicon_is_bijective` is what would reject it if it
    # tried. It is a construct word for that reason and no other.
    from liturgy.constructs import INTROIT_GUARD

    assert "introit" in lexicon.CONSTRUCT_KEYWORDS
    assert "introit" not in lexicon.LEXICON
    assert "introit" not in lexicon.INVERSE.values()
    assert INTROIT_GUARD not in lexicon.LEXICON.values()
    assert len(INTROIT_GUARD.split()) > 1


def test_unsanctioned_is_a_construct_word_not_an_alias():
    # A modifier: it generates nothing, so it has no Python spelling and
    # cannot live in a table whose targets are validated against Python.
    assert "unsanctioned" in lexicon.CONSTRUCT_KEYWORDS
    assert "unsanctioned" not in lexicon.LEXICON
    assert "unsanctioned" not in lexicon.INVERSE.values()


def test_sanctioned_and_unsanctioned_coexist():
    # `Sanctioned` is True and `unsanctioned` is the exemption marker. They
    # differ in case, in table, and in position, and this is the check that
    # says so out loud -- a later `Unsanctioned` or `sanctioned` would be
    # the collision, and neither exists.
    assert lexicon.KEYWORDS["Sanctioned"] == "True"
    assert "Sanctioned" not in lexicon.CONSTRUCT_KEYWORDS
    assert "sanctioned" not in lexicon.RESERVED
    assert "Unsanctioned" not in lexicon.RESERVED
    # Bijectivity is unharmed: the modifier is not in LEXICON at all, so it
    # cannot displace anything from INVERSE.
    assert len(lexicon.INVERSE) == len(lexicon.LEXICON)
