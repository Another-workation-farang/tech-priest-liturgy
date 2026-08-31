# Liturgy Constructs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three constructs Python cannot express — `consecrated`, `litany`, `augur` — so Liturgy is a superset in substance and not only in spelling.

**Architecture:** A token-level carrier pass rewrites construct headers **in place, on one line**, into valid Python that parses (annotated assignments and `with` blocks). A new `compile_litany()` then parses that text, runs an `ast.NodeTransformer` that restructures the carriers into real semantics, and compiles. The line invariant is preserved textually by the carrier pass; the AST pass is free to add nodes because it never touches text.

**Tech Stack:** Python 3.12+, stdlib only (`tokenize`, `ast`, `token`). pytest.

**Spec:** `docs/superpowers/specs/2026-08-31-liturgy-constructs-design.md`

## Global Constraints

- **No runtime.** Every construct desugars into self-contained generated Python. Liturgy ships no helper module and the generated code imports nothing from Liturgy. Where that cost is too high, the feature is cut rather than the constraint bent.
- **Minimum Python 3.12.** Stdlib only, no runtime dependencies.
- **Line invariant.** The carrier pass MUST never add or remove a line. `_splice` already raises `ValueError` on a substitution containing a newline; do not defeat that.
- **Every synthesised AST node gets a position** via `ast.copy_location` from its construct header. A node without one is a traceback without a line.
- **Statement position is required.** `litany(3)` in an expression is somebody's function call. Only a construct keyword beginning a statement is a construct. This is the exact shape of the Critical finding in Spec I's final review, where a rule fired on a name without checking position and turned `chain.invoke(x)` into `chain.import(x)`.
- **`TechHeresy` is the single compile-time rejection type.** It subclasses `SyntaxError` and sets `filename`, `lineno`, `offset`, `text`.
- **All 359 existing tests must pass.** `DEFAULT_PASSES` changing is the risk; the round-trip property test is the tripwire.

## File Structure

| File | Responsibility |
|---|---|
| `src/liturgy/lexicon.py` (modify) | Gains `NUMERALS`, `CONSTRUCT_KEYWORDS`, `RESERVED` |
| `src/liturgy/constructs.py` (create) | `TechHeresy`, statement-position detection, `carrier_pass` |
| `src/liturgy/rewrite.py` (create) | `ConstructPass` — the `NodeTransformer` and the three rewriters |
| `src/liturgy/compiler.py` (create) | `compile_litany()` — transform, parse, rewrite, compile |
| `src/liturgy/loader.py` (modify) | `source_to_code` and `chant` call `compile_litany` |
| `src/liturgy/commune.py` (modify) | `runsource` calls `compile_litany` |

---

### Task 1: Numerals and the reserved set

**Files:**
- Modify: `src/liturgy/lexicon.py`
- Test: `tests/test_lexicon.py`

**Interfaces:**
- Produces: `liturgy.lexicon.NUMERALS: dict[str, str]`; `CONSTRUCT_KEYWORDS: frozenset[str]`; `RESERVED: frozenset[str]`. `LEXICON` now includes `NUMERALS`.

`NUMERALS` cannot go in `SOFTWORDS` or `KEYWORDS`: those tables' targets are validated with `hasattr(builtins, target)` and against `keyword.kwlist`, and `"3"` is neither.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_lexicon.py
import pytest

from liturgy import lexicon


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
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_lexicon.py -v -k "numeral or construct or reserved"`
Expected: FAIL with `AttributeError: module 'liturgy.lexicon' has no attribute 'NUMERALS'`

- [ ] **Step 3: Modify `src/liturgy/lexicon.py`**

Add after the `CURSES` table, and replace the existing `LEXICON`/`INVERSE` lines:

```python
# Numeral words. Targets are integer literals, not Python names, so these
# cannot live in KEYWORDS or SOFTWORDS -- those tables' targets are validated
# against keyword.kwlist and builtins respectively.
NUMERALS: dict[str, str] = {
    "twice": "2",
    "thrice": "3",
}

# Recognised by the carrier pass, not substituted by the alias pass: they map
# to no Python word at all. Reserved nonetheless.
CONSTRUCT_KEYWORDS: frozenset[str] = frozenset(
    {"consecrated", "litany", "augur"}
)

LEXICON: dict[str, str] = {**KEYWORDS, **SOFTWORDS, **CURSES, **NUMERALS}
INVERSE: dict[str, str] = {py: lit for lit, py in LEXICON.items()}

# The one place that answers "is this word taken". Consumed by the corpus
# sweep's skip logic, the documented count, and Spec III's augur lint.
RESERVED: frozenset[str] = frozenset(LEXICON) | CONSTRUCT_KEYWORDS
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all pass. `INVERSE` gaining `"2"` and `"3"` keys is harmless — the reverse pass only looks up NAME tokens, and `2` is a NUMBER.

- [ ] **Step 5: Commit**

```bash
git add src/liturgy/lexicon.py tests/test_lexicon.py
git commit -m "feat(lexicon): numeral words and a single reserved set"
```

---

### Task 2: compile_litany, wired but inert

**Files:**
- Create: `src/liturgy/compiler.py`
- Modify: `src/liturgy/loader.py`
- Modify: `src/liturgy/commune.py`
- Test: `tests/test_compiler.py`

**Interfaces:**
- Consumes: `liturgy.transform.transform(src, passes=..., *, filename=...) -> tuple[str, SourceMap]`.
- Produces: `liturgy.compiler.compile_litany(src: str, filename: str, *, mode: str = "exec", dont_inherit: bool = True, optimize: int = -1) -> types.CodeType`.

This task changes the compile path with **no behaviour change**, so the integration risk is isolated from the semantics. Later tasks add the AST pass inside it.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_compiler.py
import ast

import pytest

from liturgy.compiler import compile_litany
from liturgy.transform import UnfinishedLitany


def test_compiles_liturgy_to_a_working_code_object():
    code = compile_litany('intone("ave")\n', "<test>")
    ns = {}
    exec(code, ns)


def test_result_carries_the_filename():
    code = compile_litany("x = 1\n", "prayer.lit")
    assert code.co_filename == "prayer.lit"


def test_single_mode_supports_the_repl():
    code = compile_litany("1 + 1\n", "<commune>", mode="single")
    exec(code, {})


def test_unfinished_input_still_raises_unfinished_litany():
    with pytest.raises(UnfinishedLitany):
        compile_litany("x = (1, 2\n", "prayer.lit")


def test_syntax_errors_carry_the_filename():
    with pytest.raises(SyntaxError) as exc:
        compile_litany("rite f(:\n", "prayer.lit")
    assert exc.value.filename == "prayer.lit"


def test_line_numbers_are_liturgy_line_numbers():
    code = compile_litany("x = 1\ny = 2\nproclaim MachineCurse('here')\n", "p.lit")
    try:
        exec(code, {})
    except Exception:
        import sys, traceback

        assert traceback.extract_tb(sys.exc_info()[2])[-1].lineno == 3
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_compiler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'liturgy.compiler'`

- [ ] **Step 3: Create `src/liturgy/compiler.py`**

```python
"""Liturgy source to a code object.

`transform` is text-to-text and stays that way -- the reverse pass, the
round-trip property and most of the suite are built on it. The construct
layer needs an AST stage between parse and compile, so it layers on top
here rather than changing that contract.
"""

from __future__ import annotations

import ast
import types

from .transform import transform


def compile_litany(
    src: str,
    filename: str,
    *,
    mode: str = "exec",
    dont_inherit: bool = True,
    optimize: int = -1,
) -> types.CodeType:
    """Compile Liturgy source, applying the construct rewrites.

    Raises:
        UnfinishedLitany: the source ends mid-bracket or mid-string.
        SyntaxError: a complete tokenisation or parse error.
        TechHeresy: a construct was used in a way the compiler rejects.
    """
    py, _smap = transform(src, filename=filename)
    tree = ast.parse(py, filename, mode)
    return compile(
        tree, filename, mode, dont_inherit=dont_inherit, optimize=optimize
    )
```

- [ ] **Step 4: Wire `src/liturgy/loader.py`**

Replace the body of `source_to_code` so it reads:

```python
    def source_to_code(self, data, path, *, _optimize=-1):  # noqa: D102
        src = importlib.util.decode_source(data)
        return compile_litany(src, path, optimize=_optimize)
```

In `chant`, replace the `exec(compile(py, path, ...))` line with:

```python
        exec(compile_litany(src, path), module.__dict__)
```

Delete the now-unused local that held the transform result in `chant`, add `from .compiler import compile_litany` to the imports, and drop the `from .transform import transform` import if nothing else in the file uses it. **Keep the `curse.record_source(path, src)` call exactly where it is** — the Task 7 fix in Spec I depends on it.

- [ ] **Step 5: Wire `src/liturgy/commune.py`**

`codeop` stays the oracle for "is this input complete?", but the real compile goes through `compile_litany`. In `runsource`, after the existing completeness check returns a non-`None` code object, discard it and compile properly:

```python
        if compiled is None:
            return True  # incomplete

        try:
            compiled = compile_litany(source, filename, mode=symbol)
        except SyntaxError:
            self.showsyntaxerror(filename)
            return False

        self.runcode(compiled)
        return False
```

Add `from .compiler import compile_litany` to the imports. The double compile is invisible at REPL speed and keeps `codeop`'s incomplete-input detection, which nothing else provides.

- [ ] **Step 6: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all pass — 359 existing plus 6 new. Any failure here is an integration bug, not a semantics bug, which is why this task is separate.

- [ ] **Step 7: Commit**

```bash
git add src/liturgy/compiler.py src/liturgy/loader.py src/liturgy/commune.py tests/test_compiler.py
git commit -m "feat(compiler): compile_litany as the single compile path"
```

---

### Task 3: TechHeresy and statement-position detection

**Files:**
- Create: `src/liturgy/constructs.py`
- Test: `tests/test_constructs.py`

**Interfaces:**
- Consumes: `liturgy.transform.Substitution`, `_INSIGNIFICANT`, `_OPENERS`, `_CLOSERS`.
- Produces: `liturgy.constructs.TechHeresy(SyntaxError)`; `heresy(message, filename, lineno, offset, text) -> TechHeresy`; `statement_starts(significant: list[TokenInfo]) -> set[int]`.

`statement_starts` is the defence against the Spec I failure mode. It is built and tested alone, before any construct uses it.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_constructs.py
import io
import token as tokmod
import tokenize

from liturgy import transform as _t
from liturgy.constructs import TechHeresy, heresy, statement_starts


def positions(src):
    """Names at statement-start position, by their text."""
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    significant = [t for t in toks if t.type not in _t._INSIGNIFICANT]
    starts = statement_starts(significant)
    return {
        significant[i].string
        for i in starts
        if significant[i].type == tokmod.NAME
    }


def test_first_token_of_a_file_is_a_statement_start():
    assert "alpha" in positions("alpha = 1\n")


def test_token_after_a_newline_is_a_statement_start():
    assert "beta" in positions("alpha = 1\nbeta = 2\n")


def test_token_after_a_semicolon_is_a_statement_start():
    assert "beta" in positions("alpha = 1; beta = 2\n")


def test_token_after_a_block_colon_is_a_statement_start():
    assert "beta" in positions("if alpha: beta = 2\n")


def test_token_inside_a_call_is_not_a_statement_start():
    assert "beta" not in positions("alpha(beta)\n")


def test_dict_value_after_a_colon_is_not_a_statement_start():
    # The colon rule must not fire inside brackets.
    assert "beta" not in positions("alpha = {1: beta}\n")


def test_slice_bound_after_a_colon_is_not_a_statement_start():
    assert "beta" not in positions("alpha = items[1:beta]\n")


def test_annotation_after_a_colon_is_not_a_statement_start():
    assert "int" not in positions("alpha: int = 1\n")


def test_indented_body_token_is_a_statement_start():
    assert "beta" in positions("if alpha:\n    beta = 2\n")


def test_bare_block_openers_are_handled():
    # `else:` and `try:` have no expression before the colon.
    assert "beta" in positions("if a:\n    pass\nelse: beta = 2\n")
    assert "beta" in positions("try: beta = 2\nexcept E:\n    pass\n")


def test_liturgy_spellings_open_blocks_too():
    # The carrier pass runs before substitution, so the token stream holds
    # whichever spelling the author used.
    assert "beta" in positions("should alpha: beta = 2\n")
    assert "beta" in positions("foreach x among y: beta = 2\n")


def test_lambda_colon_does_not_start_a_statement():
    assert "beta" not in positions("alpha = lambda: beta\n")
    assert "beta" not in positions("alpha = servitor: beta\n")


def test_heresy_carries_everything_the_curse_renderer_needs():
    exc = heresy("no", "prayer.lit", 3, 5, "consecrated X = 1\n")
    assert isinstance(exc, TechHeresy)
    assert isinstance(exc, SyntaxError)
    assert (exc.filename, exc.lineno, exc.offset) == ("prayer.lit", 3, 5)
    assert exc.text == "consecrated X = 1\n"
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_constructs.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'liturgy.constructs'`

- [ ] **Step 3: Create `src/liturgy/constructs.py`**

The annotation case is why the colon rule needs the depth-zero *and* a
preceding-NEWLINE check rather than the colon alone: `alpha: int = 1` has a
depth-zero colon that opens no block.

```python
"""Construct headers: recognising them, and rejecting their misuse.

The carrier pass rewrites a construct header in place, on one line, into
valid Python that parses. The AST pass in `rewrite` then restructures it.
"""

from __future__ import annotations

import token as tokmod
import tokenize

from .transform import _CLOSERS, _OPENERS


# Statements whose depth-zero `:` opens a block. Both spellings appear,
# because the carrier pass runs on the same token stream as the alias pass --
# before substitution -- and a .lit file may legally use either.
_BLOCK_OPENERS = frozenset(
    {
        # Python
        "if", "elif", "else", "for", "while", "with", "def", "class",
        "try", "except", "finally", "match", "case", "async",
        # Liturgy
        "should", "lest", "otherwise", "foreach", "whilst", "anointed",
        "rite", "pattern", "attempt", "curse", "regardless", "discern",
        "wherein", "remote",
        # Spec II block constructs
        "litany", "augur",
    }
)


class TechHeresy(SyntaxError):
    """A construct used in a way the compiler rejects.

    A SyntaxError subclass so that `curse SyntaxError` catches it and the
    curse renderer already knows how to show its file, line and caret.
    """


def heresy(
    message: str,
    filename: str,
    lineno: int,
    offset: int,
    text: str,
) -> TechHeresy:
    """Build a TechHeresy carrying everything the curse renderer needs."""
    exc = TechHeresy(message)
    exc.filename = filename
    exc.lineno = lineno
    exc.offset = offset
    exc.text = text
    return exc


def statement_starts(significant: list[tokenize.TokenInfo]) -> set[int]:
    """Indices in `significant` that begin a logical statement.

    A construct keyword is only a construct here. Everywhere else it is
    somebody's identifier, and substituting it would repeat the Spec I
    failure where a rule fired on a name without checking its position.

    A statement begins at the start of input, after a logical NEWLINE, or
    after a `;` or a block-opening `:` at bracket depth zero.

    Two things make the colon case correct. The depth test keeps `{1: x}`
    and `items[1:x]` out. Consulting the statement's *head* keeps
    `alpha: int = 1` out -- an annotation colon opens no block, and only a
    statement that began with a compound keyword has a colon that does.
    """
    starts: set[int] = set()
    depth = 0
    fresh = True
    head = ""  # first token of the statement in progress

    for i, tok in enumerate(significant):
        if tok.type == tokmod.NEWLINE:
            fresh = True
            head = ""
            continue

        if tok.type == tokmod.OP:
            if tok.string in _OPENERS:
                depth += 1
            elif tok.string in _CLOSERS:
                depth -= 1
            elif depth == 0 and tok.string == ";":
                fresh = True
                head = ""
                continue
            elif depth == 0 and tok.string == ":" and head in _BLOCK_OPENERS:
                # A block-opening colon starts a new statement after it.
                # An annotation colon (`x: int = 1`) does not, which is why
                # the head of the statement has to be consulted.
                fresh = True
                head = ""
                continue
            fresh = False
            continue

        if fresh:
            starts.add(i)
            head = tok.string
        fresh = False

    return starts
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all pass, 10 new.

- [ ] **Step 5: Commit**

```bash
git add src/liturgy/constructs.py tests/test_constructs.py
git commit -m "feat(constructs): TechHeresy and statement-position detection"
```

---

### Task 4: consecrated

**Files:**
- Modify: `src/liturgy/constructs.py` (add `carrier_pass`)
- Create: `src/liturgy/rewrite.py`
- Modify: `src/liturgy/transform.py` (append `carrier_pass` to `DEFAULT_PASSES`)
- Modify: `src/liturgy/compiler.py` (run `ConstructPass`)
- Test: `tests/test_consecrated.py`

**Interfaces:**
- Consumes: `statement_starts`, `heresy`, `TechHeresy`, `Substitution`, `compile_litany`.
- Produces: `liturgy.constructs.carrier_pass(toks) -> list[Substitution]`; `liturgy.rewrite.ConstructPass(filename: str, lines: list[str])` — an `ast.NodeTransformer` with `.visit(tree)`.

Carrier and rewrite land together: `PORT: __consecrated__ = 8080` is valid Python but evaluates `__consecrated__` as an annotation on 3.12 and 3.13, so a carrier with no rewrite behind it is a `NameError` waiting to happen.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_consecrated.py
import pytest

from liturgy.compiler import compile_litany
from liturgy.constructs import TechHeresy


def run(src):
    ns = {}
    exec(compile_litany(src, "prayer.lit"), ns)
    return ns


def test_a_consecrated_binding_holds_its_value():
    assert run("consecrated PORT = 8080\n")["PORT"] == 8080


def test_the_annotation_carrier_does_not_survive_into_the_module():
    ns = run("consecrated PORT = 8080\n")
    assert "__consecrated__" not in ns
    assert ns.get("__annotations__", {}) == {}


def test_indentation_is_preserved():
    ns = run("rite f():\n    consecrated INNER = 1\n    render INNER\n")
    assert ns["f"]() == 1


@pytest.mark.parametrize(
    "rebinding",
    [
        "PORT = 9090",
        "PORT += 1",
        "PORT: int = 9090",
        "(PORT := 9090)",
        "foreach PORT among span(3):\n    abide",
        "anointed unseal('f') styled PORT:\n    abide",
        "purge PORT",
        "invoke os styled PORT",
        "PORT, other = 1, 2",
        "[PORT] = [1]",
        "consecrated PORT = 1",
    ],
)
def test_rebinding_a_consecrated_name_is_rejected(rebinding):
    src = f"consecrated PORT = 8080\n{rebinding}\n"
    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    assert "PORT" in str(exc.value)
    assert exc.value.filename == "prayer.lit"
    assert exc.value.lineno == 2


def test_consecrating_inside_a_loop_is_rejected():
    # Rebinds on every iteration while looking like a single declaration.
    src = "foreach i among span(3):\n    consecrated X = i\n"
    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    assert "loop" in str(exc.value)


def test_a_different_name_is_unaffected():
    ns = run("consecrated PORT = 8080\nOTHER = 1\nOTHER = 2\n")
    assert ns["OTHER"] == 2


def test_a_nested_scope_may_use_the_name_freely():
    # Shadowing in a function is a different binding, not a rebinding.
    src = "consecrated PORT = 8080\nrite f():\n    PORT = 1\n    render PORT\n"
    ns = run(src)
    assert ns["f"]() == 1 and ns["PORT"] == 8080


def test_rebinding_through_universal_is_rejected():
    src = (
        "consecrated PORT = 8080\n"
        "rite f():\n"
        "    universal PORT\n"
        "    PORT = 1\n"
    )
    with pytest.raises(TechHeresy):
        compile_litany(src, "prayer.lit")


def test_the_error_is_a_syntax_error_so_curses_render_it():
    with pytest.raises(SyntaxError):
        compile_litany("consecrated P = 1\nP = 2\n", "prayer.lit")
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_consecrated.py -v`
Expected: FAIL — `consecrated PORT = 8080` is not yet valid syntax, so every test errors at compile.

- [ ] **Step 3: Add `carrier_pass` to `src/liturgy/constructs.py`**

Two substitutions on one line. The first spans from `consecrated` to the start of the name, so the indentation before `consecrated` is untouched and no stray leading space is left behind.

```python
from .lexicon import CONSTRUCT_KEYWORDS
from .transform import Substitution


def carrier_pass(toks: list[tokenize.TokenInfo]) -> list[Substitution]:
    """Rewrite construct headers, in place, into parseable Python."""
    significant = [t for t in toks if t.type not in _INSIGNIFICANT]
    starts = statement_starts(significant)
    subs: list[Substitution] = []

    for i in sorted(starts):
        tok = significant[i]
        if tok.type != tokmod.NAME or tok.string not in CONSTRUCT_KEYWORDS:
            continue
        if tok.string == "consecrated":
            subs.extend(_consecrated_carrier(significant, i))

    return subs


def _consecrated_carrier(
    significant: list[tokenize.TokenInfo], i: int
) -> list[Substitution]:
    """`consecrated NAME = v` -> `NAME: __consecrated__ = v`."""
    kw = significant[i]
    name = significant[i + 1] if i + 1 < len(significant) else None
    if name is None or name.type != tokmod.NAME:
        raise heresy(
            "consecrated must be followed by a name",
            "<unknown>", kw.start[0], kw.start[1] + 1, kw.line,
        )
    return [
        # Swallow the keyword and the space after it, keeping indentation.
        Substitution(kw.start[0], kw.start[1], name.start[1], ""),
        Substitution(
            name.start[0], name.start[1], name.end[1],
            f"{name.string}: __consecrated__",
        ),
    ]
```

Also add `_INSIGNIFICANT` to the `from .transform import ...` line.

- [ ] **Step 4: Append the pass in `src/liturgy/transform.py`**

`carrier_pass` lives in `constructs`, which imports `transform` — so import it lazily inside a function to avoid a cycle, or (preferred) leave `DEFAULT_PASSES` alone and have `compile_litany` pass both passes explicitly:

```python
# in src/liturgy/compiler.py
from .constructs import carrier_pass
from .transform import DEFAULT_PASSES, transform

_PASSES = (*DEFAULT_PASSES, carrier_pass)
```

and call `transform(src, _PASSES, filename=filename)`. This keeps `transform`'s default text-to-text behaviour unchanged, so `_reverse` and the round-trip property are untouched — which is the whole reason `transform` took a `passes` argument.

- [ ] **Step 5: Create `src/liturgy/rewrite.py`**

```python
"""The construct AST pass.

Carriers arrive as annotated assignments and `with` blocks. This turns them
into real semantics, and rejects the misuses the compiler can see.
"""

from __future__ import annotations

import ast

from .constructs import heresy


class ConstructPass(ast.NodeTransformer):
    def __init__(self, filename: str, lines: list[str]) -> None:
        self.filename = filename
        self.lines = lines

    def _heresy(self, node: ast.AST, message: str):
        line = node.lineno
        text = self.lines[line - 1] if line - 1 < len(self.lines) else ""
        return heresy(
            message, self.filename, line, (node.col_offset or 0) + 1, text
        )

    # -- scopes ------------------------------------------------------
    def visit_Module(self, node):
        return self._scope(node)

    def visit_FunctionDef(self, node):
        return self._scope(node)

    def visit_AsyncFunctionDef(self, node):
        return self._scope(node)

    def visit_ClassDef(self, node):
        return self._scope(node)

    def _scope(self, node):
        consecrated = _collect_consecrated(node, self._heresy)
        if consecrated:
            _reject_rebindings(node, consecrated, self._heresy)
        self.generic_visit(node)
        return node
```

Add the two module-level helpers below it:

```python
_LOOPS = (ast.For, ast.AsyncFor, ast.While)
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _collect_consecrated(scope, mkerr) -> dict[str, ast.AST]:
    """Find `NAME: __consecrated__ = v` directly in this scope's body.

    Rewrites each into a plain assignment as it goes, and records the
    *replacement* node -- the rebinding check compares against these by
    identity, so recording the original would make every declaration look
    like a rebinding of itself. Nested function and class scopes are left
    for their own visit.
    """
    found: dict[str, ast.AST] = {}

    def walk(body, in_loop):
        for index, stmt in enumerate(body):
            if isinstance(stmt, _SCOPES):
                continue
            if _is_consecrated(stmt):
                name = stmt.target.id
                if in_loop:
                    raise mkerr(stmt, f"{name} is consecrated inside a loop")
                if name in found:
                    raise mkerr(stmt, f"{name} is already consecrated")
                stmt.target.ctx = ast.Store()
                plain = ast.Assign(targets=[stmt.target], value=stmt.value)
                ast.copy_location(plain, stmt)
                ast.fix_missing_locations(plain)
                body[index] = plain
                found[name] = plain
                continue
            for _field, value in ast.iter_fields(stmt):
                if (
                    isinstance(value, list)
                    and value
                    and isinstance(value[0], ast.stmt)
                ):
                    walk(value, in_loop or isinstance(stmt, _LOOPS))

    walk(scope.body, False)
    return found


def _is_consecrated(stmt) -> bool:
    return (
        isinstance(stmt, ast.AnnAssign)
        and isinstance(stmt.annotation, ast.Name)
        and stmt.annotation.id == "__consecrated__"
        and isinstance(stmt.target, ast.Name)
        and stmt.value is not None
    )


def _reject_rebindings(scope, consecrated, mkerr) -> None:
    """Reject every rebinding the compiler can see.

    Descends through this scope's own blocks but NOT into nested function
    or class scopes: a function assigning the same name is making its own
    local binding, not rebinding ours. `ast.walk` is deliberately not used
    for that reason -- it would flatten the tree and reject legitimate
    shadowing.

    A nested scope counts only when it declares the name `global` or
    `nonlocal` and then assigns to it, which is a real rebinding and is
    visible. What is not visible -- setattr, globals(), assignment through
    the module object, exec -- is not enforced, and the documentation says
    so.
    """
    declarations = set(consecrated)
    declaring = {id(node) for node in consecrated.values()}

    def check(node):
        for name, at in _stored_names(node):
            if name in declarations and id(at) not in declaring:
                raise mkerr(at, f"{name} is consecrated and may not be rebound")

    def walk(node):
        if isinstance(node, _SCOPES) and node is not scope:
            _check_nested(node, declarations, mkerr)
            return
        check(node)
        for child in ast.iter_child_nodes(node):
            walk(child)

    for stmt in scope.body:
        walk(stmt)


def _check_nested(fn, declarations, mkerr) -> None:
    """A nested scope rebinds ours only via `universal`/`adjacent`."""
    declared: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            declared.update(node.names)
    reaching = declarations & declared
    if not reaching:
        return
    for node in ast.walk(fn):
        for name, at in _stored_names(node):
            if name in reaching:
                raise mkerr(at, f"{name} is consecrated and may not be rebound")


def _stored_names(node):
    """(name, node) for every binding this statement performs."""
    if isinstance(node, ast.Assign):
        for t in node.targets:
            yield from ((n.id, node) for n in _names_in_target(t))
    elif isinstance(node, ast.AugAssign):
        yield from ((n.id, node) for n in _names_in_target(node.target))
    elif isinstance(node, ast.AnnAssign) and node.value is not None:
        yield from ((n.id, node) for n in _names_in_target(node.target))
    elif isinstance(node, ast.NamedExpr):
        yield node.target.id, node
    elif isinstance(node, (ast.For, ast.AsyncFor)):
        yield from ((n.id, node) for n in _names_in_target(node.target))
    elif isinstance(node, ast.withitem) and node.optional_vars is not None:
        yield from (
            (n.id, node) for n in _names_in_target(node.optional_vars)
        )
    elif isinstance(node, ast.Delete):
        for t in node.targets:
            yield from ((n.id, node) for n in _names_in_target(t))
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        for alias in node.names:
            yield alias.asname or alias.name.split(".")[0], node


def _names_in_target(target):
    if isinstance(target, ast.Name):
        yield target
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            yield from _names_in_target(elt)
    elif isinstance(target, ast.Starred):
        yield from _names_in_target(target.value)
```

Two things in the above are easy to get wrong and were wrong in an earlier
draft of this plan:

- `_collect_consecrated` records the **replacement** `Assign`, not the original
  `AnnAssign`. Recording the original makes the identity check in
  `_reject_rebindings` miss, and every declaration is reported as a rebinding
  of itself.
- `_reject_rebindings` uses a hand-written recursive walk rather than
  `ast.walk`, because `ast.walk` descends into nested functions. With it,
  `test_a_nested_scope_may_use_the_name_freely` fails: a function making its
  own local `PORT` is shadowing, not rebinding.

`_is_consecrated` requires `stmt.value is not None`: a bare `X: __consecrated__` with no value declares nothing and must not register a name.

- [ ] **Step 6: Run `ConstructPass` in `src/liturgy/compiler.py`**

```python
    py, _smap = transform(src, _PASSES, filename=filename)
    tree = ast.parse(py, filename, mode)
    tree = ConstructPass(filename, split_lines(src)).visit(tree)
    ast.fix_missing_locations(tree)
    return compile(tree, filename, mode, dont_inherit=dont_inherit, optimize=optimize)
```

Import `ConstructPass` from `.rewrite` and `split_lines` from `.transform`. `split_lines` gives the **Liturgy** lines, so a `TechHeresy` quotes the source the author wrote.

- [ ] **Step 7: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/liturgy/constructs.py src/liturgy/rewrite.py src/liturgy/compiler.py tests/test_consecrated.py
git commit -m "feat(constructs): consecrated, with compile-time rebinding checks"
```

---

### Task 5: litany

**Files:**
- Modify: `src/liturgy/constructs.py` (`_litany_carrier`)
- Modify: `src/liturgy/rewrite.py` (`visit_With` handling `__litany__`)
- Test: `tests/test_litany.py`

**Interfaces:**
- Consumes: everything from Task 4.
- Produces: no new public names. `ConstructPass` gains `visit_With`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_litany.py
import pytest

from liturgy.compiler import compile_litany
from liturgy.constructs import TechHeresy


def run(src, **ns):
    exec(compile_litany(src, "prayer.lit"), ns)
    return ns


def test_a_succeeding_body_runs_once():
    ns = run(
        "calls = []\n"
        "litany(thrice, curse=MotiveFailure):\n"
        "    calls.append(1)\n"
    )
    assert ns["calls"] == [1]


def test_exhausted_attempts_reraise_the_last_curse():
    src = (
        "calls = []\n"
        "litany(thrice, curse=MotiveFailure):\n"
        "    calls.append(1)\n"
        "    proclaim MotiveFailure('again')\n"
    )
    ns = {}
    with pytest.raises(RuntimeError):
        exec(compile_litany(src, "prayer.lit"), ns)
    assert ns["calls"] == [1, 1, 1]


def test_it_stops_as_soon_as_the_body_succeeds():
    src = (
        "calls = []\n"
        "litany(thrice, curse=MotiveFailure):\n"
        "    calls.append(1)\n"
        "    should measure(calls) < 2:\n"
        "        proclaim MotiveFailure('again')\n"
    )
    assert run(src)["calls"] == [1, 1]


def test_an_unnamed_curse_is_not_caught():
    # The whole point of requiring the filter: a TypeError surfaces at once.
    src = (
        "calls = []\n"
        "litany(thrice, curse=MotiveFailure):\n"
        "    calls.append(1)\n"
        "    proclaim PatternMismatch('wrong')\n"
    )
    ns = {}
    with pytest.raises(TypeError):
        exec(compile_litany(src, "prayer.lit"), ns)
    assert ns["calls"] == [1]


def test_a_tuple_of_curses_is_accepted():
    src = (
        "calls = []\n"
        "litany(twice, curse=(MotiveFailure, ImpureOffering)):\n"
        "    calls.append(1)\n"
        "    proclaim ImpureOffering('again')\n"
    )
    ns = {}
    with pytest.raises(ValueError):
        exec(compile_litany(src, "prayer.lit"), ns)
    assert ns["calls"] == [1, 1]


def test_the_count_is_evaluated_exactly_once():
    src = (
        "rolls = []\n"
        "rite roll():\n"
        "    rolls.append(1)\n"
        "    render 2\n"
        "litany(roll(), curse=MotiveFailure):\n"
        "    proclaim MotiveFailure('again')\n"
    )
    ns = {}
    with pytest.raises(RuntimeError):
        exec(compile_litany(src, "prayer.lit"), ns)
    assert ns["rolls"] == [1], "the count expression must be evaluated once"


def test_resting_pauses_between_attempts(monkeypatch):
    import time

    slept = []
    monkeypatch.setattr(time, "sleep", slept.append)
    src = (
        "litany(thrice, resting=0.25, curse=MotiveFailure):\n"
        "    proclaim MotiveFailure('again')\n"
    )
    with pytest.raises(RuntimeError):
        exec(compile_litany(src, "prayer.lit"), {})
    assert slept == [0.25, 0.25], "rests between attempts, not after the last"


def test_omitting_resting_emits_no_timing_code():
    py_free = compile_litany(
        "litany(twice, curse=MotiveFailure):\n    abide\n", "p.lit"
    )
    assert "time" not in str(py_free.co_consts) + " ".join(py_free.co_names)


def test_cease_in_a_litany_body_is_rejected():
    src = "litany(twice, curse=MotiveFailure):\n    cease\n"
    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    assert "cease" in str(exc.value)


def test_persist_in_a_litany_body_is_rejected():
    src = "litany(twice, curse=MotiveFailure):\n    persist\n"
    with pytest.raises(TechHeresy):
        compile_litany(src, "prayer.lit")


def test_cease_inside_a_real_loop_in_the_body_is_fine():
    src = (
        "seen = []\n"
        "litany(twice, curse=MotiveFailure):\n"
        "    foreach i among span(5):\n"
        "        seen.append(i)\n"
        "        cease\n"
    )
    assert run(src)["seen"] == [0]


def test_render_in_a_litany_body_is_fine():
    src = (
        "rite f():\n"
        "    litany(thrice, curse=MotiveFailure):\n"
        "        render 7\n"
        "    render 0\n"
    )
    assert run(src)["f"]() == 7


def test_a_literal_count_below_one_is_rejected():
    with pytest.raises(TechHeresy) as exc:
        compile_litany("litany(0, curse=MotiveFailure):\n    abide\n", "p.lit")
    assert "at least once" in str(exc.value)


def test_a_computed_count_below_one_is_caught_at_runtime():
    src = "n = 0\nlitany(n, curse=MotiveFailure):\n    abide\n"
    with pytest.raises(ValueError):
        exec(compile_litany(src, "prayer.lit"), {})


def test_curse_passed_positionally_is_rejected():
    with pytest.raises(TechHeresy) as exc:
        compile_litany("litany(twice, MotiveFailure):\n    abide\n", "p.lit")
    assert "keyword" in str(exc.value)


def test_a_missing_curse_is_rejected():
    with pytest.raises(TechHeresy) as exc:
        compile_litany("litany(twice):\n    abide\n", "p.lit")
    assert "curse" in str(exc.value)


def test_a_construct_keyword_after_an_annotation_colon_is_untouched():
    # NAMED REGRESSION. `match` is a legal identifier (a Python soft keyword,
    # never substituted), so `match: ...` is an annotated assignment, not a
    # block. Statement position alone would wrongly fire here.
    ns = run("rite f(litany_count):\n    render litany_count\nmatch: int = 5\n")
    assert ns["match"] == 5


def test_litany_as_a_plain_call_is_untouched():
    # NAMED REGRESSION. Somebody's function, not a construct.
    ns = run("rite litany(n):\n    render n * 2\nresult = litany(3)\n")
    assert ns["result"] == 6
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_litany.py -v`
Expected: FAIL — `litany(...)` at statement position is not yet rewritten.

- [ ] **Step 3: Add `_litany_carrier` to `src/liturgy/constructs.py`**

One token swap. `litany` becomes `with __litany__`, and every argument survives untouched — including `curse=`, which Spec I's Rule 2 already protects as a keyword-argument name.

```python
def opens_a_block(significant: list[tokenize.TokenInfo], i: int) -> bool:
    """Does the logical line starting at `significant[i]` end in a `:`?

    Statement position alone is not enough for a block construct. The spec
    requires the line to open a block, and without that check
    `match: litany(3)` -- annotating a variable named `match` -- would be
    read as a construct header. Both halves of the rule are needed.
    """
    depth = 0
    for tok in significant[i:]:
        if tok.type == tokmod.NEWLINE:
            return False
        if tok.type != tokmod.OP:
            continue
        if tok.string in _OPENERS:
            depth += 1
        elif tok.string in _CLOSERS:
            depth -= 1
        elif tok.string == ":" and depth == 0:
            return True
    return False


def _litany_carrier(
    significant: list[tokenize.TokenInfo], i: int
) -> list[Substitution]:
    """`litany(args):` -> `with __litany__(args):`."""
    kw = significant[i]
    if not opens_a_block(significant, i):
        return []  # not a construct header: somebody's call, left alone
    nxt = significant[i + 1] if i + 1 < len(significant) else None
    if nxt is None or nxt.type != tokmod.OP or nxt.string != "(":
        raise heresy(
            "litany takes a parenthesised attempt count",
            "<unknown>", kw.start[0], kw.start[1] + 1, kw.line,
        )
    return [
        Substitution(
            kw.start[0], kw.start[1], kw.end[1], "with __litany__"
        )
    ]
```

Wire it into `carrier_pass` beside the `consecrated` branch:

```python
        elif tok.string == "litany":
            subs.extend(_litany_carrier(significant, i))
```

- [ ] **Step 4: Add `visit_With` to `src/liturgy/rewrite.py`**

```python
    def visit_With(self, node):
        self.generic_visit(node)
        call = _carrier_call(node, "__litany__")
        if call is None:
            return node
        return self._litany(node, call)

    def _litany(self, node, call):
        if len(call.args) != 1:
            raise self._heresy(node, "litany takes one attempt count")
        for kw in call.keywords:
            if kw.arg not in ("resting", "curse"):
                raise self._heresy(node, f"litany has no {kw.arg} argument")
        by_name = {kw.arg: kw.value for kw in call.keywords}
        if "curse" not in by_name:
            raise self._heresy(
                node, "litany needs curse= naming what to re-attempt on"
            )
        count, rest = call.args[0], by_name.get("resting")

        if isinstance(count, ast.Constant) and isinstance(count.value, int):
            if count.value < 1:
                raise self._heresy(node, "a litany must be chanted at least once")

        _reject_loop_control(node.body, self._heresy)
        return _build_retry(node, count, rest, by_name["curse"])
```

`_carrier_call` and the loop-control check go at module level:

```python
def _carrier_call(node: ast.With, name: str):
    """The `__litany__(...)`/`__augur__()` call, if this With is a carrier."""
    if len(node.items) != 1:
        return None
    ctx = node.items[0].context_expr
    if (
        isinstance(ctx, ast.Call)
        and isinstance(ctx.func, ast.Name)
        and ctx.func.id == name
    ):
        return ctx
    return None


def _reject_loop_control(body, mkerr) -> None:
    """`cease`/`persist` at the litany's own level bind to the retry loop.

    Inside a real loop in the body they are the author's own, so this
    descends into everything except loops. `ast.walk` is deliberately not
    used: it would flatten the tree and lose the distinction, wrongly
    rejecting a legitimate `cease` inside a `foreach` in the body.
    """

    def walk(node):
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            return  # its own break target
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            return  # a different frame entirely
        if isinstance(node, ast.Break):
            raise mkerr(node, "cease in a litany body binds to the retry")
        if isinstance(node, ast.Continue):
            raise mkerr(node, "persist in a litany body binds to the retry")
        for child in ast.iter_child_nodes(node):
            walk(child)

    for stmt in body:
        walk(stmt)
```

- [ ] **Step 5: Add `_build_retry` to `src/liturgy/rewrite.py`**

The generated shape, with `__n` and `__i` bound once each:

```python
_COUNT = "__liturgy_n"
_ATTEMPT = "__liturgy_attempt"


def _build_retry(node, count, rest, curse):
    """for __i in range(__n): try: body; break; except curse: ..."""
    loc = lambda n: ast.copy_location(n, node)  # noqa: E731

    bind_n = loc(ast.Assign(
        targets=[loc(ast.Name(id=_COUNT, ctx=ast.Store()))], value=count
    ))

    guard = loc(ast.If(
        test=loc(ast.Compare(
            left=loc(ast.Name(id=_COUNT, ctx=ast.Load())),
            ops=[ast.Lt()],
            comparators=[loc(ast.Constant(value=1))],
        )),
        body=[loc(ast.Raise(
            exc=loc(ast.Call(
                func=loc(ast.Name(id="ValueError", ctx=ast.Load())),
                args=[loc(ast.Constant(
                    value="a litany must be chanted at least once"
                ))],
                keywords=[],
            )),
            cause=None,
        ))],
        orelse=[],
    ))

    # if __i == __n - 1: raise
    reraise = loc(ast.If(
        test=loc(ast.Compare(
            left=loc(ast.Name(id=_ATTEMPT, ctx=ast.Load())),
            ops=[ast.Eq()],
            comparators=[loc(ast.BinOp(
                left=loc(ast.Name(id=_COUNT, ctx=ast.Load())),
                op=ast.Sub(),
                right=loc(ast.Constant(value=1)),
            ))],
        )),
        body=[loc(ast.Raise(exc=None, cause=None))],
        orelse=[],
    ))

    handler_body = [reraise]
    if rest is not None:
        # __import__("time").sleep(rest) -- self-contained, no injected import
        handler_body.append(loc(ast.Expr(value=loc(ast.Call(
            func=loc(ast.Attribute(
                value=loc(ast.Call(
                    func=loc(ast.Name(id="__import__", ctx=ast.Load())),
                    args=[loc(ast.Constant(value="time"))],
                    keywords=[],
                )),
                attr="sleep",
                ctx=ast.Load(),
            )),
            args=[rest],
            keywords=[],
        )))))

    attempt = loc(ast.Try(
        body=[*node.body, loc(ast.Break())],
        handlers=[loc(ast.ExceptHandler(
            type=curse, name=None, body=handler_body
        ))],
        orelse=[],
        finalbody=[],
    ))

    loop = loc(ast.For(
        target=loc(ast.Name(id=_ATTEMPT, ctx=ast.Store())),
        iter=loc(ast.Call(
            func=loc(ast.Name(id="range", ctx=ast.Load())),
            args=[loc(ast.Name(id=_COUNT, ctx=ast.Load()))],
            keywords=[],
        )),
        body=[attempt],
        orelse=[],
    ))

    return [bind_n, guard, loop]
```

Returning a list from a `visit_` method splices the statements in place, which is what is wanted here.

- [ ] **Step 6: Reject a positional `curse`**

`litany(twice, MotiveFailure)` has two positional args, so the existing
`len(call.args) != 1` check fires — but its message says "one attempt count",
which is unhelpful. Special-case it in `_litany`, before that check:

```python
        if len(call.args) == 2 and not call.keywords:
            raise self._heresy(node, "curse must be passed by keyword")
```

- [ ] **Step 7: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/liturgy/constructs.py src/liturgy/rewrite.py tests/test_litany.py
git commit -m "feat(constructs): litany, a retry block with a required curse filter"
```

---

### Task 6: augur

**Files:**
- Modify: `src/liturgy/constructs.py` (`_augur_carrier`)
- Modify: `src/liturgy/rewrite.py` (`visit_With` handling `__augur__`)
- Test: `tests/test_augur.py`

**Interfaces:**
- Consumes: everything from Tasks 4 and 5, plus `liturgy.sourcemap.SourceMap.to_lit`.
- Produces: no new public names.

`augur` needs the SourceMap so its message can quote the **Liturgy** source of the failed condition, not the generated Python. `ConstructPass.__init__` gains a `smap` parameter for this.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_augur.py
import pytest

from liturgy.compiler import compile_litany
from liturgy.constructs import TechHeresy


def run(src, **ns):
    exec(compile_litany(src, "prayer.lit"), ns)
    return ns


DIVIDE = (
    "rite divide(a, b):\n"
    "    augur:\n"
    "        b be nay Void\n"
    "        b != 0\n"
    "    render a / b\n"
)


def test_a_satisfied_augury_lets_the_rite_run():
    assert run(DIVIDE)["divide"](6, 2) == 3


def test_a_failed_augury_raises_impure_offering():
    with pytest.raises(ValueError):
        run(DIVIDE)["divide"](1, 0)


def test_the_message_quotes_the_liturgy_source_not_the_python():
    with pytest.raises(ValueError) as exc:
        run(DIVIDE)["divide"](1, None)
    assert "b be nay Void" in str(exc.value)
    assert "is not None" not in str(exc.value)


def test_the_first_failing_condition_is_the_one_reported():
    with pytest.raises(ValueError) as exc:
        run(DIVIDE)["divide"](1, 0)
    assert "b != 0" in str(exc.value)


def test_it_survives_optimisation():
    # A contract, not an assertion: it must not compile away under -O.
    code = compile_litany(DIVIDE, "prayer.lit", optimize=2)
    ns = {}
    exec(code, ns)
    with pytest.raises(ValueError):
        ns["divide"](1, 0)


def test_an_augury_may_follow_a_docstring():
    src = (
        "rite f(x):\n"
        '    """Divide the thing."""\n'
        "    augur:\n"
        "        x > 0\n"
        "    render x\n"
    )
    assert run(src)["f"](2) == 2
    with pytest.raises(ValueError):
        run(src)["f"](0)


def test_an_augury_outside_a_rite_is_rejected():
    with pytest.raises(TechHeresy) as exc:
        compile_litany("augur:\n    Sanctioned\n", "prayer.lit")
    assert "rite" in str(exc.value)


def test_an_augury_after_real_statements_is_rejected():
    src = "rite f(x):\n    y = x\n    augur:\n        x > 0\n    render y\n"
    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    assert "opening" in str(exc.value)


def test_a_statement_inside_an_augury_is_rejected():
    src = "rite f(x):\n    augur:\n        y = 1\n    render x\n"
    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    assert "condition" in str(exc.value)


def test_a_nested_rite_may_have_its_own_augury():
    src = (
        "rite outer(x):\n"
        "    augur:\n"
        "        x > 0\n"
        "    rite inner(y):\n"
        "        augur:\n"
        "            y > 0\n"
        "        render y\n"
        "    render inner(x)\n"
    )
    assert run(src)["outer"](3) == 3
    with pytest.raises(ValueError):
        run(src)["outer"](0)


def test_augur_as_a_plain_call_is_untouched():
    # NAMED REGRESSION. Somebody's function, not a construct.
    ns = run("rite augur(n):\n    render n + 1\nresult = augur(1)\n")
    assert ns["result"] == 2


def test_the_traceback_points_at_the_augur_line():
    import traceback

    ns = run(DIVIDE)
    try:
        ns["divide"](1, 0)
    except ValueError:
        import sys

        frames = traceback.extract_tb(sys.exc_info()[2])
    # The synthesised raise carries the augur header's location (line 2).
    assert frames[-1].lineno == 2
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_augur.py -v`
Expected: FAIL — `augur:` is not yet rewritten.

- [ ] **Step 3: Add `_augur_carrier` to `src/liturgy/constructs.py`**

```python
def _augur_carrier(
    significant: list[tokenize.TokenInfo], i: int
) -> list[Substitution]:
    """`augur:` -> `with __augur__():`."""
    kw = significant[i]
    if not opens_a_block(significant, i):
        return []  # not a construct header: somebody's call, left alone
    nxt = significant[i + 1] if i + 1 < len(significant) else None
    if nxt is None or nxt.type != tokmod.OP or nxt.string != ":":
        raise heresy(
            "augur opens a block and takes no arguments",
            "<unknown>", kw.start[0], kw.start[1] + 1, kw.line,
        )
    return [
        Substitution(
            kw.start[0], kw.start[1], kw.end[1], "with __augur__()"
        )
    ]
```

Wire it into `carrier_pass`:

```python
        elif tok.string == "augur":
            subs.extend(_augur_carrier(significant, i))
```

- [ ] **Step 4: Give `ConstructPass` the SourceMap**

Change the constructor and the `compile_litany` call site:

```python
    def __init__(self, filename: str, lines: list[str], smap) -> None:
        self.filename = filename
        self.lines = lines
        self.smap = smap
```

```python
    # in compiler.py
    py, smap = transform(src, _PASSES, filename=filename)
    tree = ast.parse(py, filename, mode)
    tree = ConstructPass(filename, split_lines(src), smap).visit(tree)
```

Add the source-slicing helper as a method:

```python
    def _liturgy_source(self, node: ast.expr) -> str:
        """The Liturgy text of an expression, for an augury's message.

        The node's columns are generated-Python columns; the SourceMap maps
        them back, and lines are identical by the transform's invariant.
        Falls back to unparsing the Python if anything is missing.
        """
        try:
            line = self.lines[node.lineno - 1]
            start = self.smap.to_lit(node.lineno, node.col_offset)
            end = self.smap.to_lit(node.lineno, node.end_col_offset)
            text = line[start:end].strip()
            if text:
                return text
        except Exception:
            pass
        return ast.unparse(node)
```

- [ ] **Step 5: Handle `__augur__` in `visit_With`**

Extend the existing `visit_With` so it dispatches on which carrier it found:

```python
    def visit_With(self, node):
        self.generic_visit(node)
        call = _carrier_call(node, "__litany__")
        if call is not None:
            return self._litany(node, call)
        call = _carrier_call(node, "__augur__")
        if call is not None:
            return self._augur(node, call)
        return node

    def _augur(self, node, call):
        if call.args or call.keywords:
            raise self._heresy(node, "augur takes no arguments")
        checks = []
        for stmt in node.body:
            if not isinstance(stmt, ast.Expr):
                raise self._heresy(
                    stmt, "an augury holds conditions, not statements"
                )
            checks.append(self._omen(node, stmt.value))
        return checks

    def _omen(self, header, test):
        """`if not (test): raise ImpureOffering("the omens forbid it -- ...")`."""
        loc = lambda n: ast.copy_location(n, header)  # noqa: E731
        message = f"the omens forbid it -- {self._liturgy_source(test)}"
        return loc(ast.If(
            test=loc(ast.UnaryOp(op=ast.Not(), operand=test)),
            body=[loc(ast.Raise(
                exc=loc(ast.Call(
                    func=loc(ast.Name(id="ValueError", ctx=ast.Load())),
                    args=[loc(ast.Constant(value=message))],
                    keywords=[],
                )),
                cause=None,
            ))],
            orelse=[],
        ))
```

`ValueError` is emitted rather than `ImpureOffering` because the generated
module imports nothing from Liturgy. `ImpureOffering` is the Liturgy spelling
of the same class, so `curse ImpureOffering` catches it.

- [ ] **Step 6: Enforce the position rule**

An augury is only valid as a rite's opening statement, after an optional
docstring. Add to `ConstructPass._scope`, before `generic_visit`:

```python
        _reject_misplaced_auguries(node, self._heresy)
```

and at module level:

```python
def _is_augur_carrier(stmt) -> bool:
    return isinstance(stmt, ast.With) and _carrier_call(stmt, "__augur__") is not None


def _is_docstring(stmt) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def _reject_misplaced_auguries(scope, mkerr) -> None:
    """An augury is a precondition, so it opens a rite or it is nothing."""
    in_rite = isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef))
    allowed = set()
    if in_rite:
        body = scope.body
        j = 1 if body and _is_docstring(body[0]) else 0
        while j < len(body) and _is_augur_carrier(body[j]):
            allowed.add(id(body[j]))
            j += 1

    def walk(node):
        # NOT ast.walk: it flattens the tree, so `continue` on a nested rite
        # skips that node but still yields its children -- and the nested
        # rite's own legitimate opening augury would be rejected here instead
        # of being allowed by its own scope visit.
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node is not scope
        ):
            return
        if _is_augur_carrier(node) and id(node) not in allowed:
            if not in_rite:
                raise mkerr(node, "an augury belongs at the opening of a rite")
            raise mkerr(node, "an augury must be the opening of its rite")
        for child in ast.iter_child_nodes(node):
            walk(child)

    walk(scope)
```

- [ ] **Step 7: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/liturgy/constructs.py src/liturgy/rewrite.py src/liturgy/compiler.py tests/test_augur.py
git commit -m "feat(constructs): augur, preconditions that survive -O"
```

---

### Task 7: Corpus sweep and node positions

**Files:**
- Modify: `tests/test_roundtrip.py` (extend the skip set)
- Test: `tests/test_positions.py` (create)

**Interfaces:**
- Consumes: `liturgy.lexicon.RESERVED`, `liturgy.compiler.compile_litany`.
- Produces: nothing importable.

Two backstops. The corpus sweep is what caught the Critical in Spec I's final review, and it must now know about five new reserved words. The position assertion is what keeps synthesised nodes from producing tracebacks with no line.

- [ ] **Step 1: Write the failing position test**

```python
# tests/test_positions.py
import ast

import pytest

from liturgy.compiler import _rewritten_tree

SOURCES = {
    "consecrated": "consecrated PORT = 8080\n",
    "litany": "litany(thrice, resting=1, curse=MotiveFailure):\n    abide\n",
    "augur": "rite f(x):\n    augur:\n        x > 0\n    render x\n",
    "nested": (
        "rite f(x):\n"
        "    augur:\n"
        "        x > 0\n"
        "    litany(twice, curse=MotiveFailure):\n"
        "        consecrated INNER = x\n"
        "        render INNER\n"
    ),
}


@pytest.mark.parametrize("name", sorted(SOURCES))
def test_every_node_in_the_rewritten_tree_has_a_position(name):
    tree = _rewritten_tree(SOURCES[name], "prayer.lit")
    missing = [
        f"{type(n).__name__}"
        for n in ast.walk(tree)
        if isinstance(n, (ast.stmt, ast.expr))
        and getattr(n, "lineno", None) is None
    ]
    assert not missing, f"nodes without a position: {missing}"


@pytest.mark.parametrize("name", sorted(SOURCES))
def test_no_synthesised_node_claims_a_line_beyond_the_source(name):
    src = SOURCES[name]
    limit = src.count("\n")
    tree = _rewritten_tree(src, "prayer.lit")
    beyond = [
        (type(n).__name__, n.lineno)
        for n in ast.walk(tree)
        if isinstance(n, (ast.stmt, ast.expr))
        and getattr(n, "lineno", 0) > limit
    ]
    assert not beyond, f"nodes past the end of the source: {beyond}"
```

- [ ] **Step 2: Expose `_rewritten_tree` in `src/liturgy/compiler.py`**

Split the tree-building out of `compile_litany` so the test can inspect it
without compiling:

```python
def _rewritten_tree(src: str, filename: str, *, mode: str = "exec") -> ast.AST:
    py, smap = transform(src, _PASSES, filename=filename)
    tree = ast.parse(py, filename, mode)
    tree = ConstructPass(filename, split_lines(src), smap).visit(tree)
    ast.fix_missing_locations(tree)
    return tree


def compile_litany(src, filename, *, mode="exec", dont_inherit=True, optimize=-1):
    tree = _rewritten_tree(src, filename, mode=mode)
    return compile(
        tree, filename, mode, dont_inherit=dont_inherit, optimize=optimize
    )
```

Keep `compile_litany`'s docstring on `compile_litany`.

- [ ] **Step 3: Run the position tests**

Run: `.venv/bin/pytest tests/test_positions.py -v`
Expected: PASS. If a node has no position, `ast.fix_missing_locations` is
papering over a missing `copy_location` — find it rather than relying on the
fixup, because `fix_missing_locations` copies from the *parent*, which can put a
node on a plausible but wrong line.

- [ ] **Step 4: Extend the corpus sweep's skip set**

In `tests/test_roundtrip.py`, the sweep skips files whose source uses a Liturgy
word as an identifier. It currently derives that set from `LEXICON`. Change it
to `RESERVED`, so the five new words are covered:

```python
from liturgy.lexicon import RESERVED
```

and replace the membership test against the old set with one against
`RESERVED`. Then add an assertion that the new words are actually in play:

```python
def test_the_sweep_skips_on_the_full_reserved_set():
    from liturgy.lexicon import RESERVED

    assert {"litany", "augur", "consecrated", "thrice", "twice"} <= RESERVED
```

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all pass. The sweep should report a slightly higher skip count than
before, since `litany`/`augur`/`consecrated` appear as identifiers in some
stdlib modules.

- [ ] **Step 6: Commit**

```bash
git add src/liturgy/compiler.py tests/test_positions.py tests/test_roundtrip.py
git commit -m "test: node positions and the corpus sweep on the full reserved set"
```

---

### Task 8: Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/LIBER-LITURGIAE.md`
- Modify: `docs/liber-liturgiae.html`
- Modify: `examples/` (create `examples/constructs.lit`)
- Test: `tests/test_examples.py`

**Interfaces:**
- Consumes: the finished constructs.
- Produces: nothing importable.

Both copies of the tome, since it ships in two, and the Markdown is canonical.

- [ ] **Step 1: Write the failing example test**

```python
# append to tests/test_examples.py
def test_constructs_example_runs():
    out = subprocess.run(
        [sys.executable, "-m", "liturgy", "chant",
         str(EXAMPLES / "constructs.lit")],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    assert "the omens forbid it" in out.stdout
    assert "attempts: 3" in out.stdout
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_examples.py -v`
Expected: FAIL — `examples/constructs.lit` does not exist.

- [ ] **Step 3: Write `examples/constructs.lit`**

```
## The Three Constructs
## Chanted to demonstrate what Python cannot say.

consecrated MAX_ATTEMPTS = 3


rite divide(a, b):
    augur:
        b be nay Void
        b != 0
    render a / b


rite flaky(attempts):
    attempts.append(1)
    proclaim MotiveFailure("the spirit is silent")


rite main():
    intone(f"++ 6 / 2 is {divide(6, 2)} ++")

    attempt:
        divide(1, 0)
    curse ImpureOffering styled omen:
        intone(f"++ {omen} ++")

    seen = []
    attempt:
        litany(MAX_ATTEMPTS, resting=0, curse=MotiveFailure):
            flaky(seen)
    curse MotiveFailure:
        intone(f"++ attempts: {measure(seen)} ++")


should __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run it and confirm the output**

Run: `.venv/bin/liturgy chant examples/constructs.lit`
Expected: three lines — the division, the themed omen message, and
`++ attempts: 3 ++`. Paste the real output into the commit message.

- [ ] **Step 5: Update `README.md`**

In the "not yet built" section, remove `consecrated`, `litany` and `augur`, and
say that `noospheric` was cut with a one-line reason. Add a short section
introducing the three constructs with the example above. Update the reserved
count from 58 to 63 wherever it appears, and add `thrice`/`twice` to the
builtin-alias table.

- [ ] **Step 6: Update `docs/LIBER-LITURGIAE.md`**

- Chapter III gains a **Numeral words** table: `twice` -> `2`, `thrice` -> `3`.
- A new **Chapter X — The Greater Rites** covers the three constructs, each with
  its syntax, its semantics, and what it rejects. Keep the house style: voice in
  the chapter opening and section headers, plain technical body.
- Chapter VII's count goes 58 -> 63, and gains a paragraph on the
  `consecrated` enforcement limitation, in the spec's own words: what the
  compiler cannot see, it cannot stop — `setattr`, `globals()`, assignment
  through the module object, and `exec` all get through. This is enforcement,
  not a guarantee.
- Chapter IX loses `consecrated`, `litany` and `augur`, and records that
  `noospheric` was cut rather than deferred.
- The Appendix gains the numerals.

- [ ] **Step 7: Mirror every change into `docs/liber-liturgiae.html`**

Same content, same structure. Add Chapter X to the rail's `<ol>`.

**Read the file first — a peer session restyled it after this plan was written.**
It is now a "cogitator terminal" treatment with its own conventions documented in
`docs/STYLE-COGITATOR.md`, and alias rows use `<td class="lit">` / `<td class="py">`
rather than `<code>` tags. Follow whatever patterns the file actually uses now and
add no new CSS. Do not restore the older styling.

- [ ] **Step 8: Validate the tables programmatically**

Run this and fix anything it reports — the same check that caught a wrong
reserved count when the tome was first written:

```bash
.venv/bin/python - <<'CHECK'
import re, pathlib
from liturgy.lexicon import LEXICON, RESERVED

for path, pattern in [
    ("docs/LIBER-LITURGIAE.md", r"\|\s*`([A-Za-z_]+)`\s*\|\s*`([A-Za-z_0-9]+)`\s*\|"),
    # A peer session restyled this page; alias rows now use class attributes
    # rather than <code> tags. Verified: 116 rows, zero mismatches.
    ("docs/liber-liturgiae.html",
     r'<td class="lit">([A-Za-z_]+)</td>\s*<td class="py">([A-Za-z_0-9]+)</td>'),
]:
    doc = pathlib.Path(path).read_text()
    pairs = re.findall(pattern, doc)
    wrong = [(l, p, LEXICON.get(l)) for l, p in pairs if LEXICON.get(l) != p]
    missing = sorted(set(LEXICON) - {l for l, _ in pairs})
    print(f"{path}: mismatches={wrong or 'none'} untabled={missing or 'none'}")
    assert not wrong and not missing
print("reserved count:", len(RESERVED))
CHECK
```

- [ ] **Step 9: Run the full suite and commit**

Run: `.venv/bin/pytest -q`

```bash
git add README.md docs examples tests/test_examples.py
git commit -m "docs: the three constructs, in the README and both copies of the tome"
```
