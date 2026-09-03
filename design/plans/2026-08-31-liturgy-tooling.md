# Liturgy Tooling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three CLI verbs (`augur` (lint), `transcribe` (Python → Liturgy), `purge` (clear caches)) so Liturgy is usable on code you did not write in it, and so the one class of mistake the compiler cannot catch is catchable.

**Architecture:** Both real verbs rest on one primitive, `find_collisions`, which reuses `rewrite._stored_names` for binding analysis and the alias pass's own `Substitution` list for positions. The reverse pass is promoted out of the test tree and becomes `transcribe`'s engine.

**Tech Stack:** Python 3.12+, stdlib only. pytest.

**Spec:** `design/specs/2026-08-31-liturgy-tooling-design.md`

## Global Constraints

- **Minimum Python 3.12**, standard library only, no runtime dependencies.
- **All 559 existing tests must pass.** Promoting `tests/_reverse.py` moves a module the round-trip suite imports; that import must be repointed, not duplicated.
- **`augur` does not become a general linter.** It checks exactly two things: the file compiles, and the reservation rule. Unused imports and the rest are ruff's job.
- **One definition of "collision".** `augur` and `transcribe` both call `find_collisions`; neither reimplements it.
- Module order gains: `collisions` and `reverse` above `rewrite`/`transform`; `tooling` above both, below `cli`.

## Verified before this plan was written

The collision algorithm below was prototyped against fourteen shapes and is known to work. Two things that look reasonable and are **wrong**, both found by that prototype:

- **Do not read the word at the AST node's column.** `_stored_names` yields the *statement* node for `for`, `def`, `class`, `except ... as` and imports, so that column is the statement's start. A prototype doing this produced five false negatives.
- **Do not treat `within jinja2 invoke render` as exempt.** It binds `render`, and every later reference substitutes to `return`. It is a collision. Spec I's exemption stops the *substitution* firing on the import target; it does not make the resulting program work.

## File Structure

| File | Responsibility |
|---|---|
| `src/liturgy/collisions.py` (create) | `Collision`, `find_collisions`. The one definition. |
| `src/liturgy/reverse.py` (create) | `to_liturgy`, moved from `tests/_reverse.py`. |
| `src/liturgy/tooling.py` (create) | `augur`, `transcribe`, `purge`: thin over the two above. |
| `src/liturgy/cli.py` (modify) | Three verbs move from `RESERVED_VERBS` into real subparsers. |
| `tests/_reverse.py` (delete) | Superseded by `src/liturgy/reverse.py`. |
| `tests/test_roundtrip.py` (modify) | Import from the shipped module. |

---

### Task 1: The collision primitive

**Files:**
- Create: `src/liturgy/collisions.py`
- Test: `tests/test_collisions.py`

**Interfaces:**
- Consumes: `liturgy.lexicon.LEXICON`; `liturgy.rewrite._stored_names`; `liturgy.transform.alias_pass`, `transform`, `split_lines`, `UnfinishedLitany`.
- Produces: `Collision(line: int, col: int, word: str, target: str, quiet: bool)` (frozen dataclass); `find_collisions(src: str, filename: str, *, liturgy: bool) -> list[Collision]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_collisions.py
import pytest

from liturgy.collisions import Collision, find_collisions


def words(src, *, liturgy=True):
    return sorted(
        (c.line, c.word, c.target)
        for c in find_collisions(src, "p.lit" if liturgy else "p.py", liturgy=liturgy)
    )


# --- clause (a): a substitution landed on a binding ---
def test_a_quiet_assignment_collides():
    assert words('span = "text range"\n') == [(1, "span", "range")]


def test_a_for_target_collides():
    assert words("foreach span among [1]:\n    abide\n") == [(1, "span", "range")]


def test_a_with_as_target_collides():
    src = "anointed unseal('f') styled measure:\n    abide\n"
    assert words(src) == [(1, "measure", "len")]


def test_a_rite_name_collides():
    assert words("rite span():\n    abide\n") == [(1, "span", "range")]


def test_a_pattern_name_collides():
    assert words("pattern measure:\n    abide\n") == [(1, "measure", "len")]


def test_an_except_as_target_collides():
    src = "attempt:\n    abide\ncurse MachineCurse styled measure:\n    abide\n"
    assert words(src) == [(3, "measure", "len")]


def test_a_walrus_target_collides():
    assert words("should (span := 1):\n    abide\n") == [(1, "span", "range")]


def test_an_unpacked_target_collides():
    assert words("span, other = 1, 2\n") == [(1, "span", "range")]


def test_a_curse_name_collides_and_is_quiet():
    # MachineCurse -> Exception is a name, not a keyword: it compiles and shadows.
    found = find_collisions("MachineCurse = 5\n", "p.lit", liturgy=True)
    assert [(c.word, c.target, c.quiet) for c in found] == [
        ("MachineCurse", "Exception", True)
    ]


# --- clause (b): the binding survived unsubstituted ---
def test_an_import_alias_collides():
    # Rule 3 protects the target from substitution, so the binding stays
    # `span` -- but every later reference to it becomes `range`.
    assert words("invoke os styled span\n") == [(1, "span", "range")]


def test_an_import_target_collides():
    assert words("within jinja2 invoke render\n") == [(1, "render", "return")]


# --- bindings _stored_names does not report, which collisions still needs ---
def test_a_parameter_name_collides():
    # def f(span) becomes def f(range).
    assert words("rite f(span):\n    render span\n") == [(1, "span", "range")]


def test_a_comprehension_target_collides():
    # [p for p in xs] with p == `pattern` becomes `class`, a syntax error.
    assert words("x = [pattern foreach pattern among xs]\n") == [
        (1, "pattern", "class")
    ]


def test_a_universal_declaration_collides():
    src = "rite f():\n    universal span\n    span = 1\n"
    assert (2, "span", "range") in words(src)


# --- NAMED REGRESSIONS: these bind nothing and must never be reported ---
def test_attribute_access_is_not_a_collision():
    assert words("template.render()\n") == []


def test_a_keyword_argument_is_not_a_collision():
    assert words("f(intone=1)\n") == []


def test_correct_use_of_a_reserved_word_is_not_a_collision():
    assert words("intone(measure([1, 2]))\n") == []


# --- positions ---
def test_clause_a_reports_the_words_own_column():
    (c,) = find_collisions("foreach span among [1]:\n    abide\n", "p.lit", liturgy=True)
    assert (c.line, c.col) == (1, 8)


# --- .py files: clause (b) only ---
def test_python_bindings_of_liturgy_words_collide():
    src = "span = 5\ndef render(): pass\nx = 1\n"
    assert words(src, liturgy=False) == [(1, "span", "range"), (2, "render", "return")]


def test_clean_python_has_no_collisions():
    assert words("x = 1\nimport os\n", liturgy=False) == []


# --- failure modes ---
def test_source_that_does_not_tokenise_raises():
    # The caller decides what to do; there is no map to scan against.
    from liturgy.transform import UnfinishedLitany

    with pytest.raises(UnfinishedLitany):
        find_collisions("x = (1, 2\n", "p.lit", liturgy=True)


def test_loud_collisions_surface_as_syntax_errors():
    # `render = 1` becomes `return = 1`. There is no tree to walk.
    with pytest.raises(SyntaxError):
        find_collisions("render = 1\n", "p.lit", liturgy=True)
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_collisions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'liturgy.collisions'`

- [ ] **Step 3: Create `src/liturgy/collisions.py`**

```python
"""Reserved words used as identifiers.

`augur` reports them; `transcribe` refuses on them. One definition, so the
two verbs cannot drift apart about what counts.
"""

from __future__ import annotations

import ast
import io
import keyword
import tokenize
from dataclasses import dataclass

from .lexicon import LEXICON
from .rewrite import _names_in_target, _stored_names
from .transform import alias_pass, split_lines, transform


@dataclass(frozen=True, slots=True)
class Collision:
    """A binding whose source-language name is reserved.

    `col` is 0-based. `quiet` means the substitution target is not a Python
    keyword, so the file compiles and silently shadows -- which is the whole
    reason this check exists.
    """

    line: int
    col: int
    word: str
    target: str
    quiet: bool


def _is_quiet(target: str) -> bool:
    return not keyword.iskeyword(target)


def _bindings(node):
    """Every binding, including three `_stored_names` does not report.

    `_stored_names` exists for Spec II's `consecrated` check, where a
    parameter and a comprehension target are correctly *not* rebindings --
    each opens its own scope. For collisions they matter, because the
    substitution does not care about scope:

        def f(span):        ->  def f(range):
        [p for p in xs]     ->  [p for p in xs]  with p == `pattern`
                                -> `class`, a syntax error

    Measured against the stdlib corpus, adding these three took the
    disagreement with the round-trip sweep's own predicate from 28 files to
    2 -- and both survivors are the sweep being wrong, not this.

    Extending `_stored_names` itself was rejected: it would change what
    Spec II's `consecrated` rejects, for no benefit there.
    """
    yield from _stored_names(node)
    if isinstance(node, ast.arg):
        yield node.arg, node
    elif isinstance(node, ast.comprehension):
        yield from ((n.id, n) for n in _names_in_target(node.target))
    elif isinstance(node, (ast.Global, ast.Nonlocal)):
        yield from ((name, node) for name in node.names)


def find_collisions(
    src: str, filename: str, *, liturgy: bool
) -> list[Collision]:
    """Every binding in `src` whose name is a reserved Liturgy word.

    Two clauses, because a binding can collide two ways:

    (a) A substitution produced the bound name -- the author wrote `span` and
        it became `range`. Position comes from the `Substitution` itself,
        which is already in Liturgy coordinates and exact.
    (b) The bound name is itself a Liturgy word, surviving unsubstituted
        because an exemption protected it -- `invoke os styled span` binds
        `span`, and every later reference to it becomes `range`. Position
        falls back to the AST node, whose column is the statement's start for
        `for`/`def`/`class`/`except`/`import`. Line is exact regardless.

    Clause (b) alone is the whole rule for a `.py` file, which has no
    substitutions.

    Raises:
        UnfinishedLitany: `src` ends mid-bracket or mid-string.
        SyntaxError: `src` does not parse. A loud collision -- `render = 1`
            becoming `return = 1` -- arrives this way, and the caller reports
            it as a compile failure rather than a collision.
    """
    if liturgy:
        py, _smap = transform(src, filename=filename)
        tree = ast.parse(py, filename)
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
        subs = {(s.row, s.text): s for s in alias_pass(toks)}
    else:
        tree = ast.parse(src, filename)
        subs = {}

    lines = split_lines(src)
    found: set[Collision] = set()

    for node in ast.walk(tree):
        for name, at in _bindings(node):
            line = getattr(at, "lineno", 0)
            sub = subs.get((line, name))
            if sub is not None:
                word = lines[line - 1][sub.col_start : sub.col_end]
                col = sub.col_start
            elif name in LEXICON:
                word = name
                col = getattr(at, "col_offset", 0) or 0
            else:
                continue
            found.add(
                Collision(line, col, word, LEXICON[word], _is_quiet(LEXICON[word]))
            )

    return sorted(found, key=lambda c: (c.line, c.col, c.word))
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all pass, 18 new.

- [ ] **Step 5: Commit**

```bash
git add src/liturgy/collisions.py tests/test_collisions.py
git commit -m "feat(collisions): one definition of a reserved word used as an identifier"
```

---

### Task 2: Promote the reverse pass

**Files:**
- Create: `src/liturgy/reverse.py`
- Delete: `tests/_reverse.py`
- Modify: `tests/test_roundtrip.py` (the import)
- Test: `tests/test_reverse.py`

**Interfaces:**
- Consumes: `liturgy.lexicon.INVERSE`; `liturgy.transform`.
- Produces: `liturgy.reverse.to_liturgy(src: str) -> str`.

Spec II deliberately moved this **out** of the shipped wheel because it was test-only. Under Spec III it becomes the feature, so it moves back, and the round-trip property test then exercises shipped code rather than a private twin.

- [ ] **Step 1: Move the file and repoint the import**

```bash
git mv tests/_reverse.py src/liturgy/reverse.py
```

In `src/liturgy/reverse.py`, change the module docstring's first line from the test-only framing to:

```python
"""Python to Liturgy, the reverse of the alias pass.

The engine behind `transcribe`. It shares `transform`'s traversal, so the
three context rules -- attribute position, keyword-argument position, import
statements -- apply identically in both directions.
"""
```

In `tests/test_roundtrip.py`, change `from tests._reverse import to_liturgy` (or `from _reverse import ...`, whichever is present) to:

```python
from liturgy.reverse import to_liturgy
```

- [ ] **Step 2: Run the full suite to confirm the move is clean**

Run: `.venv/bin/pytest -q`
Expected: all pass, unchanged count. A failure here means the import was repointed wrongly, not that the move was.

- [ ] **Step 3: Write tests for it as shipped code**

```python
# tests/test_reverse.py
from liturgy.reverse import to_liturgy
from liturgy.transform import transform


def test_keywords_are_reversed():
    assert to_liturgy("def f():\n    return 1\n") == "rite f():\n    render 1\n"


def test_builtins_are_reversed():
    assert to_liturgy("print(len(x))\n") == "intone(measure(x))\n"


def test_attribute_names_are_left_alone():
    # The same exemption as the forward direction: obj.return is not a thing,
    # and obj.render is somebody's method.
    assert to_liturgy("template.render()\n") == "template.render()\n"


def test_keyword_arguments_are_left_alone():
    assert to_liturgy("f(print=1)\n") == "f(print=1)\n"


def test_import_targets_are_left_alone():
    assert to_liturgy("from jinja2 import render\n") == "within jinja2 invoke render\n"


def test_the_line_count_is_preserved():
    src = "def f():\n    if x:\n        return 1\n    return 2\n"
    assert to_liturgy(src).count("\n") == src.count("\n")


def test_it_round_trips_through_transform():
    src = "class C:\n    def m(self):\n        return [i for i in range(3)]\n"
    assert transform(to_liturgy(src))[0] == src
```

- [ ] **Step 4: Run to verify, then commit**

Run: `.venv/bin/pytest -q`

```bash
git add src/liturgy/reverse.py tests/test_reverse.py tests/test_roundtrip.py
git commit -m "refactor(reverse): promote the reverse pass out of the test tree"
```

---

### Task 3: augur

**Files:**
- Create: `src/liturgy/tooling.py`
- Modify: `src/liturgy/cli.py`
- Test: `tests/test_augur_verb.py`

**Interfaces:**
- Consumes: `find_collisions`; `liturgy.compiler.compile_litany`; `liturgy.transform.UnfinishedLitany`.
- Produces: `liturgy.tooling.augur(paths: list[str], *, plain: bool = False, out=None) -> int`.

Named `test_augur_verb.py`, not `test_augur.py`; that file already exists for the Spec II construct, and the two are different things.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_augur_verb.py
import io

import pytest

from liturgy.tooling import augur


def run(tmp_path, name, src, *, plain=False):
    p = tmp_path / name
    p.write_text(src)
    buf = io.StringIO()
    code = augur([str(p)], plain=plain, out=buf)
    return code, buf.getvalue()


def test_a_clean_litany_passes(tmp_path):
    code, out = run(tmp_path, "clean.lit", "intone(measure([1, 2]))\n")
    assert code == 0
    assert "troubled" not in out


def test_a_quiet_collision_is_reported(tmp_path):
    code, out = run(tmp_path, "quiet.lit", 'span = "text range"\n')
    assert code == 1
    assert "span" in out and "range" in out


def test_plain_output_is_machine_readable(tmp_path):
    code, out = run(tmp_path, "quiet.lit", 'span = "text range"\n', plain=True)
    assert code == 1
    assert out.strip().startswith(str(tmp_path / "quiet.lit") + ":1:1:")


def test_plain_columns_are_one_based(tmp_path):
    # Collision.col is 0-based; editors and CI expect 1-based.
    _, out = run(tmp_path, "q.lit", "foreach span among [1]:\n    abide\n", plain=True)
    assert ":1:9:" in out


def test_a_litany_that_does_not_compile_reports_the_failure(tmp_path):
    code, out = run(tmp_path, "bad.lit", "rite f(:\n")
    assert code == 1
    assert "SyntaxError" in out or "ill-written" in out


def test_a_litany_that_does_not_tokenise_says_the_omens_are_unread(tmp_path):
    # No SourceMap means nothing to scan; reporting "clean" would lie.
    code, out = run(tmp_path, "unfinished.lit", "x = (1, 2\n")
    assert code == 1
    assert "omens unread" in out


def test_a_python_file_is_scanned_for_transcribability(tmp_path):
    code, out = run(tmp_path, "legacy.py", "span = 5\n")
    assert code == 1
    assert "span" in out


def test_a_clean_python_file_passes(tmp_path):
    code, out = run(tmp_path, "fine.py", "x = 1\nimport os\n")
    assert code == 0


def test_a_directory_is_walked(tmp_path):
    (tmp_path / "a.lit").write_text("intone(1)\n")
    (tmp_path / "b.lit").write_text("span = 5\n")
    (tmp_path / "notes.txt").write_text("span = 5\n")  # not ours
    buf = io.StringIO()
    assert augur([str(tmp_path)], out=buf) == 1
    assert "b.lit" in buf.getvalue() and "notes.txt" not in buf.getvalue()


def test_a_missing_path_is_an_error_not_a_pass(tmp_path):
    buf = io.StringIO()
    assert augur([str(tmp_path / "nope.lit")], out=buf) == 1
    assert "nope.lit" in buf.getvalue()
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_augur_verb.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'liturgy.tooling'`

- [ ] **Step 3: Create `src/liturgy/tooling.py` with `augur`**

```python
"""The Spec III verbs: augur, transcribe, purge."""

from __future__ import annotations

import pathlib
import sys

from .collisions import find_collisions
from .compiler import compile_litany
from .transform import UnfinishedLitany, split_lines

_SOURCES = (".lit", ".py")


def _gather(paths: list[str]) -> list[pathlib.Path]:
    """Files to read, expanding directories to the sources we understand."""
    out: list[pathlib.Path] = []
    for raw in paths:
        p = pathlib.Path(raw)
        if p.is_dir():
            out.extend(
                sorted(f for f in p.rglob("*") if f.suffix in _SOURCES and f.is_file())
            )
        else:
            out.append(p)
    return out


def _report(path, line, src_line, col, width, message, *, out) -> None:
    print("++ THE OMENS ARE TROUBLED ++", file=out)
    print(f"   {path}, line {line}", file=out)
    if src_line:
        print(f"       {src_line}", file=out)
        print(f"       {' ' * col}{'^' * max(width, 1)}", file=out)
    print(f"   {message}", file=out)


def augur(paths: list[str], *, plain: bool = False, out=None) -> int:
    """Read litanies for faults without chanting them. 0 clean, 1 findings."""
    out = out if out is not None else sys.stdout
    troubled = False

    for path in _gather(paths):
        try:
            src = path.read_text(encoding="utf-8")
        except OSError as err:
            troubled = True
            _emit_bare(path, f"cannot be read: {err.strerror}", plain=plain, out=out)
            continue

        liturgy = path.suffix == ".lit"
        try:
            collisions = find_collisions(src, str(path), liturgy=liturgy)
        except UnfinishedLitany:
            troubled = True
            _emit_bare(
                path, "omens unread: the litany does not tokenise",
                plain=plain, out=out,
            )
            continue
        except SyntaxError as err:
            troubled = True
            _emit_bare(
                path, f"{type(err).__name__}: {err.msg}",
                line=err.lineno or 1, plain=plain, out=out,
            )
            continue

        if liturgy:
            # Compiling is what makes augur agree with chant. Collisions are
            # already in hand, so a failure here is something else entirely.
            try:
                compile_litany(src, str(path))
            except SyntaxError as err:
                troubled = True
                _emit_bare(
                    path, f"{type(err).__name__}: {err.msg}",
                    line=err.lineno or 1, plain=plain, out=out,
                )

        lines = split_lines(src)
        for c in collisions:
            troubled = True
            note = f"{c.word} is reserved; it becomes {c.target}"
            if c.quiet:
                note += " -- silently"
            if plain:
                print(f"{path}:{c.line}:{c.col + 1}: {note}", file=out)
            else:
                text = lines[c.line - 1].rstrip("\n") if c.line <= len(lines) else ""
                _report(path, c.line, text, c.col, len(c.word), note, out=out)

    return 1 if troubled else 0


def _emit_bare(path, message, *, line: int = 1, plain: bool, out) -> None:
    if plain:
        print(f"{path}:{line}:1: {message}", file=out)
    else:
        _report(path, line, "", 0, 0, message, out=out)
```

- [ ] **Step 4: Wire the verb in `src/liturgy/cli.py`**

Remove `"augur"` from `RESERVED_VERBS`, add a subparser beside `chant`:

```python
    p_augur = verbs.add_parser("augur", help="read a litany for faults")
    p_augur.add_argument("paths", nargs="+")
    p_augur.add_argument(
        "--plain", action="store_true",
        help="emit file:line:col: messages for editors and CI",
    )
```

and dispatch it in `main`, beside the `chant` branch:

```python
    if args.verb == "augur":
        from .tooling import augur

        return augur(args.paths, plain=args.plain)
```

The import is local, matching how `commune` is already dispatched: it keeps `cli` importable without pulling in the tooling modules.

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/liturgy/tooling.py src/liturgy/cli.py tests/test_augur_verb.py
git commit -m "feat(augur): read a litany for faults without chanting it"
```

---

### Task 4: transcribe

**Files:**
- Modify: `src/liturgy/tooling.py` (add `transcribe`)
- Modify: `src/liturgy/cli.py`
- Test: `tests/test_transcribe.py`

**Interfaces:**
- Consumes: `find_collisions`; `liturgy.reverse.to_liturgy`; `liturgy.transform.transform`.
- Produces: `liturgy.tooling.transcribe(source: str, dest: str | None = None, *, out=None) -> int`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_transcribe.py
import io

import pytest

from liturgy.tooling import transcribe


def run(tmp_path, src, *, name="legacy.py", dest=None):
    p = tmp_path / name
    p.write_text(src)
    buf = io.StringIO()
    code = transcribe(str(p), dest, out=buf)
    return code, buf.getvalue()


def test_a_clean_file_is_transcribed_to_stdout(tmp_path):
    code, out = run(tmp_path, "def f():\n    return 1\n")
    assert code == 0
    assert "rite f():" in out and "render 1" in out


def test_it_writes_to_a_destination_when_given_one(tmp_path):
    dest = tmp_path / "out.lit"
    code, out = run(tmp_path, "print(len(x))\n", dest=str(dest))
    assert code == 0
    assert dest.read_text() == "intone(measure(x))\n"
    assert "transcribed" in out


def test_a_collision_refuses_the_whole_file(tmp_path):
    code, out = run(tmp_path, "span = 5\nprint(span)\n")
    assert code == 1
    assert "CANNOT TRANSCRIBE" in out
    # Nothing partial is emitted.
    assert "intone" not in out


def test_every_collision_is_listed_not_just_the_first(tmp_path):
    src = "span = 5\npattern = 6\ndef render(): pass\n"
    code, out = run(tmp_path, src)
    assert code == 1
    for word in ("span", "pattern", "render"):
        assert word in out


def test_a_refusal_names_lines(tmp_path):
    code, out = run(tmp_path, "x = 1\nspan = 5\n")
    assert code == 1
    assert ":2" in out or "line 2" in out


def test_nothing_is_written_when_it_refuses(tmp_path):
    dest = tmp_path / "out.lit"
    code, _ = run(tmp_path, "span = 5\n", dest=str(dest))
    assert code == 1
    assert not dest.exists()


def test_it_verifies_its_own_output_before_writing(tmp_path, monkeypatch):
    # A reverse pass that produces something not round-tripping must be
    # caught here rather than written to disk.
    import liturgy.tooling as tooling

    monkeypatch.setattr(tooling, "to_liturgy", lambda src: "intone('wrong')\n")
    dest = tmp_path / "out.lit"
    code, out = run(tmp_path, "print(1)\n", dest=str(dest))
    assert code == 1
    assert "does not round-trip" in out
    assert not dest.exists()


def test_a_missing_source_is_an_error(tmp_path):
    buf = io.StringIO()
    assert transcribe(str(tmp_path / "nope.py"), None, out=buf) == 1
    assert "nope.py" in buf.getvalue()


def test_a_syntactically_invalid_source_is_refused(tmp_path):
    code, out = run(tmp_path, "def f(:\n")
    assert code == 1
    assert "SyntaxError" in out
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_transcribe.py -v`
Expected: FAIL with `ImportError: cannot import name 'transcribe'`

- [ ] **Step 3: Add `transcribe` to `src/liturgy/tooling.py`**

Add `from .reverse import to_liturgy` and `from .transform import transform` to the imports. `to_liturgy` is imported by name at module level so the round-trip self-check test can monkeypatch it.

```python
def transcribe(source: str, dest: str | None = None, *, out=None) -> int:
    """Render a Python file into Liturgy. 0 written, 1 refused."""
    out = out if out is not None else sys.stdout
    path = pathlib.Path(source)

    try:
        src = path.read_text(encoding="utf-8")
    except OSError as err:
        print(f"++ CANNOT TRANSCRIBE: {path} {err.strerror} ++", file=out)
        return 1

    try:
        collisions = find_collisions(src, str(path), liturgy=False)
    except SyntaxError as err:
        print(
            f"++ CANNOT TRANSCRIBE: {type(err).__name__} at line {err.lineno} ++",
            file=out,
        )
        return 1

    if collisions:
        print(
            f"++ CANNOT TRANSCRIBE: {len(collisions)} "
            f"COLLISION{'S' if len(collisions) != 1 else ''} ++",
            file=out,
        )
        for c in collisions:
            print(
                f"  {path}:{c.line}  {c.word:<12} -> reserved ({c.target})",
                file=out,
            )
        print("rename these, then chant again", file=out)
        return 1

    litany = to_liturgy(src)

    # Verify before writing. This is the round-trip property test applied to
    # one real file: if the output does not transform back to the input, the
    # output is wrong and must not reach disk claiming otherwise.
    try:
        back, _ = transform(litany, filename=str(path))
    except SyntaxError:
        back = None
    if back != src:
        print("++ CANNOT TRANSCRIBE: the output does not round-trip ++", file=out)
        print("   this is a fault in Liturgy, not in your source", file=out)
        return 1

    if dest is None:
        print(litany, end="", file=out)
    else:
        pathlib.Path(dest).write_text(litany, encoding="utf-8")
        print(f"++ {len(split_lines(litany))} lines transcribed ++", file=out)
    return 0
```

- [ ] **Step 4: Wire the verb in `src/liturgy/cli.py`**

Remove `"transcribe"` from `RESERVED_VERBS`, add:

```python
    p_trans = verbs.add_parser("transcribe", help="render Python into Liturgy")
    p_trans.add_argument("source")
    p_trans.add_argument("-o", "--out", dest="dest", default=None)
```

and dispatch:

```python
    if args.verb == "transcribe":
        from .tooling import transcribe

        return transcribe(args.source, args.dest)
```

- [ ] **Step 5: Run the full suite, then commit**

Run: `.venv/bin/pytest -q`

```bash
git add src/liturgy/tooling.py src/liturgy/cli.py tests/test_transcribe.py
git commit -m "feat(transcribe): render Python into Liturgy, refusing on collisions"
```

---

### Task 5: purge

**Files:**
- Modify: `src/liturgy/tooling.py` (add `purge`)
- Modify: `src/liturgy/cli.py`
- Test: `tests/test_purge.py`

**Interfaces:**
- Consumes: `liturgy.heresy.state_path`.
- Produces: `liturgy.tooling.purge(*, heresies: bool = False, root: str | None = None, out=None) -> int`.

The only destructive verb. `root` exists so tests never delete anything outside `tmp_path`; the CLI leaves it `None`, meaning the working directory.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_purge.py
import io
import json

import pytest

from liturgy.tooling import purge


def test_it_removes_pycache_directories(tmp_path):
    (tmp_path / "prayer.lit").write_text("intone(1)\n")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "prayer.cpython-312.pyc").write_bytes(b"\x00")
    nested = tmp_path / "sub" / "__pycache__"
    nested.mkdir(parents=True)
    (nested / "x.pyc").write_bytes(b"\x00")

    buf = io.StringIO()
    assert purge(root=str(tmp_path), out=buf) == 0
    assert not cache.exists() and not nested.exists()
    assert "__pycache__" in buf.getvalue()


def test_it_refuses_outside_a_liturgy_project(tmp_path):
    # No .lit file anywhere: a recursive delete here is somebody's mistake.
    (tmp_path / "__pycache__").mkdir()
    buf = io.StringIO()
    assert purge(root=str(tmp_path), out=buf) == 1
    assert (tmp_path / "__pycache__").exists()
    assert "does not look like" in buf.getvalue()


def test_it_leaves_other_directories_alone(tmp_path):
    (tmp_path / "prayer.lit").write_text("intone(1)\n")
    keep = tmp_path / "src"
    keep.mkdir()
    (keep / "thing.py").write_text("x = 1\n")
    assert purge(root=str(tmp_path), out=io.StringIO()) == 0
    assert (keep / "thing.py").exists()


def test_it_does_not_follow_symlinks(tmp_path):
    # The symlink must be NAMED __pycache__: rglob matches on name, so a
    # link called anything else is never yielded and the guard under test
    # is never reached.
    project = tmp_path / "forge"
    project.mkdir()
    (project / "prayer.lit").write_text("intone(1)\n")
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "precious.pyc").write_bytes(b"\x00")
    try:
        (project / "__pycache__").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")

    assert purge(root=str(project), out=io.StringIO()) == 0
    assert (outside / "precious.pyc").exists(), "followed a symlink"
    assert (project / "__pycache__").is_symlink(), "removed the link itself"


def test_heresies_clears_the_state_file(tmp_path, monkeypatch):
    (tmp_path / "prayer.lit").write_text("intone(1)\n")
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    from liturgy import heresy

    state = heresy.state_path()
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({"run": 3}))

    buf = io.StringIO()
    assert purge(heresies=True, root=str(tmp_path), out=buf) == 0
    assert not state.exists()
    assert str(state) in buf.getvalue(), "the full path is reported before deletion"


def test_heresies_is_quiet_when_there_is_nothing_to_clear(tmp_path, monkeypatch):
    (tmp_path / "prayer.lit").write_text("intone(1)\n")
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    assert purge(heresies=True, root=str(tmp_path), out=io.StringIO()) == 0
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_purge.py -v`
Expected: FAIL with `ImportError: cannot import name 'purge'`

- [ ] **Step 3: Add `purge` to `src/liturgy/tooling.py`**

Add `import shutil` and `from .heresy import state_path` to the imports.

```python
def purge(
    *, heresies: bool = False, root: str | None = None, out=None
) -> int:
    """Clear generated caches. 0 done, 1 refused.

    The only destructive verb, so it is guarded: it refuses unless the tree
    holds at least one .lit file, because a recursive delete in the wrong
    directory is a bad afternoon. Symlinked directories are never entered --
    `rglob` does not follow them, and each candidate is checked anyway.
    """
    out = out if out is not None else sys.stdout
    base = pathlib.Path(root) if root is not None else pathlib.Path.cwd()

    if not any(base.rglob("*.lit")):
        print(f"++ {base} does not look like a Liturgy forge ++", file=out)
        print("   no .lit file found; refusing to delete anything", file=out)
        return 1

    removed = 0
    for cache in sorted(base.rglob("__pycache__")):
        if cache.is_symlink() or not cache.is_dir():
            continue
        print(f"   purged {cache}", file=out)
        shutil.rmtree(cache)
        removed += 1

    if heresies:
        state = state_path()
        if state.exists():
            print(f"   purged {state}", file=out)
            state.unlink()
            removed += 1

    print(f"++ {removed} relic{'' if removed == 1 else 's'} purged ++", file=out)
    return 0
```

- [ ] **Step 4: Wire the verb in `src/liturgy/cli.py`**

Remove `"purge"` from `RESERVED_VERBS`, add:

```python
    p_purge = verbs.add_parser("purge", help="clear generated caches")
    p_purge.add_argument(
        "--heresies", action="store_true", help="also clear the heresy record"
    )
```

and dispatch:

```python
    if args.verb == "purge":
        from .tooling import purge

        return purge(heresies=args.heresies)
```

`RESERVED_VERBS` now holds five names, not eight. Update `test_reserved_verbs_are_declared` in `tests/test_cli.py` so it asserts the five that remain (`prove`, `sanctify`, `forge`, `consecrate`, `anoint`) and that the three built ones are **no longer** in it.

- [ ] **Step 5: Run the full suite, then commit**

Run: `.venv/bin/pytest -q`

```bash
git add src/liturgy/tooling.py src/liturgy/cli.py tests/test_purge.py tests/test_cli.py
git commit -m "feat(purge): clear generated caches, guarded against the wrong directory"
```

---

### Task 6: The corpus cross-check

**Files:**
- Test: `tests/test_augur_corpus.py`

**Interfaces:**
- Consumes: `find_collisions`; the corpus discovery already in `tests/test_roundtrip.py`.
- Produces: nothing importable.

Two independent implementations of "this file uses a Liturgy word as an identifier" (the sweep's skip predicate and `find_collisions`) should agree.

`tests/` is not a package, and pytest puts each test file's directory on
`sys.path`, so the import is `from test_roundtrip import ...`. If that fails in
your environment, add a `tests/__init__.py` and use `from tests.test_roundtrip
import ...`, but check which works before assuming. The sweep is what caught the Critical that hand-written tests missed in Spec I; making a second implementation answer to it is cheap insurance on both.

- [ ] **Step 1: Write the test**

```python
# tests/test_augur_corpus.py
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
```

- [ ] **Step 2: Run it**

Run: `.venv/bin/pytest tests/test_augur_corpus.py -q -s`

**Expect exactly two disagreements, and expect the sweep to be the wrong one.**
This was measured before the plan shipped: with `_bindings` as written in Task 1,
623 corpus files were checked and 621 agreed. The two survivors are files where
the sweep skips and `find_collisions` correctly does not:

- **A Liturgy word in keyword-argument position**: `increment_count(thrice=3)`.
  Rule 2 exempts it, the file round-trips fine, and the sweep is over-skipping.
- The same shape again in the other file.

So the fix is to the **sweep**, not to `find_collisions`: narrow
`_liturgy_word_as_identifier` to skip a NAME immediately followed by `=` at
paren depth greater than zero, mirroring Rule 2 exactly as it already mirrors
Rule 1 for attribute position. That should take the corpus from 573 swept to
575, two files gained, not lost.

If you see a different count or a disagreement in the other direction
(`find_collisions` flagging where the sweep does not), **do not weaken the
assertion**: that is a new finding. Report the named files and what you
concluded before changing either predicate.

- [ ] **Step 3: Commit**

```bash
git add tests/test_augur_corpus.py
git commit -m "test: augur and the corpus sweep must agree about collisions"
```

---

### Task 7: Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/LIBER-LITURGIAE.md`
- Modify: `docs/liber-liturgiae.html`
- Modify: `docs/liturgy-data-slate.html`
- Modify: `docs/index.html`
- Test: `tests/test_examples.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_examples.py
def test_augur_catches_the_quiet_shadowing_the_docs_warn_about(tmp_path):
    # Chapter VII names `span = ...` as the quiet trap. This is the verb
    # that finds it, so the two must actually agree.
    p = tmp_path / "quiet.lit"
    p.write_text('span = "text range"\nintone(span)\n')
    out = subprocess.run(
        [sys.executable, "-m", "liturgy", "augur", "--plain", str(p)],
        capture_output=True, text=True,
    )
    assert out.returncode == 1
    assert "span is reserved" in out.stdout
```

- [ ] **Step 2: Run to verify it fails, then make it pass**

Run: `.venv/bin/pytest tests/test_examples.py -v`
Expected: FAIL until Task 3's verb is wired, then PASS.

- [ ] **Step 3: Update `README.md`**

Add a section for the three verbs after "Heresy". For `augur`, state plainly that it exists to catch the quiet shadowing the disclaimer and Chapter VII already warn about, and show the real output. Update "What's not built yet" so it names the five deferred verbs and says why each: `prove` because pytest already works on `.lit`, `sanctify` because a real formatter is its own project, and the other three because they were reserved as flavour with no feature behind them.

- [ ] **Step 4: Update both tome copies**

A new **Chapter XI: The Reading of Omens** covering the three verbs, in house style: voice in the chapter opening and section headers, plain technical body. It must say:

- `augur`'s two checks, and that it deliberately does not become a general linter.
- That an import bound to a reserved word is a collision, with the `within json invoke loads styled render` example and why; this is the subtle one and Chapter VI's exemptions do not cover it.
- `transcribe`'s refusal policy and its round-trip self-check.
- `purge`'s guard.

Chapter VII's "The quiet ones" gains a line pointing at `augur` as the answer, replacing the existing "until the `augur` rite exists to warn you"; it exists now.

Chapter IX loses the three built verbs and records why the five remaining are unbuilt.

- [ ] **Step 5: Update `docs/liturgy-data-slate.html` and `docs/index.html`**

The data-slate gains a verbs section in its existing `.. function::` style. The landing page's `[V] FURTHER READING` gains a line for the verbs, and `[I]` mentions that `augur` exists.

- [ ] **Step 6: Validate and run everything**

```bash
.venv/bin/python - <<'CHECK'
import re, pathlib
from liturgy.lexicon import LEXICON, RESERVED
for path, pattern in [
    ("docs/LIBER-LITURGIAE.md", r"\|\s*`([A-Za-z_]+)`\s*\|\s*`([A-Za-z_0-9]+)`\s*\|"),
    ("docs/liber-liturgiae.html",
     r'<td class="lit">([A-Za-z_]+)</td>\s*<td class="py">([A-Za-z_0-9]+)</td>'),
    ("docs/liturgy-data-slate.html",
     r'<td class="lit">([A-Za-z_]+)</td>\s*<td class="py">([A-Za-z_0-9]+)</td>'),
]:
    doc = pathlib.Path(path).read_text()
    pairs = re.findall(pattern, doc)
    wrong = [(l, p, LEXICON.get(l)) for l, p in pairs if LEXICON.get(l) != p]
    print(f"{path}: rows={len(pairs)} mismatches={wrong or 'none'}")
    assert not wrong
print("reserved:", len(RESERVED))
CHECK
```

Then run every command you documented and paste the real output into the commit message. Run `.venv/bin/pytest -q`.

- [ ] **Step 7: Commit**

```bash
git add README.md docs tests/test_examples.py
git commit -m "docs: the three tooling verbs, in the README and every page"
```
