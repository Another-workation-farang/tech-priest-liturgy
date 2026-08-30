import textwrap

import pytest

from liturgy._reverse import to_liturgy
from liturgy.transform import transform

SAMPLES = [
    textwrap.dedent(
        """\
        def fib(n):
            if n < 2:
                return n
            return fib(n - 1) + fib(n - 2)
        """
    ),
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
    textwrap.dedent(
        """\
        async def go(items):
            async with lock:
                return [x async for x in items if x is not None]
        """
    ),
    # --- Task 4 fix coverage --------------------------------------------
    #
    # Each sample below is deliberately narrow: its *only* translatable
    # content is the construct under test. That matters because a single
    # missed substitution is otherwise invisible to a round-trip check —
    # valid Python left untranslated by the reverse pass is still valid
    # Python, and reappears unchanged on the way back through `transform`.
    # If a sample also had unrelated translatable content, that content
    # succeeding would satisfy the `lit != src` guard and mask a regression
    # in the construct actually under test. Keeping each sample narrow
    # means a regression drives that sample's substitution count to zero,
    # which the guard catches directly.
    #
    # Fix 1 (relative-import dot) + the import-safe set: plain import and
    # `from ... import ... as ...`.
    textwrap.dedent(
        """\
        import os
        from collections import OrderedDict as OD
        """
    ),
    # Fix 1: relative imports specifically (single- and double-dot).
    textwrap.dedent(
        """\
        from . import sibling
        from ..pkg import helper as helper2
        """
    ),
    # Fix 2: import scope must end at a semicolon, not just at NEWLINE, so
    # the statement following `;` is still translated.
    textwrap.dedent(
        """\
        import os; value = True
        """
    ),
    # Fix 3: PEP 701 f-string debug (`{name=}`) and debug-plus-format-spec
    # (`{name=:>10}`) syntax must not be mistaken for a keyword argument.
    textwrap.dedent(
        """\
        f"{len=}"
        f"{len=:>10}"
        """
    ),
    # Fix 3, other side: a genuine keyword argument inside an f-string
    # expression must still be protected by the kwarg rule.
    textwrap.dedent(
        """\
        print(f"{fn(print=1)}")
        """
    ),
]


@pytest.mark.parametrize("src", SAMPLES, ids=range(len(SAMPLES)))
def test_python_to_liturgy_and_back_is_identity(src):
    lit = to_liturgy(src)
    assert lit != src, "reverse pass produced no Liturgy words"
    assert transform(lit)[0] == src
