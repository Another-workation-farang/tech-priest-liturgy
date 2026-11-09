# Liturgy Anoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `liturgy anoint hymn.lit` renders a litany tree as one native executable (Nuitka, single-file mode) that curses like `chant` and imports nothing from Liturgy.

**Architecture:** The curse renderer is split so its rendering half (`rubric.py`) imports nothing from Liturgy. `unction.py` renders every litany to Python with `ast.unparse`, builds a generated-line to litany-line map by walking the two trees in lockstep, mirrors the project into a staging directory, and bakes `__liturgy_curse.py` (rubric's source, verbatim, plus tables). `tooling.anoint` runs Nuitka on the staged entry and moves the executable into place.

**Tech Stack:** Python 3.12+, stdlib `ast`/`traceback`, Nuitka >= 4.3 (optional extra), pytest, GitHub Actions.

**Spec:** `design/specs/2026-11-07-liturgy-anoint-design.md`

## Global Constraints

- Nothing in the executable imports Liturgy. `rubric.py` imports only the standard library.
- Core `dependencies = []` stays. New extra: `anoint = ["nuitka>=4.3", "patchelf; sys_platform == 'linux'"]`.
- No `ast.walk` in `src/`. The lockstep walk recurses with `ast.iter_fields`.
- `transform` is untouched; line N of `chant`'s Python is still line N of the litany.
- Missing Nuitka refusal, exact text:
  ```
  ++ CANNOT ANOINT: nuitka is not installed ++
     anointing needs it:  pip install 'liturgy[anoint]'
  ```
- Every other refusal is one `++ CANNOT ANOINT: ... ++` line. Exit 0 anointed, 1 refused or failed.
- Nuitka's output is streamed, never captured. `--assume-yes-for-downloads` is never passed.
- Generated module name: `__liturgy_curse`. Paths in an executable's curses are relative to the entry litany's directory and `/`-separated.
- Executable carets: none. Multi-line statement: reported at its first line.
- Docs: no em dashes, no arrow glyphs (both retired from the tree).
- Suite green on Python 3.12 and 3.14. Test runner: `.venv/bin/pytest`.

**Setup (once, before Task 1):** the worktree has no venv. `uv venv -p 3.12 .venv && uv pip install -p .venv -e '.[trials,archetypes,highlight]' pytest`, and the same into `.venv314` with `-p 3.14` for the dual-version check. Task 5 adds `anoint` to both installs.

## Review Focus

1. **An entry litany named by a relative path from another directory** (`liturgy anoint codex/hymn.lit`): root and default output resolve against the litany, not the cwd. Test in Task 5.
2. **Re-anointing over an existing executable**: the old file is replaced, exit 0. Test in Task 5.
3. **A virtual environment or hidden directory inside the project** holding `.py` files and a broken `.lit`: neither staged nor fatal. Test in Task 4 (fixture's `venv/`).
4. **A litany with a UTF-8 BOM and non-ASCII on the faulting line**: the curse quotes the line without the BOM, characters intact. Test in Task 4 (fixture's `rites.lit`, `chain` omen).
5. **Two modules with the same stem in different packages** (`helpers/util.lit`, `other/util.lit`): the curse names the right one. Test in Task 4 (`twin` omen).

---

## File Structure

| File | Responsibility |
|---|---|
| `src/liturgy/rubric.py` (new) | Curse rendering with no Liturgy imports: `curse_name`, `render`, `install`, `TableSeer`. Copied verbatim into executables. A leaf, like `highlight`. |
| `src/liturgy/curse.py` | Keeps its public surface; supplies a live seer (recorded source, transform, column maps) and delegates rendering to `rubric`. |
| `src/liturgy/unction.py` (new) | Litany to Python text, line map, staging mirror, baked curse module. Imports `compiler`, `lexicon`, `transform`, `rubric`; sits after `compiler`. |
| `src/liturgy/tooling.py` | `anoint()` verb: refusals, temp dir, Nuitka subprocess, final move. |
| `src/liturgy/cli.py` | `anoint` subparser; `RESERVED_VERBS` removed. |
| `pyproject.toml` | `anoint` extra; `slow` pytest marker. |
| `tests/conftest.py` (new) | `codex` fixture project and curse-comparison helpers. |
| `tests/test_rubric.py`, `tests/test_unction.py`, `tests/test_anoint.py` (new) | Tests per module. |
| `tests/test_cli.py`, `tests/test_roundtrip.py` | Reserved-verb tests replaced; corpus sweep gains the unparse assertion. |
| `.github/workflows/anoint.yml` (new) | Three OS by two Python matrix for the anoint tests. |
| Five doc surfaces, `CLAUDE.md` | Task 7. |

---

### Task 1: Split the renderer out of `curse.py`

**Files:**
- Create: `src/liturgy/rubric.py`
- Modify: `src/liturgy/curse.py`
- Test: `tests/test_rubric.py`; `tests/test_curse.py` unchanged

**Interfaces:**
- Produces, in `rubric`:
  - `BANNER_OPEN`, `BANNER_CLOSE`, `CAUSE_SEPARATOR`, `CONTEXT_SEPARATOR` (moved verbatim; `curse` re-exports them).
  - `Placement = tuple[str, int, str, tuple[int, int] | None]`: path shown, line shown, source line (`""` if unknown), caret span `[start, end)` in character columns of that unstripped line, or `None`.
  - `class Seer(Protocol)`: `is_litany(filename: str) -> bool`; `is_plumbing(frame: traceback.FrameSummary) -> bool`; `place(frame: traceback.FrameSummary) -> Placement`; `place_syntax(exc: SyntaxError) -> Placement`.
  - `curse_name(exc_type: type, names: Mapping[str, str]) -> str` (today's logic, table passed in).
  - `syntax_span(exc: SyntaxError) -> tuple[int, int] | None`: today's unmapped offset to `[start, end)` arithmetic from `_render_syntax_location`.
  - `render(exc_type, exc, tb, *, seer: Seer, names: Mapping[str, str], file) -> None`: banner, chain, groups, launcher-frame dropping, as today. Never raises; on internal failure calls `sys.__excepthook__`. Calls `seer.place` only for frames where `seer.is_litany(frame.filename)`, and `seer.place_syntax` only when `seer.is_litany(exc.filename)`; non-litany frames and non-litany `SyntaxError`s render as today from `frame.line` / `exc.text` with `syntax_span`.
  - `install(seer: Seer, names: Mapping[str, str]) -> None`: sets `sys.excepthook` and `threading.excepthook` to closures over `render`.
- `curse` keeps every name tests touch: `curse_name(exc_type) -> str` (now `rubric.curse_name(exc_type, INVERSE)`), `render_curse(exc_type, exc, tb, *, file=None)`, `_thread_hook`, `install`, `uninstall`, `record_source`, `forget_source`, `_source_cache`, `_map_cache`, and the four constants. `install()` still assigns `render_curse` and `_thread_hook` themselves.

- [ ] **Step 1: Write the failing tests** in `tests/test_rubric.py`

```python
def test_rubric_imports_nothing_from_liturgy():
    tree = ast.parse(pathlib.Path(rubric.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):  # a test, not src/
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0 and not (node.module or "").startswith("liturgy")
        if isinstance(node, ast.Import):
            assert not any(a.name.startswith("liturgy") for a in node.names)

def test_unencodable_source_is_replaced_not_lost():
    class Seer:  # minimal litany seer
        def is_litany(self, f): return f == "x.lit"
        def is_plumbing(self, fr): return False
        def place(self, fr): return ("x.lit", 1, 'intone("⚙")', None)
        def place_syntax(self, e): raise AssertionError
    raw = io.BytesIO()
    file = io.TextIOWrapper(raw, encoding="cp1252")
    try:
        exec(compile("1/0", "x.lit", "exec"))
    except ZeroDivisionError as e:
        rubric.render(type(e), e, e.__traceback__, seer=Seer(), names={"ZeroDivisionError": "DivisionByTheVoid"}, file=file)
    file.flush()
    text = raw.getvalue().decode("cp1252")
    assert rubric.BANNER_OPEN in text and "DivisionByTheVoid: division by zero" in text
    assert 'intone("?")' in text
```

- [ ] **Step 2: Run them; expect `ModuleNotFoundError: liturgy.rubric`**

Run: `.venv/bin/pytest tests/test_rubric.py -v`

- [ ] **Step 3: Create `rubric.py` and make `curse.py` delegate**

Move the pure logic named above into `rubric`. `curse` gains a private `_LiveSeer` built from its existing `_is_litany`, `_is_plumbing`, `_line_for`, `_map_for`, `_py_line_for` and the caret/column mapping now in `_render_lit_frame` and `_render_syntax_location`. Unencodable text: `render` writes the joined text with `file.write`; on `UnicodeEncodeError` it re-encodes with `errors="replace"` using `file.encoding` and writes that.

- [ ] **Step 4: Run the new tests and the whole curse suite; expect all PASS**

Run: `.venv/bin/pytest tests/test_rubric.py tests/test_curse.py tests/test_cli.py tests/test_commune.py tests/test_loader.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/liturgy/rubric.py src/liturgy/curse.py tests/test_rubric.py
git commit -m "refactor(curse): split the renderer into rubric, which imports nothing from Liturgy"
```

---

### Task 2: `TableSeer`, the executable's seer

**Files:**
- Modify: `src/liturgy/rubric.py`
- Test: `tests/test_rubric.py`

**Interfaces:**
- Consumes: `Placement`, `Seer`, `render` from Task 1.
- Produces, in `rubric`:
  - `Tables = dict[str, tuple[str, dict[int, int], list[str]]]`: key is the staged module's path relative to the staging root, `/`-separated (`"pkg/cog.py"`); value is (litany path to show, `{generated line: litany line}`, litany source lines without newlines).
  - `key_for(filename: str, root: str) -> str`: `os.path.relpath`, `os.path.normcase`, `os.sep` to `/`.
  - `class TableSeer(tables: Tables, root: str)`: `is_litany` is "its key is in `tables`"; `is_plumbing` is `frame.filename.startswith("<frozen importlib.")`; `place` maps the line, falling back to the nearest mapped line above it, and a frame above every mapped line keeps its generated number with no source; the caret is always `None`. `place_syntax` does the same lookup on `exc.filename`/`exc.lineno`.

- [ ] **Step 1: Write the failing tests**

```python
TABLES = {
    "hymn.py": ("hymn.lit", {3: 7, 4: 9}, ["", "", "", "", "", "", "rite main() -> Void:", "", "    divide(1, 0)"]),
    "helpers/util.py": ("helpers/util.lit", {1: 1, 2: 2}, ["rite whisper() -> Void:", "    proclaim LostPattern('x')"]),
    "other/util.py": ("other/util.lit", {1: 1}, ["rite shout() -> str:"]),
}

def _frame(path, line, name="main"):
    return traceback.FrameSummary(path, line, name, lookup_line=False)

def test_table_seer_maps_generated_lines_to_litany_lines(tmp_path):
    seer = rubric.TableSeer(TABLES, str(tmp_path))
    assert seer.place(_frame(str(tmp_path / "hymn.py"), 4)) == ("hymn.lit", 9, "    divide(1, 0)", None)

def test_unmapped_line_falls_back_to_the_nearest_mapped_line_above(tmp_path):
    seer = rubric.TableSeer(TABLES, str(tmp_path))
    assert seer.place(_frame(str(tmp_path / "hymn.py"), 5))[1] == 9

def test_same_stem_in_two_packages_is_kept_apart(tmp_path):
    seer = rubric.TableSeer(TABLES, str(tmp_path))
    assert seer.place(_frame(str(tmp_path / "helpers" / "util.py"), 2))[0] == "helpers/util.lit"

def test_files_outside_the_tables_are_not_litanies(tmp_path):
    seer = rubric.TableSeer(TABLES, str(tmp_path))
    assert not seer.is_litany(str(tmp_path / "helper.py"))
    assert not seer.is_litany("/usr/lib/python3/threading.py")
```

- [ ] **Step 2: Run; expect `AttributeError: TableSeer`**

Run: `.venv/bin/pytest tests/test_rubric.py -v`

- [ ] **Step 3: Implement `key_for` and `TableSeer` in `rubric.py`**

- [ ] **Step 4: Run; expect PASS**

Run: `.venv/bin/pytest tests/test_rubric.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/liturgy/rubric.py tests/test_rubric.py
git commit -m "feat(rubric): TableSeer places frames from baked tables"
```

---

### Task 3: Render a litany as Python, with its line map

**Files:**
- Create: `src/liturgy/unction.py`
- Modify: `tests/test_roundtrip.py`
- Test: `tests/test_unction.py`

**Interfaces:**
- Consumes: `compiler._artifacts(src, filename)` (returns `(tree, py, smap)`).
- Produces, in `unction`:
  - `HOOK_MODULE = "__liturgy_curse"`
  - `class UnctionFault(Exception)`: constructed `UnctionFault(path: str, reason: str)`, with `.path` and `.reason`; `str()` is the reason.
  - `line_map(tree: ast.Module, text: str, path: str = "<unknown>") -> dict[int, int]`: re-parses `text`; raises `UnctionFault(path, ...)` if `ast.dump` of the two trees differs; otherwise walks both in lockstep and records `{generated stmt line: original stmt line}` for every `ast.stmt` whose original `lineno` is truthy (first wins).
  - `render_litany(src: str, filename: str, *, entry: bool = False) -> tuple[str, dict[int, int]]`: `_artifacts` with sanction on; when `entry`, inserts the hook; returns `ast.unparse(tree) + "\n"` and `line_map(tree, text, filename)`.

The lockstep walk is the one algorithm the signature leaves open:

```python
def _lockstep(a: ast.AST, b: ast.AST, out: dict[int, int]) -> None:
    if isinstance(a, ast.stmt) and getattr(a, "lineno", 0):
        out.setdefault(b.lineno, a.lineno)
    for (_, va), (_, vb) in zip(ast.iter_fields(a), ast.iter_fields(b)):
        if isinstance(va, list):
            for x, y in zip(va, vb):
                if isinstance(x, ast.AST):
                    _lockstep(x, y, out)
        elif isinstance(va, ast.AST):
            _lockstep(va, vb, out)
```

Hook position: after a leading docstring (`Expr` holding a `str` `Constant`) and every `ImportFrom` of `__future__` that follows it. The node is `ast.Import(names=[ast.alias(HOOK_MODULE)])` with `lineno`, `end_lineno`, `col_offset` and `end_col_offset` all 0, so the walk skips it.

- [ ] **Step 1: Write the failing tests** in `tests/test_unction.py`

```python
def test_hook_follows_docstring_and_future_import():
    src = '"""doc"""\nwithin __future__ invoke annotations\nintone(1)\n'
    text, lm = unction.render_litany(src, "e.lit", entry=True)
    assert text.splitlines()[:4] == ['"""doc"""', "from __future__ import annotations", "import __liturgy_curse", "print(1)"]
    assert lm == {1: 1, 2: 2, 4: 3}

def test_hook_is_first_in_a_bare_litany():
    text, _ = unction.render_litany("intone(1)\n", "e.lit", entry=True)
    assert text.splitlines()[0] == "import __liturgy_curse"

def test_non_entry_litanies_get_no_hook():
    text, _ = unction.render_litany("intone(1)\n", "m.lit")
    assert "__liturgy_curse" not in text

def test_construct_statements_map_to_the_construct_line():
    src = (pathlib.Path(__file__).parents[1] / "examples" / "constructs.lit").read_text(encoding="utf-8")
    text, lm = unction.render_litany(src, "constructs.lit", entry=True)
    litany_line = next(i for i, l in enumerate(src.splitlines(), 1) if "litany(" in l)
    gen = [i for i, l in enumerate(text.splitlines(), 1) if "__liturgy_attempt_0" in l]
    assert gen and all(lm[i] == litany_line for i in gen)

def test_multi_line_statement_maps_to_its_first_line():
    _, lm = unction.render_litany("total = max(\n    1,\n    4,\n)\n", "m.lit")
    assert lm == {1: 1}

def test_a_tree_that_does_not_round_trip_is_refused():
    with pytest.raises(unction.UnctionFault):
        unction.line_map(ast.parse("x = 1"), "x = 2\n")
```

- [ ] **Step 2: Run; expect `ModuleNotFoundError: liturgy.unction`**

Run: `.venv/bin/pytest tests/test_unction.py -v`

- [ ] **Step 3: Implement `unction.py` as specified above**

- [ ] **Step 4: Run; expect PASS**

Run: `.venv/bin/pytest tests/test_unction.py -v`

- [ ] **Step 5: Add the corpus backstop to `test_real_python_files_round_trip_through_liturgy`**

Inside the existing `try`, after `back = ...`: `tree = _artifacts(lit, str(path), sanction=False)[0]` and `unction.line_map(tree, ast.unparse(tree))`, where `lit = to_liturgy(src)` is hoisted so it is computed once. A raise is appended to `failures` by the existing `except`. `CORPUS_FLOOR` and `CORPUS_TARGET` are not touched.

- [ ] **Step 6: Run the sweep; expect PASS with the usual swept count**

Run: `.venv/bin/pytest tests/test_roundtrip.py -v -s`

- [ ] **Step 7: Commit**

```bash
git add src/liturgy/unction.py tests/test_unction.py tests/test_roundtrip.py
git commit -m "feat(unction): render litanies as Python with a line map back to the litany"
```

---

### Task 4: Stage a project and bake the curse

**Files:**
- Modify: `src/liturgy/unction.py`
- Create: `tests/conftest.py`
- Test: `tests/test_unction.py`

**Interfaces:**
- Consumes: `render_litany`, `HOOK_MODULE`, `UnctionFault` (Task 3); `rubric.Tables`, rubric's source file (Tasks 1-2); `lexicon.INVERSE`; `transform.split_lines`; `tooling._gather` (tests and Task 5 call it, `stage` does not).
- Produces, in `unction`:
  - `bake(tables: rubric.Tables) -> str`: rubric's source text verbatim, then `_TABLES = {tables!r}`, `_NAMES = {dict(INVERSE)!r}`, then `install(TableSeer(_TABLES, os.path.dirname(os.path.abspath(__file__))), _NAMES)`.
  - `stage(entry: pathlib.Path, files: list[pathlib.Path], staging: pathlib.Path) -> int`: root is `entry.parent`. Each `.lit` is decoded with `importlib.util.decode_source(path.read_bytes())` (as `chant` does), rendered (`entry=True` for the entry), and written to `staging/<rel>.py` as UTF-8. Its table row is `(rel .lit posix, line map, [l.rstrip("\n") for l in split_lines(src)])`. Each `.py` is copied with `shutil.copy2` at its relative path. `staging/__liturgy_curse.py` is written from `bake`. Returns the number of litanies. `SyntaxError` (including `TechHeresy` and `UnfinishedLitany`) propagates; `UnicodeDecodeError`, `ValueError` and `LookupError` are re-raised as `UnctionFault(str(path), f"{type(err).__name__}: {err}")`.
- Produces, in `tests/conftest.py`:
  - fixture `codex(tmp_path) -> pathlib.Path`: writes the project below and returns its root.
  - `chant_run(root: pathlib.Path, omen: str) -> subprocess.CompletedProcess` runs `[sys.executable, "-m", "liturgy", "chant", "hymn.lit", omen]` with `cwd=root`.
  - `normalise(text: str, root: pathlib.Path) -> str` strips `f"{root}{os.sep}"`, turns `os.sep` into `/`, and drops caret-only lines (`re.fullmatch(r"\s*\^+\s*", line)`).
  - `OMENS = ("thread", "chain", "twin")`: the faults that must match `chant` exactly.

The `codex` project (verified under `liturgy chant` while planning). `hymn.lit`:

```
"""The entry litany: every shape an anointing must carry."""
within __future__ invoke annotations

invoke sys
invoke threading
invoke helper
within rites invoke divide
within pkg.cog invoke Cogitator
within reliquary.tally invoke tally
within sanctum.orison invoke orison
within helpers.util invoke whisper
within other.util invoke shout


rite main(omen: str) -> Void:
    intone(divide(6, 2), Cogitator("alpha").speak(), helper.double(4))
    intone(tally(), orison(), shout())
    should omen == "thread":
        t = threading.Thread(target=Cogitator("omega").fail)
        t.start()
        t.join()
    lest omen == "chain":
        attempt:
            divide(1, 0)
        curse DivisionByTheVoid styled e:
            proclaim MotiveFailure("the spirit is silent") within e
    lest omen == "sprawl":
        total = max(
            1,
            2 / 0,
        )
    lest omen == "twin":
        whisper()


introit:
    main(sys.argv[1])
```

| File | Content |
|---|---|
| `rites.lit` | bytes `b"\xef\xbb\xbf## \xe2\x9a\x99 the rite of division \xe2\x9a\x99\nrite divide(a: float, b: float) -> float:\n    render a / b  ## \xc3\xb7\n"` |
| `pkg/__init__.lit` | `VERSION: int = 1` |
| `pkg/cog.lit` | `pattern Cogitator:` with `rite __init__(self, name: str) -> Void: self.name = name`, `rite speak(self) -> str: render f"++ {self.name} speaks ++"`, `rite fail(self) -> Void: proclaim ImpureOffering(f"{self.name} is corrupted")` (one statement per line, `fail`'s `proclaim` on line 9) |
| `reliquary/__init__.lit` + `reliquary/tally.py` | `SEAL: str = "reliquary"`; `def tally(): return 3` |
| `sanctum/__init__.py` (empty) + `sanctum/orison.lit` | `rite orison() -> str: render "spoken in the sanctum"` |
| `helpers/util.lit`, `other/util.lit` (no `__init__`) | `rite whisper() -> Void: proclaim LostPattern("the whisper is lost")`; `rite shout() -> str: render "SHOUT"` |
| `helper.py` | `def double(x): return x * 2` |
| `venv/pyvenv.cfg` (empty) + `venv/broken.lit` | `rite (:` |

- [ ] **Step 1: Write `tests/conftest.py` and the failing tests**

```python
def _staged(codex, tmp_path):
    files, notes = _gather([str(codex)])
    assert not notes
    staging = tmp_path / "staged"
    n = unction.stage(codex / "hymn.lit", files, staging)
    return staging, n

def _run_staged(staging, omen, cwd):
    # -S: no site-packages, so Liturgy cannot be imported even by accident
    return subprocess.run([sys.executable, "-S", str(staging / "hymn.py"), omen],
                          cwd=cwd, capture_output=True, text=True)

@pytest.mark.parametrize("omen", OMENS)
def test_staged_curse_matches_chant(codex, tmp_path, omen):
    staging, _ = _staged(codex, tmp_path)
    expected = normalise(chant_run(codex, omen).stderr, codex)
    assert _run_staged(staging, omen, tmp_path).stderr == expected

def test_staged_clean_run_matches_chant(codex, tmp_path):
    staging, n = _staged(codex, tmp_path)
    assert n == 8
    run = _run_staged(staging, "", tmp_path)
    assert run.returncode == 0 and run.stdout == chant_run(codex, "").stdout

def test_sprawling_statement_reports_its_first_line(codex, tmp_path):
    staging, _ = _staged(codex, tmp_path)
    err = _run_staged(staging, "sprawl", tmp_path).stderr
    assert "hymn.lit, line 28, in rite main" in err and "total = max(" in err
    assert "line 30" not in err

def test_environments_are_neither_staged_nor_fatal(codex, tmp_path):
    staging, _ = _staged(codex, tmp_path)
    assert not (staging / "venv").exists()

def test_baked_module_imports_nothing_from_liturgy(codex, tmp_path):
    staging, _ = _staged(codex, tmp_path)
    tree = ast.parse((staging / "__liturgy_curse.py").read_text(encoding="utf-8"))
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not any(m.startswith("liturgy") for m in names)
```

`chain` covers Review Focus 4 (the BOM'd `rites.lit` line `render a / b  ## ÷`); `twin` covers 5; `venv/` covers 3.

- [ ] **Step 2: Run; expect `AttributeError: stage`**

Run: `.venv/bin/pytest tests/test_unction.py -v`

- [ ] **Step 3: Implement `bake` and `stage`**

- [ ] **Step 4: Run; expect PASS**

Run: `.venv/bin/pytest tests/test_unction.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/liturgy/unction.py tests/conftest.py tests/test_unction.py
git commit -m "feat(unction): stage a litany tree as Python with a baked curse"
```

---

### Task 5: The `anoint` verb

**Files:**
- Modify: `src/liturgy/tooling.py`, `src/liturgy/cli.py`, `pyproject.toml`, `tests/test_cli.py`
- Test: `tests/test_anoint.py`

**Interfaces:**
- Consumes: `unction.stage`, `unction.UnctionFault` (Task 4); `tooling._gather`.
- Produces, in `tooling`:
  - `nuitka_available() -> bool`: `importlib.util.find_spec("nuitka") is not None`, never importing it.
  - `anoint(path: str, dest: str | None = None, *, out=None, build=None) -> int`. `build: Callable[[pathlib.Path, pathlib.Path], int] | None` takes (staged entry, output file) and returns an exit code. `None` means run Nuitka, which requires `nuitka_available()`.
- `cli`: `anoint` subparser with global flags, positional `file`, `-o/--out dest="dest"`, help `"render a litany as a native executable"`; dispatch `anoint(args.file, args.dest)`. `RESERVED_VERBS` and its comment are deleted.

Order of work in `anoint` (each refusal returns 1 before anything is written):
1. `build is None and not nuitka_available()`: the exact two-line refusal.
2. `entry = pathlib.Path(os.path.abspath(path))`. Missing: `++ CANNOT ANOINT: {path} does not exist ++`. Suffix not `.lit`: `++ CANNOT ANOINT: {path} is not a litany ++`.
3. Output: `dest` made absolute against the cwd, or by default `entry.with_name(entry.stem + (".exe" if os.name == "nt" else ""))`. A missing parent directory: `++ CANNOT ANOINT: {parent} does not exist ++`.
4. `files, notes = _gather([str(entry.parent)])`; each note is refused forge-style, `++ CANNOT ANOINT: {d} {message} ++`.
5. Print `++ ANOINTING {entry.name} ++`, flushed.
6. In `tempfile.TemporaryDirectory(prefix="liturgy-anoint-", ignore_cleanup_errors=True)`, stage into `<tmp>/staged`. A `SyntaxError` gives `++ CANNOT ANOINT: {err.filename relative to root} line {err.lineno} {type}: {err.msg} ++`; an `UnctionFault` gives `++ CANNOT ANOINT: {fault.path} {fault} ++`. Then print `   {n} litan{"y" if n == 1 else "ies"} rendered; the machine tongue is being forged`, flushed.
7. `code = build(staging / f"{entry.stem}.py", tmp / "out" / dest.name)`. Non-zero, or no file produced: `++ CANNOT ANOINT: nuitka failed (exit {code}) ++`.
8. Replace any existing `dest`, `shutil.move` the file there, then print `++ {entry.name} IS ANOINTED: {dest} ++`.

The default build, not captured, with stdin inherited:
`[sys.executable, "-m", "nuitka", "--mode=onefile", "--follow-imports", f"--output-dir={output.parent}", f"--output-filename={output.name}", str(entry)]` with `cwd=entry.parent`.

`pyproject.toml`: `anoint = ["nuitka>=4.3", "patchelf; sys_platform == 'linux'"]`; under `[tool.pytest.ini_options]`, `markers = ["slow: builds a native executable with Nuitka"]`.

- [ ] **Step 1: Write the failing tests** in `tests/test_anoint.py` (the `codex` fixture from conftest)

```python
def fake_build(calls):
    def build(entry, output):
        calls.append((entry, output, sorted(p.name for p in entry.parent.iterdir())))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"MZ")
        return 0
    return build

def test_refuses_without_nuitka(monkeypatch, codex):
    monkeypatch.setattr(tooling, "nuitka_available", lambda: False)
    buf = io.StringIO()
    assert tooling.anoint(str(codex / "hymn.lit"), out=buf) == 1
    assert buf.getvalue() == ("++ CANNOT ANOINT: nuitka is not installed ++\n"
                              "   anointing needs it:  pip install 'liturgy[anoint]'\n")

def test_writes_the_executable_beside_the_litany_and_nothing_else(codex):
    before = sorted(p.name for p in codex.iterdir())
    calls = []
    assert tooling.anoint(str(codex / "hymn.lit"), out=io.StringIO(), build=fake_build(calls)) == 0
    name = "hymn.exe" if os.name == "nt" else "hymn"
    assert sorted(p.name for p in codex.iterdir()) == sorted(before + [name])
    assert "__liturgy_curse.py" in calls[0][2] and calls[0][0].name == "hymn.py"
    assert not calls[0][0].parent.exists()  # staging removed

def test_out_flag_places_it_elsewhere(codex, tmp_path): ...  # dest=tmp_path/"bin"/"x" with bin/ created; file exists there
def test_reanointing_replaces_the_old_executable(codex): ...    # pre-write b"old" at dest; after: b"MZ", exit 0
def test_relative_entry_from_another_cwd(codex, monkeypatch):    # chdir(codex.parent); anoint("<codex name>/hymn.lit"); codex/hymn exists
def test_an_uncompilable_litany_anywhere_refuses(codex):         # write codex/bad.lit "rite (:\n"; exit 1; "CANNOT ANOINT: bad.lit line 1" in output; no codex/hymn
def test_a_failed_build_refuses_and_cleans_up(codex): ...        # build returns 2; exit 1; "nuitka failed (exit 2)"; no codex/hymn; staging gone
def test_refuses_a_missing_file_and_a_python_file(tmp_path): ... # both exit 1 with the messages above

needs_nuitka = pytest.mark.skipif(
    not tooling.nuitka_available() and not os.environ.get("LITURGY_REQUIRE_NUITKA"),
    reason="needs liturgy[anoint]")

@needs_nuitka
@pytest.mark.slow
def test_an_anointed_executable_curses_like_chant(codex, tmp_path):
    expected = {o: normalise(chant_run(codex, o).stderr, codex) for o in OMENS}
    clean = chant_run(codex, "").stdout
    shipped = tmp_path / "elsewhere"; shipped.mkdir()
    dest = shipped / ("hymn.exe" if os.name == "nt" else "hymn")
    assert tooling.anoint(str(codex / "hymn.lit"), str(dest)) == 0
    shutil.rmtree(codex)  # the sources are gone; only the executable remains
    for omen in OMENS:
        assert subprocess.run([str(dest), omen], cwd=shipped, capture_output=True, text=True).stderr == expected[omen]
    run = subprocess.run([str(dest), ""], cwd=shipped, capture_output=True, text=True)
    assert run.returncode == 0 and run.stdout == clean
```

In `tests/test_cli.py`, replace `test_reserved_verbs_are_declared` with `test_anoint_is_a_verb` (`run_cli(["anoint", "--help"]).returncode == 0`), and change `test_an_unknown_verb_is_rejected` to use `"exorcise"`.

- [ ] **Step 2: Run; expect failures (`anoint` missing)**

Run: `.venv/bin/pytest tests/test_anoint.py tests/test_cli.py -v`

- [ ] **Step 3: Implement `nuitka_available`, `anoint`, the subparser and the extra; delete `RESERVED_VERBS`**

- [ ] **Step 4: Install the extra and run everything, the slow test included**

Run: `uv pip install -p .venv -e '.[anoint]' && .venv/bin/pytest tests/test_anoint.py -v -rs`
Expected: all PASS, nothing skipped. Repeat with `.venv314`.

- [ ] **Step 5: Run the full suite on both versions; expect green**

Run: `.venv/bin/pytest -q && .venv314/bin/pytest -q`

- [ ] **Step 6: Commit**

```bash
git add src/liturgy/tooling.py src/liturgy/cli.py pyproject.toml tests/test_anoint.py tests/test_cli.py
git commit -m "feat(anoint): render a litany as a native executable"
```

---

### Task 6: Verify on three platforms

**Files:**
- Create: `.github/workflows/anoint.yml`

**Interfaces:** none.

- [ ] **Step 1: Write the workflow**

The workflow:
- runs on `push` and `pull_request`;
- has one job with matrix `os: [macos-latest, ubuntu-latest, windows-latest]` and `python: ["3.12", "3.14"]`, with `fail-fast: false` and `timeout-minutes: 45`;
- runs `actions/checkout`, then `actions/setup-python` with `${{ matrix.python }}`, then `python -m pip install -e ".[anoint]" pytest`;
- runs `python -m pytest tests/test_rubric.py tests/test_unction.py tests/test_anoint.py -v -rs` with `LITURGY_REQUIRE_NUITKA: "1"`, so the end-to-end test fails rather than skips if Nuitka is absent.

- [ ] **Step 2: Push the branch and read the run.** This needs the user's go-ahead.

Expected: six green jobs. If Linux fails on `patchelf`, record what Nuitka asked for and fix the extra or the docs. If Windows fails on output encoding or path keys, fix it in `rubric` with a test that reproduces it.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/anoint.yml
git commit -m "ci: verify anoint on macOS, Linux and Windows"
```

---

### Task 7: Documentation

**Files:**
- Modify: `docs/LIBER-LITURGIAE.md`, `docs/liber-liturgiae.html`, `README.md`, `docs/index.html`, `docs/liturgy-data-slate.html`, `CLAUDE.md`

**Interfaces:** none.

- [ ] **Step 1: Liber first.**
  - **Chapter IX:** delete *The one verb still unwritten*, and move its history of how each reserved name was spent elsewhere in the chapter, with `anoint` added.
  - **Chapter XI:** add `anoint` to the verb list and the opening count. Give it its own section covering:
    - real output from a run;
    - the extra;
    - what survives in a curse, and what does not (the spec's table);
    - relative paths;
    - one OS per build;
    - Gatekeeper, with the command that clears the quarantine;
    - Linux `patchelf`;
    - the `.exe` name on Windows;
    - data files and `__file__`;
    - source carried in plain text;
    - litanies outside the folder.
  - **Chapter II:** reword the "no verb for anointing an environment" paragraph.
- [ ] **Step 2: Mirror the change.** Update `liber-liturgiae.html` (per `docs/STYLE-COGITATOR.md`), the README (the incompleteness note at line 29, the reserved-name list near line 1191, the extras list), `index.html` (mirrors the README's claims), and the data slate (line 506).
- [ ] **Step 3: `CLAUDE.md` *Where things go*.** `rubric` is a leaf that imports nothing from Liturgy and is copied into executables. `unction` sits after `compiler`.
- [ ] **Step 4: Run every documented command and paste the real output.** Run `liturgy anoint` and the executable's curse on macOS. Take platform claims from the Task 6 run. Then `grep -n "anoint" README.md docs/*` and check that each hit is current.
- [ ] **Step 5: Add a spec correction note for any claim the build superseded.** The repo's convention is a *(Correction, post-review: ...)* note.
- [ ] **Step 6: Full suite on both versions; expect green.** `.venv/bin/pytest -q && .venv314/bin/pytest -q`
- [ ] **Step 7: Commit**

```bash
git add docs README.md CLAUDE.md design/specs/2026-11-07-liturgy-anoint-design.md
git commit -m "docs: anoint, the last reserved verb, is built"
```
