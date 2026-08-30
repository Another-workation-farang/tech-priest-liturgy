import io
import math
import pathlib
import re
import sysconfig
import textwrap
import tokenize

import pytest

from _reverse import to_liturgy

from liturgy.lexicon import LEXICON
from liturgy.transform import transform


def _has_word(text: str, word: str) -> bool:
    """Whole-word membership, so e.g. "as" doesn't match inside "case"."""
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


# Each entry is (python_source, required_liturgy_words): every word in the
# second element must appear in the intermediate Liturgy the reverse pass
# produces from the first. This is the primary check, not `lit != src`:
# Liturgy is a superset of Python, so a word the reverse pass fails to
# translate is still valid Python and comes back through `transform`
# unchanged — under-translation is invisible to a round-trip identity
# check alone, no matter how narrow the sample, as long as anything else
# in that sample still translates. Requiring specific words closes that
# hole by checking the intermediate directly, for the exact words each
# construct depends on.
SAMPLES: list[tuple[str, list[str]]] = [
    (
        textwrap.dedent(
            """\
            def fib(n):
                if n < 2:
                    return n
                return fib(n - 1) + fib(n - 2)
            """
        ),
        ["rite", "should", "render"],
    ),
    (
        textwrap.dedent(
            """\
            class Cogitator:
                def __init__(self, name):
                    self.name = name

                def speak(self):
                    for i in range(3):
                        print(f"{self.name}: {i}")
                        if i == 1:
                            continue
                        else:
                            pass
            """
        ),
        ["pattern", "rite", "foreach", "intone", "persist", "otherwise", "abide"],
    ),
    (
        textwrap.dedent(
            """\
            try:
                value = int(input())
            except ValueError as exc:
                raise RuntimeError("bad") from exc
            finally:
                print("done")
            """
        ),
        ["attempt", "curse", "styled", "proclaim", "within", "regardless", "intone"],
    ),
    (
        textwrap.dedent(
            """\
            async def go(items):
                async with lock:
                    return [x async for x in items if x is not None]
            """
        ),
        ["remote", "rite", "anointed", "render", "nay", "Void"],
    ),
    # --- Task 4 fix coverage --------------------------------------------
    #
    # These samples target the exact spots the refactor had to get right,
    # each with an explicit list of words the reverse pass must produce.
    # A regression that stops translating one of them fails immediately,
    # regardless of what else in the sample still translates correctly —
    # which is precisely what `lit != src` could not guarantee (see the
    # module docstring above).
    #
    # Fix 1 / the import-safe set: plain import and
    # `from ... import ... as ...`. Reverting the import-safe set to
    # Python spellings (the realistic regression: reusing
    # `transform._IMPORT_SAFE` directly) suppresses every keyword here.
    (
        textwrap.dedent(
            """\
            import os
            from collections import OrderedDict as OD
            """
        ),
        ["invoke", "within", "styled"],
    ),
    # Fix 1, single-dot: `import` sits directly after the relative-import
    # dot, which is exactly the token pattern Rule 1 (attribute access)
    # would otherwise misread as `dot.attribute`.
    (
        "from . import sibling\n",
        ["invoke"],
    ),
    # Fix 1, double-dot: same shape, two leading dots. Kept separate from
    # the single-dot case (rather than merged into one multi-line sample)
    # because a regression affecting only one of the two would otherwise
    # be masked by the other line's successful translation.
    (
        "from .. import y\n",
        ["invoke"],
    ),
    # Fix 2: import scope must end at a semicolon, not just at NEWLINE.
    # `Sanctioned` is the word that depends on it — it sits after the `;`,
    # so if the semicolon doesn't clear import scope it stays protected
    # (and un-translated) as if it were still part of the import.
    (
        "import os; value = True\n",
        ["invoke", "Sanctioned"],
    ),
    # Fix 3, the "}" branch: PEP 701 f-string debug syntax (`{name=}`)
    # tokenizes a real OP "=" that must not be mistaken for a keyword
    # argument. Kept as its own sample (not merged with the format-spec
    # case below) so a regression in this branch specifically cannot hide
    # behind the other branch's success.
    (
        'f"{len=}"\n',
        ["measure"],
    ),
    # Fix 3, the ":" branch: debug syntax plus a format spec
    # (`{name=:>10}`) exercises the sibling branch of the same guard.
    (
        'f"{len=:>10}"\n',
        ["measure"],
    ),
    # Fix 3, the other side: a genuine keyword argument inside an
    # f-string expression must still be protected by the kwarg rule, even
    # though it sits in the same syntactic position PEP 701 debug syntax
    # does. Only the outer `print` should translate; the inner one is a
    # real kwarg name and must stay put — that half is still guarded by
    # the round-trip check below, since a wrongly-translated kwarg name
    # would come back through `transform` still translated (its own Rule 2
    # would refuse to translate it back), breaking the round trip.
    (
        'print(f"{fn(print=1)}")\n',
        ["intone"],
    ),
]


@pytest.mark.parametrize("src,required", SAMPLES, ids=range(len(SAMPLES)))
def test_python_to_liturgy_and_back_is_identity(src, required):
    lit = to_liturgy(src)
    for word in required:
        assert _has_word(lit, word), f"expected {word!r} in reverse output: {lit!r}"
    assert transform(lit)[0] == src


# --- I9: the same property over real Python files ---------------------------
#
# The spec asks for "real Python files", mechanically reverse-aliased into
# Liturgy and transformed back. The hand-written samples above stay -- they
# carry the required-word assertions, which a corpus sweep cannot -- but they
# are not real files, and a real corpus finds things they cannot. Running
# this against the pre-C2 transform fails on nine files, all of them
# `button.invoke()`.

TRIVIAL = frozenset(
    {tokenize.COMMENT, tokenize.NL, tokenize.INDENT, tokenize.DEDENT}
)

# Bound the sweep: stride the discovered corpus down to about this many
# files, deterministically and spread across the whole tree, so the runtime
# stays roughly constant whatever stdlib happens to be installed.
CORPUS_TARGET = 700
CORPUS_FLOOR = 200  # below this, something is wrong with discovery itself


def _liturgy_word_as_identifier(toks) -> bool:
    """Does this source use a Liturgy word where the forward pass would act?

    That is the documented caveat, not a bug: a Python file with its own
    `def render(...)` cannot survive the round trip, because `render` is how
    Liturgy spells `return`.

    A Liturgy word in *attribute* position is explicitly not covered by the
    caveat -- Rule 1 exists to protect `button.invoke()` and
    `template.render()`, which are attributes on objects the author does not
    own. Those files stay in the corpus; they are the point.
    """
    prev = None
    for tok in toks:
        if tok.type in TRIVIAL:
            continue
        after_dot = (
            prev is not None
            and prev.type == tokenize.OP
            and prev.string == "."
        )
        if tok.type == tokenize.NAME and tok.string in LEXICON and not after_dot:
            return True
        prev = tok
    return False


def _corpus() -> list[pathlib.Path]:
    root = pathlib.Path(sysconfig.get_paths()["stdlib"])
    files = sorted(
        p
        for p in root.rglob("*.py")
        if not {"site-packages", "__pycache__"} & set(p.relative_to(root).parts)
    )
    stride = max(1, math.ceil(len(files) / CORPUS_TARGET))
    return files[::stride]


def test_real_python_files_round_trip_through_liturgy(capsys):
    swept = skipped_word = skipped_unreadable = 0
    failures: list[str] = []

    for path in _corpus():
        try:
            with tokenize.open(str(path)) as fh:
                src = fh.read()
            toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
        except Exception:
            # Deliberately broken fixtures, exotic encodings, syntax from a
            # future or past release. Not our corpus.
            skipped_unreadable += 1
            continue

        if _liturgy_word_as_identifier(toks):
            skipped_word += 1
            continue

        swept += 1
        try:
            back = transform(to_liturgy(src))[0]
        except Exception as exc:  # noqa: BLE001 - report, do not mask
            failures.append(f"{path}: {type(exc).__name__}: {exc}")
            continue
        if back != src:
            failures.append(str(path))

    with capsys.disabled():
        print(
            f"\nround-trip sweep: {swept} swept, {skipped_word} skipped "
            f"(Liturgy word as identifier), {skipped_unreadable} unreadable"
        )

    assert swept >= CORPUS_FLOOR, (
        f"only {swept} files swept (skipped {skipped_word} for a Liturgy "
        f"word, {skipped_unreadable} unreadable) -- a silent near-zero sweep "
        "proves nothing"
    )
    assert not failures, (
        f"{len(failures)} of {swept} real Python files did not round-trip:\n"
        + "\n".join(failures[:20])
    )
