# Liturgy Archetype Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** `augur --archetypes` reports archetypes that are *false*, not merely
absent — by delegating to mypy and translating its diagnostics back into
Liturgy.

**Architecture:** Liturgy does not need a type checker; it needs a translator.
The transform never adds or removes a line, so a checker's diagnostics on the
generated Python already land on the right line of the litany. Columns go back
through `SourceMap.to_lit`. mypy is an optional extra.

**Spec:** `design/specs/2026-09-03-liturgy-archetype-truth-design.md`

## Global Constraints

- Python 3.12 floor. **The core keeps zero runtime dependencies** — mypy is an
  optional extra, as Pygments is for `[highlight]` and pytest for `[trials]`.
  Nothing outside the new module may import it.
- `ast` and `traceback` count UTF-8 bytes; everything else counts characters.
  Offsets go through `sourcemap.char_offset`.
- No `ast.walk` in `src/` except `collisions.py` and `seals.py`.
- `-> int` CLI contracts never raise for bad input.
- Every documented command and output is run before it ships.

## Measured facts — verified against the post-Spec-IV tree, do not re-derive

1. **Line mapping is free.** `transform` preserves line count exactly. mypy's
   errors land on the litany's own lines with no arithmetic.
2. **mypy columns are 1-based** with `--show-column-numbers`. `SourceMap.to_lit`
   takes 0-based. Subtract one going in; add one coming out for display.
3. **Spec IV made `consecrated` checkable.** `consecrated PORT: int = 8080`
   now generates `PORT: int = 8080`, and mypy catches `PORT + "nine"` as
   `Unsupported operand types for + ("int" and "str")`. Before Spec IV the
   carrier made `PORT`'s type unknown.
4. **Two carriers still leak.** `__litany__` and `__augur__` are reported as
   `Name "..." is not defined [name-defined]`. `__consecrated__` no longer
   appears at all.
5. **`--follow-imports=skip --ignore-missing-imports`** silences unknown-module
   noise while still reporting real errors in the file under test.

---

### Task 1: The checker core

**Files:** create `src/liturgy/archetypes.py`; test `tests/test_archetypes.py`

**Produces:** `check(src, filename) -> list[Finding]`, where `Finding` carries
`line`, `col` (0-based, Liturgy), `message`, `code` and `severity`.

Transform the litany, write the generated Python to a temp file, run mypy over
it, parse the diagnostics, map each back, and return them. Nothing is printed
here — rendering is Task 2's.

**Hazards:**
- Run mypy through `mypy.api.run` or a subprocess, but **isolate its cache**
  (`--cache-dir` under a temp directory) so a user's project is never polluted
  and runs cannot interfere.
- The temp file's *name* becomes the module name mypy reports. Keep the
  litany's stem so messages read naturally, and strip the temp directory from
  the reported path before it reaches a `Finding`.
- A diagnostic with no column (mypy omits it for some codes) must still
  produce a usable `Finding`. Do not invent a column.
- mypy failing to run at all — not installed, crashed, timed out — is not a
  finding. Raise something the caller can distinguish, or the verb will report
  "no type errors" when it checked nothing. **That silent-success mode is the
  worst outcome available here; guard it explicitly and test it.**
- Filter `name-defined` diagnostics naming `__litany__` or `__augur__`. Take
  the names from `constructs`, never a literal — a third carrier must not
  slip through because someone typed a string. `__consecrated__` is gone but
  costs nothing to include.

### Task 2: The verb

**Files:** `src/liturgy/tooling.py`, `src/liturgy/cli.py`, `pyproject.toml`;
test `tests/test_archetypes_verb.py`

`augur --archetypes`, an optional extra named `archetypes`.

- Without mypy installed: refuse cleanly, as `prove` does without pytest.
  `++ CANNOT READ ARCHETYPES: mypy is not installed ++` and the install line.
- Findings render in the house style with a caret, like every other `augur`
  finding, and honour `--plain`.
- **A flag, not a default.** mypy is slow and `augur`'s contract is that it is
  fast enough to run constantly. Chapter XI's "two checks, and no third"
  becomes "three, and the third is asked for".
- Exit 1 on findings, as `augur` already does.

### Task 3: Message translation

**Files:** `src/liturgy/archetypes.py`; test `tests/test_archetypes.py`

mypy speaks Python; a litany's author has never written `def` or `return`.

```
mypy:     Incompatible return value type (got "str", expected "int")
Liturgy:  this rite renders a str where it declared an int
```

`lexicon.INVERSE` already maps Python spellings to Liturgy ones.

**Hazard, and the important one:** a message that cannot be confidently
translated is **passed through verbatim and marked as the checker's own**. A
half-translated diagnostic is worse than an honest untranslated one. Decide
the set you translate, test each, and let the rest through unharmed.

### Task 4: Documentation

Five surfaces. State plainly:
- what the checker knows, and that it is a **third** check asked for by flag;
- that imports are **not followed** in this version, so it checks one litany at
  a time — say so rather than implying whole-project coverage;
- that `chant` still runs code mypy dislikes. This is a reading rite. The
  checker's judgement is advisory, and `augur`'s own two checks are unchanged.

### Task 5: Release 0.5.0

Bump, build, both Pythons, tag, notes.

## Out of scope

- **The shadow tree for multi-module checking.** Documented limitation instead.
- **Extending the out-of-band pattern to `__litany__` and `__augur__.`** The
  filter ships first; Spec IV made this cheaper than it was, and it is the
  right follow-up, but it is not needed for a first version.
- **Making the checker authoritative.** `chant` must keep running.
