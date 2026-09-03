# Liturgy Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Core of Liturgy, a superset of Python whose surface syntax is Warhammer 40,000 tech-priest ritual language, so alias-only `.lit` programs can be written, imported, run, and debugged with honest tracebacks.

**Architecture:** A pure `transform(src) -> (python_src, SourceMap)` function tokenizes Liturgy source, substitutes NAME tokens against a lexicon, and splices replacements into the original lines without ever adding or removing a line. That line invariant makes traceback line numbers correct for free; the SourceMap exists solely to fix caret columns. A `SourceFileLoader` subclass registered as a path hook compiles `.lit` on import, and a `sys.excepthook` renders themed "machine curses".

**Tech Stack:** Python 3.12+, stdlib only (`tokenize`, `importlib`, `linecache`, `traceback`, `code`, `argparse`, `json`). pytest for tests. hatchling for packaging.

**Spec:** `design/specs/2026-08-30-liturgy-core-design.md`

## Global Constraints

- **Minimum Python 3.12.** Set `requires-python = ">=3.12"`. Driven by f-string tokenization: on 3.12+ f-string internals yield real NAME tokens, so `f"{rite}"` substitutes correctly; on 3.11 and earlier the whole f-string is one opaque STRING token and silently does not.
- **Runtime dependencies: none.** Standard library only. Test-time dependency on pytest is permitted.
- **Line invariant.** The token pass MUST never add or remove a line. Every substitution is line-local. Any change that could alter line count is a defect.
- **Never override `get_source`** on the loader. The inherited `SourceFileLoader.get_source` already returns original `.lit` text, which is what makes `linecache` and tracebacks show Liturgy.
- **The excepthook must never raise.** It wraps everything in `try/except` and falls back to `sys.__excepthook__`.
- **Heresy rebukes go to stderr, never stdout, and never change the exit code.**
- **Layout:** `src/liturgy/`, tests in `tests/`. Module dependency order is `lexicon` -> `sourcemap` -> `transform` -> `loader`/`curse` -> `cli`. No module may import one later in that order.

---

### Task 1: Scaffolding and lexicon

**Files:**
- Create: `pyproject.toml`
- Create: `src/liturgy/__init__.py`
- Create: `src/liturgy/lexicon.py`
- Test: `tests/test_lexicon.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `liturgy.lexicon.KEYWORDS`, `SOFTWORDS`, `CURSES` (all `dict[str, str]`, Liturgy word -> Python word); `LEXICON` (merged); `INVERSE` (`dict[str, str]`, Python word -> Liturgy word).

- [ ] **Step 1: Create the package skeleton and `pyproject.toml`**

```toml
[project]
name = "liturgy"
version = "0.1.0"
description = "A superset of Python in the ritual language of the Adeptus Mechanicus"
requires-python = ">=3.12"
dependencies = []

[project.scripts]
liturgy = "liturgy.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/liturgy"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Create an empty `src/liturgy/__init__.py`. Then:

```bash
python3 -m venv .venv && .venv/bin/pip install -q -e . pytest
```

- [ ] **Step 2: Write the failing lexicon tests**

```python
# tests/test_lexicon.py
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_lexicon.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'liturgy.lexicon'`

- [ ] **Step 4: Write `src/liturgy/lexicon.py`**

```python
"""Alias tables. Pure data plus lookup; depends on nothing."""

from __future__ import annotations

# Python keywords. Reserved words, so substitution is unambiguous.
KEYWORDS: dict[str, str] = {
    "Heretical": "False",
    "Void": "None",
    "Sanctioned": "True",
    "likewise": "and",
    "styled": "as",
    "attest": "assert",
    "remote": "async",
    "attend": "await",
    "cease": "break",
    "pattern": "class",
    "persist": "continue",
    "rite": "def",
    "purge": "del",
    "lest": "elif",
    "otherwise": "else",
    "curse": "except",
    "regardless": "finally",
    "foreach": "for",
    "within": "from",
    "universal": "global",
    "should": "if",
    "invoke": "import",
    "among": "in",
    "be": "is",
    "servitor": "lambda",
    "adjacent": "nonlocal",
    "nay": "not",
    "elsewise": "or",
    "abide": "pass",
    "proclaim": "raise",
    "render": "return",
    "attempt": "try",
    "whilst": "while",
    "anointed": "with",
    "emanate": "yield",
    # soft keywords
    "discern": "match",
    "wherein": "case",
    "archetype": "type",
}

# Builtins. Deliberately small: each entry widens the reserved-word surface.
SOFTWORDS: dict[str, str] = {
    "intone": "print",
    "measure": "len",
    "span": "range",
    "unseal": "open",
    "hearken": "input",
}

# Exception types. Also inverted at curse-render time.
CURSES: dict[str, str] = {
    "MachineCurse": "Exception",
    "PrimalCurse": "BaseException",
    "ImpureOffering": "ValueError",
    "PatternMismatch": "TypeError",
    "LostPattern": "KeyError",
    "BeyondTheManifest": "IndexError",
    "AbsentAugmetic": "AttributeError",
    "DivisionByTheVoid": "ZeroDivisionError",
    "ForbiddenLore": "ImportError",
    "RelicNotFound": "FileNotFoundError",
    "SpiralOfMadness": "RecursionError",
    "TheRiteIsEnded": "StopIteration",
    "UnknownInvocation": "NameError",
    "MotiveFailure": "RuntimeError",
    "RiteUnwritten": "NotImplementedError",
}

LEXICON: dict[str, str] = {**KEYWORDS, **SOFTWORDS, **CURSES}
INVERSE: dict[str, str] = {py: lit for lit, py in LEXICON.items()}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_lexicon.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/liturgy tests/test_lexicon.py
git commit -m "feat(lexicon): alias tables with bijectivity and coverage invariants"
```

---

### Task 2: SourceMap

**Files:**
- Create: `src/liturgy/sourcemap.py`
- Test: `tests/test_sourcemap.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Span(py_start: int, py_end: int, lit_start: int, lit_end: int)` (frozen dataclass); `SourceMap` with `add(line: int, span: Span) -> None`, `freeze() -> None`, and `to_lit(line: int, col: int) -> int`.

Coordinates are 0-based columns, matching `tokenize`. Lines are 1-based, matching tracebacks.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_sourcemap.py
from liturgy.sourcemap import SourceMap, Span


def build(*spans):
    m = SourceMap()
    for s in spans:
        m.add(1, s)
    m.freeze()
    return m


def test_absent_line_is_identity():
    m = SourceMap()
    m.freeze()
    assert m.to_lit(7, 12) == 12


def test_column_before_any_substitution_is_unchanged():
    # "should x"  ->  "if x": span py[0,2) <- lit[0,6)
    m = build(Span(0, 2, 0, 6))
    assert m.to_lit(1, 0) == 0


def test_column_inside_substitution_points_at_token_start():
    m = build(Span(0, 2, 0, 6))
    assert m.to_lit(1, 1) == 0


def test_column_after_substitution_shifts_by_delta():
    # python col 3 is one past "if ", lit col 7 is one past "should "
    m = build(Span(0, 2, 0, 6))
    assert m.to_lit(1, 3) == 7


def test_deltas_accumulate_across_multiple_substitutions():
    # "should intone"  ->  "if print"
    #   span A: py[0,2) <- lit[0,6)   delta +4
    #   span B: py[3,8) <- lit[7,13)  delta +1  (cumulative +5)
    m = build(Span(0, 2, 0, 6), Span(3, 8, 7, 13))
    assert m.to_lit(1, 8) == 13


def test_spans_may_be_added_out_of_order():
    m = build(Span(3, 8, 7, 13), Span(0, 2, 0, 6))
    assert m.to_lit(1, 8) == 13


def test_mapping_is_monotonic_within_a_line():
    m = build(Span(0, 2, 0, 6), Span(3, 8, 7, 13))
    cols = [m.to_lit(1, c) for c in range(0, 20)]
    assert cols == sorted(cols)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_sourcemap.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'liturgy.sourcemap'`

- [ ] **Step 3: Write `src/liturgy/sourcemap.py`**

Cumulative deltas are precomputed in `freeze()` so `to_lit` stays a binary search rather than a scan.

```python
"""Column mapping between generated Python and original Liturgy source.

Line numbers need no mapping: the token pass preserves lines exactly, so
line N of the Python is line N of the Liturgy. Only columns move.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Span:
    """One substitution, in 0-based column coordinates."""

    py_start: int
    py_end: int
    lit_start: int
    lit_end: int


@dataclass
class SourceMap:
    _spans: dict[int, list[Span]] = field(default_factory=dict)
    _starts: dict[int, list[int]] = field(default_factory=dict)
    _cum: dict[int, list[int]] = field(default_factory=dict)

    def add(self, line: int, span: Span) -> None:
        self._spans.setdefault(line, []).append(span)

    def freeze(self) -> None:
        """Sort spans and precompute cumulative width deltas."""
        for line, spans in self._spans.items():
            spans.sort(key=lambda s: s.py_start)
            self._starts[line] = [s.py_start for s in spans]
            total = 0
            cum: list[int] = []
            for s in spans:
                total += (s.lit_end - s.lit_start) - (s.py_end - s.py_start)
                cum.append(total)
            self._cum[line] = cum

    def to_lit(self, line: int, col: int) -> int:
        """Map a column in generated Python back to the .lit column."""
        spans = self._spans.get(line)
        if not spans:
            return col
        i = bisect_right(self._starts[line], col) - 1
        if i < 0:
            return col
        if col < spans[i].py_end:
            return spans[i].lit_start
        return col + self._cum[line][i]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_sourcemap.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/liturgy/sourcemap.py tests/test_sourcemap.py
git commit -m "feat(sourcemap): column mapping with precomputed cumulative deltas"
```

---

### Task 3: Token pass and splicing

**Files:**
- Create: `src/liturgy/transform.py`
- Test: `tests/test_transform.py`

**Interfaces:**
- Consumes: `liturgy.lexicon.LEXICON`; `liturgy.sourcemap.SourceMap`, `Span`.
- Produces: `Substitution(row: int, col_start: int, col_end: int, text: str)` (NamedTuple, `row` 1-based, columns 0-based); `TokenPass` protocol, `list[TokenInfo] -> list[Substitution]`; `alias_pass`; `DEFAULT_PASSES: tuple[TokenPass, ...]`; `transform(src: str, passes: Sequence[TokenPass] = DEFAULT_PASSES) -> tuple[str, SourceMap]`.

This task implements naive substitution. Task 4 adds the context rules; do not write them yet.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_transform.py
import ast

import pytest

from liturgy.transform import transform


def py(src):
    return transform(src)[0]


def test_substitutes_a_keyword():
    assert py("rite f():\n    abide\n") == "def f():\n    pass\n"


def test_leaves_plain_python_untouched():
    src = "def f(x):\n    return x + 1\n"
    assert py(src) == src


def test_never_touches_string_contents():
    assert py('x = "rite abide"\n') == 'x = "rite abide"\n'


def test_never_touches_comments():
    assert py("x = 1  ## rite abide\n") == "x = 1  ## rite abide\n"


def test_substitutes_inside_fstring_replacement_fields():
    # 3.12+ tokenizes f-string internals as real NAME tokens, so this IS code.
    assert py('rite f():\n    render f"{measure(x)}"\n') == (
        'def f():\n    return f"{len(x)}"\n'
    )


def test_does_not_touch_fstring_literal_text():
    assert py('x = f"rite {y}"\n') == 'x = f"rite {y}"\n'


def test_preserves_line_count():
    src = "rite f():\n    should x:\n        render 1\n    render 2\n"
    assert py(src).count("\n") == src.count("\n")


def test_output_parses():
    src = "rite f(n):\n    should n < 2:\n        render n\n    render f(n - 1)\n"
    ast.parse(py(src))


def test_multiline_string_bodies_are_untouched():
    src = 'x = """\nrite abide\n"""\n'
    assert py(src) == src


@pytest.mark.parametrize(
    "src",
    [
        "x = 1\n",
        "class A:\n    def m(self):\n        return [i for i in range(3)]\n",
        "with open('f') as fh:\n    data = fh.read()\n",
        "async def go():\n    await thing()\n",
    ],
)
def test_identity_on_python_without_liturgy_words(src):
    assert py(src) == src


def test_columns_map_back_to_original():
    src = "should x:\n    abide\n"
    out, smap = transform(src)
    assert out == "if x:\n    pass\n"
    # "x" sits at python col 3, liturgy col 7
    assert smap.to_lit(1, 3) == 7
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_transform.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'liturgy.transform'`

- [ ] **Step 3: Write `src/liturgy/transform.py`**

Note `_splice`: positions are computed forward (so cumulative deltas are right) but the string edit runs backward (so earlier column offsets stay valid).

```python
"""Liturgy source -> Python source, preserving line numbers exactly."""

from __future__ import annotations

import io
import token as tokmod
import tokenize
from collections.abc import Sequence
from typing import NamedTuple, Protocol

from .lexicon import LEXICON
from .sourcemap import SourceMap, Span


class Substitution(NamedTuple):
    row: int  # 1-based
    col_start: int  # 0-based, inclusive
    col_end: int  # 0-based, exclusive
    text: str


class TokenPass(Protocol):
    def __call__(
        self, toks: list[tokenize.TokenInfo]
    ) -> list[Substitution]: ...


def alias_pass(toks: list[tokenize.TokenInfo]) -> list[Substitution]:
    subs: list[Substitution] = []
    for tok in toks:
        if tok.type != tokmod.NAME:
            continue
        py = LEXICON.get(tok.string)
        if py is None:
            continue
        subs.append(Substitution(tok.start[0], tok.start[1], tok.end[1], py))
    return subs


DEFAULT_PASSES: tuple[TokenPass, ...] = (alias_pass,)


def transform(
    src: str, passes: Sequence[TokenPass] = DEFAULT_PASSES
) -> tuple[str, SourceMap]:
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    subs = [s for p in passes for s in p(toks)]
    return _splice(src, subs)


def _splice(src: str, subs: list[Substitution]) -> tuple[str, SourceMap]:
    lines = src.splitlines(keepends=True)
    smap = SourceMap()

    by_line: dict[int, list[Substitution]] = {}
    for s in subs:
        by_line.setdefault(s.row, []).append(s)

    for row, row_subs in by_line.items():
        row_subs.sort(key=lambda s: s.col_start)

        # Forward pass: where does each replacement land in the output?
        delta = 0
        for s in row_subs:
            py_start = s.col_start + delta
            py_end = py_start + len(s.text)
            smap.add(row, Span(py_start, py_end, s.col_start, s.col_end))
            delta += len(s.text) - (s.col_end - s.col_start)

        # Backward pass: edit the line without invalidating earlier offsets.
        line = lines[row - 1]
        for s in reversed(row_subs):
            line = line[: s.col_start] + s.text + line[s.col_end :]
        lines[row - 1] = line

    smap.freeze()
    return "".join(lines), smap
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_transform.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add src/liturgy/transform.py tests/test_transform.py
git commit -m "feat(transform): tokenize, alias, and splice with line preservation"
```

---

### Task 4: Context rules

**Files:**
- Modify: `src/liturgy/transform.py` (replace `alias_pass`)
- Test: `tests/test_context_rules.py`

**Interfaces:**
- Consumes: everything from Task 3.
- Produces: no signature change. `alias_pass` keeps its `list[TokenInfo] -> list[Substitution]` shape.

These three rules are correctness requirements, not polish. Without them Liturgy is unusable against real libraries.

- [ ] **Step 1: Write the failing regression tests**

```python
# tests/test_context_rules.py
from liturgy.transform import transform


def py(src):
    return transform(src)[0]


# Rule 1: after a dot
def test_attribute_access_is_not_substituted():
    # template.render() must not become template.return()
    assert py("template.render()\n") == "template.render()\n"


def test_attribute_named_pattern_survives():
    assert py("m = regex.pattern\n") == "m = regex.pattern\n"


def test_method_call_on_result_survives():
    assert py("get().span(1)\n") == "get().span(1)\n"


def test_bare_name_still_substituted_alongside_attribute():
    assert py("render obj.render\n") == "return obj.render\n"


# Rule 2: keyword-argument position
def test_keyword_argument_name_is_not_substituted():
    # f(intone=True) must not become f(print=True)
    assert py("f(intone=True)\n") == "f(intone=True)\n"


def test_keyword_argument_value_is_still_substituted():
    assert py("f(mode=Sanctioned)\n") == "f(mode=True)\n"


def test_equality_comparison_is_still_substituted():
    # "==" is a single token, so it must not be mistaken for a kwarg "="
    assert py("f(measure == 1)\n") == "f(len == 1)\n"


def test_walrus_is_still_substituted():
    assert py("f(measure := 1)\n") == "f(len := 1)\n"


def test_assignment_at_module_level_is_still_substituted():
    # depth 0, so this is a real assignment, not a kwarg
    assert py("measure = 1\n") == "len = 1\n"


# Rule 3: import statements
def test_import_target_is_not_substituted():
    assert py("within jinja2 invoke render\n") == "from jinja2 import render\n"


def test_plain_import_target_is_not_substituted():
    assert py("invoke span\n") == "import span\n"


def test_as_clause_still_works_in_imports():
    assert py("invoke jinja2 styled j2\n") == "import jinja2 as j2\n"


def test_import_scope_ends_at_newline():
    assert py("invoke os\nrender measure\n") == "import os\nreturn len\n"


def test_parenthesised_import_list_is_protected():
    src = "within x invoke (render,\n    measure)\n"
    assert py(src) == "from x import (render,\n    measure)\n"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_context_rules.py -v`
Expected: FAIL. Several tests, e.g. `template.render()` producing `template.return()`

- [ ] **Step 3: Replace `alias_pass` in `src/liturgy/transform.py`**

```python
# Tokens that carry no syntactic weight when looking backwards.
_INSIGNIFICANT = frozenset(
    {
        tokmod.COMMENT,
        tokmod.NL,
        tokmod.INDENT,
        tokmod.DEDENT,
    }
)

# Inside an import statement, only these targets may still be substituted.
_IMPORT_SAFE = frozenset({"import", "from", "as"})

_OPENERS = frozenset("([{")
_CLOSERS = frozenset(")]}")


def alias_pass(toks: list[tokenize.TokenInfo]) -> list[Substitution]:
    subs: list[Substitution] = []
    significant = [t for t in toks if t.type not in _INSIGNIFICANT]

    depth = 0
    in_import = False

    for i, tok in enumerate(significant):
        if tok.type == tokmod.NEWLINE:
            in_import = False
            continue

        if tok.type == tokmod.OP:
            if tok.string in _OPENERS:
                depth += 1
            elif tok.string in _CLOSERS:
                depth -= 1
            continue

        if tok.type != tokmod.NAME:
            continue

        py = LEXICON.get(tok.string)

        # Track import statements in either spelling. Do this before the
        # substitution decision so the keyword itself is still translated.
        if tok.string in ("import", "from") or py in ("import", "from"):
            in_import = True

        if py is None:
            continue

        prev = significant[i - 1] if i else None
        nxt = significant[i + 1] if i + 1 < len(significant) else None

        # Rule 1: attribute access. obj.render must not become obj.return.
        if prev is not None and prev.type == tokmod.OP and prev.string == ".":
            continue

        # Rule 2: keyword-argument name inside a call.
        if (
            depth > 0
            and nxt is not None
            and nxt.type == tokmod.OP
            and nxt.string == "="
        ):
            continue

        # Rule 3: import statements. Only the statement keywords translate.
        if in_import and py not in _IMPORT_SAFE:
            continue

        subs.append(Substitution(tok.start[0], tok.start[1], tok.end[1], py))

    return subs
```

- [ ] **Step 4: Run the whole suite**

Run: `.venv/bin/pytest -v`
Expected: all passed, including Task 3's tests (no regressions)

- [ ] **Step 5: Commit**

```bash
git add src/liturgy/transform.py tests/test_context_rules.py
git commit -m "feat(transform): context rules for attributes, kwargs, and imports"
```

---

### Task 5: Round-trip property test

**Files:**
- Create: `src/liturgy/_reverse.py`
- Test: `tests/test_roundtrip.py`

**Interfaces:**
- Consumes: `liturgy.lexicon.INVERSE`; `liturgy.transform.transform`.
- Produces: `liturgy._reverse.to_liturgy(src: str) -> str`, a test-support inverse used only to generate Liturgy fixtures. It is private and is **not** the Spec III `transcribe` verb.

This task exercises bijectivity and the whole lexicon at once, and catches lexicon entries no hand-written test covers.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_roundtrip.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_roundtrip.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'liturgy._reverse'`

- [ ] **Step 3: Write `src/liturgy/_reverse.py`**

The reverse direction needs the same context rules, so it reuses the forward pass machinery by swapping the lookup table.

```python
"""Python -> Liturgy, for test fixtures only.

Not the Spec III `transcribe` verb: this exists so the round-trip property
test can generate Liturgy from real Python and assert we get the Python back.
"""

from __future__ import annotations

import token as tokmod
import tokenize

from . import transform as _t
from .lexicon import INVERSE


def _reverse_pass(toks: list[tokenize.TokenInfo]) -> list[_t.Substitution]:
    subs: list[_t.Substitution] = []
    significant = [t for t in toks if t.type not in _t._INSIGNIFICANT]

    depth = 0
    in_import = False

    for i, tok in enumerate(significant):
        if tok.type == tokmod.NEWLINE:
            in_import = False
            continue
        if tok.type == tokmod.OP:
            if tok.string in _t._OPENERS:
                depth += 1
            elif tok.string in _t._CLOSERS:
                depth -= 1
            continue
        if tok.type != tokmod.NAME:
            continue

        lit = INVERSE.get(tok.string)
        if tok.string in ("import", "from"):
            in_import = True
        if lit is None:
            continue

        prev = significant[i - 1] if i else None
        nxt = significant[i + 1] if i + 1 < len(significant) else None

        if prev is not None and prev.type == tokmod.OP and prev.string == ".":
            continue
        if (
            depth > 0
            and nxt is not None
            and nxt.type == tokmod.OP
            and nxt.string == "="
        ):
            continue
        if in_import and tok.string not in _t._IMPORT_SAFE:
            continue

        subs.append(
            _t.Substitution(tok.start[0], tok.start[1], tok.end[1], lit)
        )
    return subs


def to_liturgy(src: str) -> str:
    return _t.transform(src, passes=(_reverse_pass,))[0]
```

- [ ] **Step 4: Run the whole suite**

Run: `.venv/bin/pytest -v`
Expected: all passed. If a sample fails, the lexicon or a context rule is at fault; fix the source, not the sample.

- [ ] **Step 5: Commit**

```bash
git add src/liturgy/_reverse.py tests/test_roundtrip.py
git commit -m "test: round-trip property over real Python samples"
```

---

### Task 6: Import hook

**Files:**
- Create: `src/liturgy/loader.py`
- Test: `tests/test_loader.py`

**Interfaces:**
- Consumes: `liturgy.transform.transform`.
- Produces: `liturgy.loader.SUFFIX = ".lit"`; `LiturgyLoader(SourceFileLoader)`; `install() -> None` (idempotent); `chant(path: str, argv: list[str]) -> int`.

**The trap in this task:** `FileFinder.path_hook((LiturgyLoader, ['.lit']))` inserted at `sys.path_hooks[0]` produces a finder that matches *every* directory but knows only `.lit`, which shadows the default finder and breaks all normal `.py` imports. The hook must be built with the full default loader details alongside ours.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_loader.py
import subprocess
import sys
import textwrap

import pytest

from liturgy import loader

PRAYER = textwrap.dedent(
    """\
    GREETING = "Ave Omnissiah"


    rite greet(name):
        render f"{GREETING}, {name}"
    """
)


@pytest.fixture
def prayer_dir(tmp_path, monkeypatch):
    (tmp_path / "prayer.lit").write_text(PRAYER)
    monkeypatch.syspath_prepend(str(tmp_path))
    loader.install()
    yield tmp_path


def test_imports_a_lit_module(prayer_dir):
    import prayer

    assert prayer.greet("Magos") == "Ave Omnissiah, Magos"


def test_get_source_returns_original_liturgy(prayer_dir):
    import prayer

    assert "rite greet" in prayer.__loader__.get_source("prayer")


def test_install_is_idempotent():
    before = len(sys.path_hooks)
    loader.install()
    loader.install()
    assert len(sys.path_hooks) == before


def test_normal_python_imports_still_work(tmp_path, monkeypatch):
    # Regression: a path hook registered without the default loader details
    # shadows the stdlib FileFinder and breaks every .py import.
    (tmp_path / "plain_mod.py").write_text("VALUE = 42\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    loader.install()
    import plain_mod

    assert plain_mod.VALUE == 42


def test_chant_runs_as_main(tmp_path):
    script = tmp_path / "main.lit"
    script.write_text('intone("chanted")\nintone(__name__)\n')
    out = subprocess.run(
        [sys.executable, "-c",
         f"from liturgy.loader import chant; chant({str(script)!r}, [])"],
        capture_output=True, text=True, check=True,
    )
    assert out.stdout.splitlines() == ["chanted", "__main__"]


def test_chant_passes_argv(tmp_path):
    script = tmp_path / "args.lit"
    script.write_text("invoke sys\nintone(sys.argv[1])\n")
    out = subprocess.run(
        [sys.executable, "-c",
         f"from liturgy.loader import chant; chant({str(script)!r}, ['omnissiah'])"],
        capture_output=True, text=True, check=True,
    )
    assert out.stdout.strip() == "omnissiah"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_loader.py -v`
Expected: FAIL with `ImportError: cannot import name 'loader'`

- [ ] **Step 3: Write `src/liturgy/loader.py`**

```python
"""Import hook and __main__ execution for .lit files."""

from __future__ import annotations

import importlib
import importlib.machinery
import importlib.util
import linecache
import os
import sys
import types

from importlib.machinery import (
    BYTECODE_SUFFIXES,
    EXTENSION_SUFFIXES,
    SOURCE_SUFFIXES,
    ExtensionFileLoader,
    FileFinder,
    SourceFileLoader,
    SourcelessFileLoader,
)

from .transform import transform

SUFFIX = ".lit"


class LiturgyLoader(SourceFileLoader):
    """Compiles Liturgy on import.

    `get_source` is deliberately NOT overridden: the inherited one returns
    the original .lit text, which is what makes linecache and tracebacks
    display Liturgy rather than generated Python.
    """

    def source_to_code(self, data, path, *, _optimize=-1):  # noqa: D102
        src = importlib.util.decode_source(data)
        py, _smap = transform(src)
        return compile(
            py, path, "exec", dont_inherit=True, optimize=_optimize
        )


_installed = False


def install() -> None:
    """Register the .lit path hook. Idempotent."""
    global _installed
    if _installed:
        return

    # The default loader details MUST be included. A hook carrying only our
    # details still matches every directory, shadowing the stdlib FileFinder
    # and breaking all .py imports.
    hook = FileFinder.path_hook(
        (LiturgyLoader, [SUFFIX]),
        (ExtensionFileLoader, EXTENSION_SUFFIXES),
        (SourceFileLoader, SOURCE_SUFFIXES),
        (SourcelessFileLoader, BYTECODE_SUFFIXES),
    )
    sys.path_hooks.insert(0, hook)
    sys.path_importer_cache.clear()
    importlib.invalidate_caches()
    _installed = True


def chant(path: str, argv: list[str]) -> int:
    """Execute a .lit file with __main__ semantics."""
    install()
    path = os.path.abspath(path)
    with open(path, encoding="utf-8") as fh:
        src = fh.read()

    py, _smap = transform(src)

    # No loader is involved here, so seed linecache by hand or the traceback
    # will have no source lines to show.
    linecache.cache[path] = (
        len(src),
        None,
        src.splitlines(keepends=True),
        path,
    )

    module = types.ModuleType("__main__")
    module.__file__ = path
    module.__loader__ = None
    module.__package__ = None
    sys.modules["__main__"] = module

    old_argv = sys.argv
    sys.argv = [path, *argv]
    try:
        exec(compile(py, path, "exec", dont_inherit=True), module.__dict__)
    finally:
        sys.argv = old_argv
    return 0
```

- [ ] **Step 4: Run the whole suite**

Run: `.venv/bin/pytest -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add src/liturgy/loader.py tests/test_loader.py
git commit -m "feat(loader): .lit path hook and chant execution"
```

---

### Task 7: Curse rendering

**Files:**
- Create: `src/liturgy/curse.py`
- Test: `tests/test_curse.py`

**Interfaces:**
- Consumes: `liturgy.lexicon.INVERSE`; `liturgy.transform.transform`; `liturgy.sourcemap.SourceMap`.
- Produces: `liturgy.curse.render_curse(exc_type, exc, tb, *, file=None) -> None`; `install() -> None`; `uninstall() -> None`; `curse_name(exc_type: type) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_curse.py
import io
import textwrap

import pytest

from liturgy import curse, loader

BROKEN = textwrap.dedent(
    """\
    rite invoke_spirit(tome):
        render tome / 0
    """
)


@pytest.fixture
def broken(tmp_path, monkeypatch):
    (tmp_path / "broken.lit").write_text(BROKEN)
    monkeypatch.syspath_prepend(str(tmp_path))
    loader.install()
    import broken as mod

    return mod


def capture(exc_info):
    buf = io.StringIO()
    curse.render_curse(*exc_info, file=buf)
    return buf.getvalue()


def test_exception_name_is_themed():
    assert curse.curse_name(ZeroDivisionError) == "DivisionByTheVoid"
    assert curse.curse_name(KeyError) == "LostPattern"


def test_unmapped_exception_keeps_its_name():
    class Bespoke(Exception):
        pass

    assert curse.curse_name(Bespoke) == "Bespoke"


def test_rendered_curse_has_the_frame_and_theme(broken):
    try:
        broken.invoke_spirit(1)
    except ZeroDivisionError:
        import sys

        out = capture(sys.exc_info())
    assert "++ MACHINE CURSE ++" in out
    assert "broken.lit" in out
    assert "line 2" in out
    assert "DivisionByTheVoid" in out


def test_rendered_curse_shows_liturgy_source_not_generated_python(broken):
    try:
        broken.invoke_spirit(1)
    except ZeroDivisionError:
        import sys

        out = capture(sys.exc_info())
    assert "render tome / 0" in out
    assert "return tome / 0" not in out


def test_library_frames_are_not_themed(broken):
    # A frame from a .py file must render with its real path and no ++ banner
    # on that line.
    try:
        broken.invoke_spirit(1)
    except ZeroDivisionError:
        import sys

        out = capture(sys.exc_info())
    assert out.count("++ MACHINE CURSE ++") == 1


def test_hook_never_raises_even_with_a_broken_map(broken, monkeypatch):
    monkeypatch.setattr(
        curse, "_map_for", lambda path: (_ for _ in ()).throw(RuntimeError())
    )
    try:
        broken.invoke_spirit(1)
    except ZeroDivisionError:
        import sys

        exc_info = sys.exc_info()
    buf = io.StringIO()
    # Must not propagate; falls back to the stdlib hook (which writes to
    # sys.stderr, so buf may stay empty). The assertion is that it returns.
    curse.render_curse(*exc_info, file=buf)


def test_deleted_source_file_degrades_gracefully(tmp_path, monkeypatch):
    # Import succeeds, then the .lit file vanishes before the curse renders.
    # The map is unavailable, so we must fall back to an uncaretted frame
    # rather than raise or print wrong columns.
    import sys

    path = tmp_path / "vanishing.lit"
    path.write_text("rite boom():\n    proclaim MachineCurse('gone')\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    loader.install()
    import vanishing

    path.unlink()
    linecache.clearcache()
    curse._map_cache.clear()

    try:
        vanishing.boom()
    except Exception:
        out = capture(sys.exc_info())

    assert "++ MACHINE CURSE ++" in out
    assert "MachineCurse: gone" in out
```

`tests/test_curse.py` needs `import linecache` at the top for the test above.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_curse.py -v`
Expected: FAIL with `ImportError: cannot import name 'curse'`

- [ ] **Step 3: Write `src/liturgy/curse.py`**

```python
"""Themed traceback rendering for .lit frames."""

from __future__ import annotations

import linecache
import sys
import threading
import traceback
import types

from .lexicon import INVERSE
from .sourcemap import SourceMap
from .transform import transform

BANNER_OPEN = "++ MACHINE CURSE ++"
BANNER_CLOSE = "++ the machine spirit is displeased ++"

_map_cache: dict[str, SourceMap | None] = {}


def curse_name(exc_type: type) -> str:
    return INVERSE.get(exc_type.__name__, exc_type.__name__)


def _map_for(path: str) -> SourceMap | None:
    """Lazily build the column map. Only needed when rendering a curse."""
    if path not in _map_cache:
        try:
            src = "".join(linecache.getlines(path))
            if not src:
                with open(path, encoding="utf-8") as fh:
                    src = fh.read()
            _map_cache[path] = transform(src)[1]
        except Exception:
            _map_cache[path] = None
    return _map_cache[path]


def _render_lit_frame(frame: traceback.FrameSummary, out: list[str]) -> None:
    out.append(
        f"   the rite was broken at {frame.filename}, "
        f"line {frame.lineno}, in rite {frame.name}"
    )
    line = linecache.getline(frame.filename, frame.lineno).rstrip("\n")
    if not line:
        return
    out.append(f"       {line.strip()}")

    smap = _map_for(frame.filename)
    if smap is None or frame.colno is None or frame.end_colno is None:
        return
    lead = len(line) - len(line.lstrip())
    start = smap.to_lit(frame.lineno, frame.colno) - lead
    end = smap.to_lit(frame.lineno, frame.end_colno) - lead
    if 0 <= start < end <= len(line.strip()):
        out.append("       " + " " * start + "^" * (end - start))


def _render(
    exc_type: type,
    exc: BaseException,
    tb: types.TracebackType | None,
    file,
) -> None:
    frames = traceback.extract_tb(tb)
    out = [BANNER_OPEN]
    for frame in frames:
        if frame.filename.endswith(".lit"):
            _render_lit_frame(frame, out)
        else:
            out.append(
                f'   File "{frame.filename}", line {frame.lineno}, '
                f"in {frame.name}"
            )
            if frame.line:
                out.append(f"       {frame.line}")
    out.append(f"   {curse_name(exc_type)}: {exc}")
    out.append(BANNER_CLOSE)
    print("\n".join(out), file=file)


def render_curse(exc_type, exc, tb, *, file=None) -> None:
    """Never raises. A failing excepthook would destroy the original error."""
    try:
        _render(exc_type, exc, tb, file or sys.stderr)
    except Exception:
        sys.__excepthook__(exc_type, exc, tb)


def _thread_hook(args) -> None:
    render_curse(args.exc_type, args.exc_value, args.exc_traceback)


def install() -> None:
    sys.excepthook = render_curse
    threading.excepthook = _thread_hook


def uninstall() -> None:
    sys.excepthook = sys.__excepthook__
    threading.excepthook = threading.__excepthook__
```

- [ ] **Step 4: Run the whole suite**

Run: `.venv/bin/pytest -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add src/liturgy/curse.py tests/test_curse.py
git commit -m "feat(curse): themed tracebacks with column remapping and safe fallback"
```

---

### Task 8: Heresy rebukes

**Files:**
- Create: `src/liturgy/heresy.py`
- Test: `tests/test_heresy.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `liturgy.heresy.rebuke(alias: str, proper: str, *, stream=None) -> None`; `state_path() -> pathlib.Path`; `REBUKES: list[str]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_heresy.py
import io

import pytest

from liturgy import heresy


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.delenv("LITURGY_PIOUS", raising=False)


def emit():
    buf = io.StringIO()
    heresy.rebuke("run", "chant", stream=buf)
    return buf.getvalue()


def test_first_offence_is_noted():
    out = emit()
    assert "TECH-HERESY DETECTED" in out
    assert "CHANT" in out
    assert "noted" in out


def test_second_offence_escalates():
    emit()
    assert "permanent record" in emit()


def test_third_offence_summons_the_inquisition():
    emit()
    emit()
    assert "Inquisition" in emit()


def test_escalation_saturates_at_the_last_rebuke():
    for _ in range(5):
        out = emit()
    assert "Inquisition" in out


def test_pious_zero_silences_everything(monkeypatch):
    monkeypatch.setenv("LITURGY_PIOUS", "0")
    assert emit() == ""


def test_unwritable_state_file_does_not_raise(monkeypatch):
    monkeypatch.setattr(
        heresy, "state_path", lambda: (_ for _ in ()).throw(OSError())
    )
    assert "TECH-HERESY DETECTED" in emit()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_heresy.py -v`
Expected: FAIL with `ImportError: cannot import name 'heresy'`

- [ ] **Step 3: Write `src/liturgy/heresy.py`**

```python
"""Rebukes for invoking a rite by its mundane name."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REBUKES = [
    "this rite is named {proper}. the omission is noted.",
    "this rite is named {proper}. the transgression is recorded in your "
    "permanent record.",
    "this rite is named {proper}. the Inquisition has been notified.",
]


def state_path() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")
    return Path(base) / "liturgy" / "heresies.json"


def _bump(alias: str) -> int:
    """Increment and persist the offence count. Never raises."""
    try:
        path = state_path()
        data = json.loads(path.read_text()) if path.exists() else {}
    except Exception:
        return 1
    count = int(data.get(alias, 0)) + 1
    data[alias] = count
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
    except Exception:
        pass  # the joke must never break the CLI
    return count


def rebuke(alias: str, proper: str, *, stream=None) -> None:
    if os.environ.get("LITURGY_PIOUS") == "0":
        return
    stream = stream if stream is not None else sys.stderr
    count = _bump(alias)
    message = REBUKES[min(count, len(REBUKES)) - 1].format(proper=proper.upper())
    print("++ TECH-HERESY DETECTED ++", file=stream)
    print(f"++ {message} ++", file=stream)
```

- [ ] **Step 4: Run the whole suite**

Run: `.venv/bin/pytest -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add src/liturgy/heresy.py tests/test_heresy.py
git commit -m "feat(heresy): escalating rebukes for mundane verb aliases"
```

---

### Task 9: CLI, `chant`

**Files:**
- Create: `src/liturgy/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `liturgy.loader.chant`, `liturgy.curse.install`, `liturgy.heresy.rebuke`.
- Produces: `liturgy.cli.main(argv: list[str] | None = None) -> int`; `HERETICAL: dict[str, str]`; `RESERVED_VERBS: frozenset[str]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli.py
import subprocess
import sys

import pytest

from liturgy import cli


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.delenv("LITURGY_PIOUS", raising=False)


@pytest.fixture
def prayer(tmp_path):
    p = tmp_path / "hello.lit"
    p.write_text('intone("Ave Omnissiah")\n')
    return p


def run_cli(args, **env):
    return subprocess.run(
        [sys.executable, "-m", "liturgy", *args],
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), **env},
    )


def test_chant_runs_a_prayer(prayer):
    out = run_cli(["chant", str(prayer)])
    assert out.returncode == 0
    assert out.stdout.strip() == "Ave Omnissiah"
    assert out.stderr == ""


def test_heretical_alias_still_works(prayer):
    out = run_cli(["run", str(prayer)])
    assert out.returncode == 0
    assert out.stdout.strip() == "Ave Omnissiah"


def test_heretical_alias_rebukes_on_stderr_only(prayer):
    out = run_cli(["run", str(prayer)])
    assert "TECH-HERESY DETECTED" in out.stderr
    assert "TECH-HERESY" not in out.stdout


def test_heresy_does_not_change_the_exit_code(prayer):
    assert run_cli(["run", str(prayer)]).returncode == 0


def test_absolved_silences_the_rebuke(prayer):
    out = run_cli(["--absolved", "run", str(prayer)])
    assert "TECH-HERESY" not in out.stderr


def test_pious_zero_silences_the_rebuke(prayer):
    out = run_cli(["run", str(prayer)], LITURGY_PIOUS="0")
    assert "TECH-HERESY" not in out.stderr


def test_failing_prayer_renders_a_machine_curse(tmp_path):
    bad = tmp_path / "bad.lit"
    bad.write_text("intone(1 / 0)\n")
    out = run_cli(["chant", str(bad)])
    assert out.returncode != 0
    assert "MACHINE CURSE" in out.stderr
    assert "DivisionByTheVoid" in out.stderr


def test_profane_gives_a_plain_traceback(tmp_path):
    bad = tmp_path / "bad.lit"
    bad.write_text("intone(1 / 0)\n")
    out = run_cli(["--profane", "chant", str(bad)])
    assert "MACHINE CURSE" not in out.stderr
    assert "ZeroDivisionError" in out.stderr


def test_profane_env_var_also_gives_a_plain_traceback(tmp_path):
    bad = tmp_path / "bad.lit"
    bad.write_text("intone(1 / 0)\n")
    out = run_cli(["chant", str(bad)], LITURGY_PROFANE="1")
    assert "MACHINE CURSE" not in out.stderr
    assert "ZeroDivisionError" in out.stderr


def test_reserved_verbs_are_declared():
    # Spec III owns these; Core must not hand the names to anything else.
    assert {"augur", "prove", "sanctify", "transcribe"} <= cli.RESERVED_VERBS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_cli.py -v`
Expected: FAIL with `ImportError: cannot import name 'cli'`

- [ ] **Step 3: Write `src/liturgy/cli.py` and `src/liturgy/__main__.py`**

Heretical aliases are resolved by rewriting `argv` before parsing, so argparse never needs to know which spelling was used.

```python
"""Command line interface."""

from __future__ import annotations

import argparse
import os
import sys

from . import curse, heresy
from .loader import chant as _chant

HERETICAL: dict[str, str] = {"run": "chant", "repl": "commune"}

# Owned by Spec III. Declared here so Core never reuses the names.
RESERVED_VERBS = frozenset(
    {
        "augur",
        "prove",
        "sanctify",
        "forge",
        "consecrate",
        "purge",
        "anoint",
        "transcribe",
    }
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liturgy")
    parser.add_argument(
        "--absolved",
        action="store_true",
        help="suppress rebukes for mundane verb names",
    )
    parser.add_argument(
        "--profane",
        action="store_true",
        help="render plain Python tracebacks instead of machine curses",
    )
    verbs = parser.add_subparsers(dest="verb", required=True)

    p_chant = verbs.add_parser("chant", help="execute a litany")
    p_chant.add_argument("file")
    p_chant.add_argument("args", nargs=argparse.REMAINDER)

    verbs.add_parser("commune", help="open an interactive session")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Resolve heretical aliases before parsing, remembering the transgression.
    transgression: tuple[str, str] | None = None
    for i, arg in enumerate(argv):
        if arg.startswith("-"):
            continue
        if arg in HERETICAL:
            transgression = (arg, HERETICAL[arg])
            argv[i] = HERETICAL[arg]
        break

    args = _build_parser().parse_args(argv)

    if transgression and not args.absolved:
        heresy.rebuke(*transgression)

    profane = args.profane or os.environ.get("LITURGY_PROFANE") == "1"
    if not profane:
        curse.install()

    if args.verb == "chant":
        return _chant(args.file, args.args)
    if args.verb == "commune":
        from .commune import commune

        return commune()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

```python
# src/liturgy/__main__.py
from .cli import main

raise SystemExit(main())
```

Task 9's tests exercise `chant` only. `test_reserved_verbs_are_declared` passes now; the `commune` import is exercised in Task 10.

- [ ] **Step 4: Run the whole suite**

Run: `.venv/bin/pytest -v`
Expected: all passed except any test that reaches `commune` (Task 10). If `test_cli.py` has no such test, all passed.

- [ ] **Step 5: Commit**

```bash
git add src/liturgy/cli.py src/liturgy/__main__.py tests/test_cli.py
git commit -m "feat(cli): chant verb, heretical aliases, profane escape hatch"
```

---

### Task 10: CLI, `commune`

**Files:**
- Create: `src/liturgy/commune.py`
- Test: `tests/test_commune.py`

**Interfaces:**
- Consumes: `liturgy.transform.transform`.
- Produces: `liturgy.commune.LiturgyConsole(code.InteractiveConsole)`; `commune(banner: str | None = None) -> int`.

The wrinkle: `tokenize` raises `TokenError` on unterminated brackets and strings. The REPL must read that as "keep reading", not as an error, or multi-line rites become impossible to type.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_commune.py
import subprocess
import sys

from liturgy.commune import LiturgyConsole


def feed(lines):
    """Push lines through runsource; return (needs_more_flags, console)."""
    console = LiturgyConsole()
    flags = []
    buffer = []
    for line in lines:
        buffer.append(line)
        flags.append(console.runsource("\n".join(buffer)))
        if not flags[-1]:
            buffer = []
    return flags, console


def test_single_statement_executes():
    flags, console = feed(["x = 1 + 1"])
    assert flags == [False]
    assert console.locals["x"] == 2


def test_liturgy_keywords_work():
    flags, console = feed(["x = Sanctioned"])
    assert flags == [False]
    assert console.locals["x"] is True


def test_incomplete_block_requests_more_input():
    flags, _ = feed(["rite f():"])
    assert flags == [True]


def test_multiline_rite_completes():
    flags, console = feed(["rite f():", "    render 7", ""])
    assert flags[-1] is False
    assert console.locals["f"]() == 7


def test_unterminated_bracket_requests_more_input():
    # tokenize raises TokenError here; it must read as "keep reading"
    flags, _ = feed(["x = ["])
    assert flags == [True]


def test_unterminated_string_requests_more_input():
    flags, _ = feed(['x = """abc'])
    assert flags == [True]


def test_syntax_error_is_reported_not_buffered(capsys):
    # A complete, unambiguous syntax error: not incomplete input.
    flags, _ = feed(["x = = 1"])
    assert flags == [False]
    assert "SyntaxError" in capsys.readouterr().err


def test_commune_starts_and_exits_cleanly():
    out = subprocess.run(
        [sys.executable, "-m", "liturgy", "commune"],
        input="intone(measure('omnissiah'))\n",
        capture_output=True,
        text=True,
    )
    assert "9" in out.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_commune.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'liturgy.commune'`

- [ ] **Step 3: Write `src/liturgy/commune.py`**

```python
"""Interactive Liturgy session."""

from __future__ import annotations

import code
import sys
import tokenize

from .transform import transform

BANNER = (
    "++ COMMUNION ESTABLISHED ++\n"
    f"++ cogitator {sys.version.split()[0]} attends your litanies ++"
)
FAREWELL = "++ communion ended. the Omnissiah is served. ++"


class LiturgyConsole(code.InteractiveConsole):
    def runsource(self, source, filename="<commune>", symbol="single"):
        try:
            py, _smap = transform(source)
        except tokenize.TokenError:
            # Unterminated bracket or string: not an error, just unfinished.
            return True
        except IndentationError:
            return True
        except SyntaxError:
            self.showsyntaxerror(filename)
            return False

        try:
            compiled = self.compile(py, filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            self.showsyntaxerror(filename)
            return False

        if compiled is None:
            return True  # incomplete

        self.runcode(compiled)
        return False


def commune(banner: str | None = None) -> int:
    console = LiturgyConsole()
    console.interact(
        banner=BANNER if banner is None else banner, exitmsg=FAREWELL
    )
    return 0
```

- [ ] **Step 4: Run the whole suite**

Run: `.venv/bin/pytest -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add src/liturgy/commune.py tests/test_commune.py
git commit -m "feat(commune): interactive session with incomplete-input handling"
```

---

### Task 11: README and worked example

**Files:**
- Create: `README.md`
- Create: `examples/fibonacci.lit`
- Test: `tests/test_examples.py`

**Interfaces:**
- Consumes: `liturgy.loader.chant`.
- Produces: nothing importable.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_examples.py
import pathlib
import subprocess
import sys

EXAMPLES = pathlib.Path(__file__).parent.parent / "examples"


def test_fibonacci_example_runs():
    out = subprocess.run(
        [sys.executable, "-m", "liturgy", "chant", str(EXAMPLES / "fibonacci.lit")],
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stderr
    assert "55" in out.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_examples.py -v`
Expected: FAIL. `examples/fibonacci.lit` does not exist

- [ ] **Step 3: Write `examples/fibonacci.lit`**

```
## The Rite of Recurrent Numeration
## Chanted before the cogitator, that it may recall the sacred sequence.

rite fibonacci(n):
    should n < 2:
        render n
    render fibonacci(n - 1) + fibonacci(n - 2)


rite litany_of_numeration(count):
    foreach i among span(count):
        intone(f"++ the {i}th number is {fibonacci(i)} ++")


should __name__ == "__main__":
    litany_of_numeration(11)
```

- [ ] **Step 4: Write `README.md`**

Cover, in this order: what Liturgy is; a hello-world; installation; `chant` and `commune`; the superset promise stated exactly as the spec words it ("all valid Python is valid Liturgy, except programs that use a Liturgy word as an identifier"); the full KEYWORDS table; the heresy rebuke with an example transcript; `--profane` and `LITURGY_PIOUS=0`; the Python 3.12 floor and why; and a "not yet built" section naming Spec II constructs and Spec III verbs. Link both spec and plan.

- [ ] **Step 5: Run the whole suite**

Run: `.venv/bin/pytest -v`
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add README.md examples tests/test_examples.py
git commit -m "docs: README and worked fibonacci example"
```
