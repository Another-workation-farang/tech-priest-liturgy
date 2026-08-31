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
