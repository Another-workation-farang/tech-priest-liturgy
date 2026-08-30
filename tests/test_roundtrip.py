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
]


@pytest.mark.parametrize("src", SAMPLES, ids=range(len(SAMPLES)))
def test_python_to_liturgy_and_back_is_identity(src):
    lit = to_liturgy(src)
    assert lit != src, "reverse pass produced no Liturgy words"
    assert transform(lit)[0] == src
