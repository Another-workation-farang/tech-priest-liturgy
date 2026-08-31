import ast
import io
import tokenize

import pytest

from liturgy.collisions import find_collisions
from test_roundtrip import CORPUS_FLOOR, _corpus, _liturgy_word_as_identifier


def test_augur_agrees_with_the_sweeps_skip_predicate(capsys):
    """Every file the sweep skips, augur should flag -- and vice versa.

    The predicates are written differently: the sweep scans tokens, augur
    walks bindings. Where they disagree, one of them is wrong, and this is
    the only place that would notice.

    That equivalence holds for *bindings*, which is the only shape the
    corpus currently contains. It is not universal: a bare Load of a
    Liturgy word (`d = {thrice: 1}`, `a[thrice:1]`) still breaks the round
    trip -- the sweep is correct to flag it -- but binds nothing, so augur
    (which reports bindings only) correctly does not. Both predicates
    would be right on their own narrower question in that case, and
    neither should change to "fix" it. If this assertion ever fails on a
    file that turns out to be a bare load rather than a binding, that is
    not automatically a regression in either predicate -- check which
    question is actually being asked before touching either.
    """
    files = _corpus()
    assert len(files) >= CORPUS_FLOOR, "corpus discovery is broken"

    checked = disagreements = 0
    detail = []
    for path in files:
        try:
            src = path.read_text(encoding="utf-8")
            ast.parse(src)
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        checked += 1
        # NOTE: the predicate takes a token list, not source text.
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
        skipped = _liturgy_word_as_identifier(toks)
        flagged = bool(find_collisions(src, str(path), liturgy=False))
        if skipped != flagged:
            disagreements += 1
            if len(detail) < 10:
                detail.append(f"{path.name}: sweep={skipped} augur={flagged}")

    with capsys.disabled():
        print(f"\naugur/sweep cross-check: {checked} files, {disagreements} disagree")
    assert not disagreements, "\n".join(detail)


# --- The three shapes ruling (c) exists for --------------------------------
#
# The brief's own prescribed fix -- "skip a NAME immediately followed by `=`
# at paren depth greater than zero" -- cannot tell a call-site keyword
# argument apart from a def/lambda parameter default. The corpus does not
# contain the latter two shapes today, so a too-broad fix would pass the
# cross-check above green and sit as a trap for whoever adds one later.
# These three cases are the whole point and must not rely on the corpus.
@pytest.mark.parametrize(
    "src,should_be_flagged",
    [
        ("increment_count(thrice=3)\n", False),
        ("def f(thrice=3): pass\n", True),
        ("f = lambda thrice=3: thrice\n", True),
    ],
    ids=["call-site kwarg", "def parameter default", "lambda parameter default"],
)
def test_augur_and_sweep_agree_on_kwarg_vs_parameter_default(src, should_be_flagged):
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    skipped = _liturgy_word_as_identifier(toks)
    flagged = bool(find_collisions(src, "<test>", liturgy=False))
    assert flagged is should_be_flagged
    assert skipped is should_be_flagged


# --- Regression: PEP 701 f-string debug syntax is not a kwarg -------------
#
# `f"{thrice=}"` tokenizes NAME then a bare `=` one bracket deep, exactly
# the shape the kwarg exemption looks for -- but the enclosing bracket is
# an f-string's `{`, not a call's `(`. A version of the exemption keyed on
# depth alone (rather than the innermost bracket's own character) wrongly
# exempts it, and the round trip genuinely breaks: `to_liturgy` then
# `transform` turns `f"{thrice=}"` into `f"{3=}"`, a different program.
#
# This is a bare Load, not a binding (see the docstring above), so augur
# correctly does *not* flag it -- only the sweep predicate is asserted on
# here, not agreement between the two.
@pytest.mark.parametrize(
    "src",
    [
        'x = f"{thrice=}"\n',
        'f = lambda x=f"{thrice=}": x\n',
    ],
    ids=["f-string debug at statement level", "f-string debug in a lambda default"],
)
def test_sweep_flags_fstring_debug_syntax_as_a_reserved_word(src):
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    assert _liturgy_word_as_identifier(toks) is True


def test_sweep_still_exempts_a_plain_call_site_kwarg():
    # Guards against a fix that "solves" the above by flagging everything.
    toks = list(tokenize.generate_tokens(io.StringIO("f(thrice=3)\n").readline))
    assert _liturgy_word_as_identifier(toks) is False
