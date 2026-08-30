import keyword

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
