# Liturgy Sanction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Enforce that every rite's parameters and return, and every
consecrated binding, declare an archetype, with `unsanctioned` as the
per-rite and per-file exemption.

**Architecture:** Consecration moves out of the annotation slot into a side
table on `transform`, freeing `consecrated NAME: T = v` to be legal. A new
token pass splices `unsanctioned` out and records the rows it marked.
Enforcement is a compile-time rule in `rewrite.ConstructPass`, so it fires
identically for `chant`, `augur` and `prove`.

**Tech Stack:** Python 3.12+, standard library only.

**Spec:** `design/specs/2026-09-03-liturgy-sanction-design.md`

## Global Constraints

- Python 3.12 floor. Standard library only, no third-party runtime deps.
- **The transform never adds or removes a line.** `_splice` refuses any
  substitution containing `\n`. Length changes are fine and routine
  (`Sanctioned` -> `True` already shortens by 6).
- **`ast` and `traceback` count UTF-8 bytes; everything else counts
  characters.** Any offset from either goes through `sourcemap.char_offset`.
- **No `ast.walk` in `src/`** except `collisions.py` and `seals.py`, which
  are documented scope-blind exceptions. Anything needing scope goes on
  `rewrite._in_scope`.
- **No runtime.** Constructs desugar into self-contained generated Python.
- `-> int` CLI contracts never raise for bad input.
- Every documented command and output is run before it ships.

---

### Task 1: Carry consecration out of the annotation slot

**Files:**
- Modify: `src/liturgy/transform.py`, `src/liturgy/constructs.py`,
  `src/liturgy/rewrite.py`, `src/liturgy/seals.py`, `src/liturgy/collisions.py`
- Test: `tests/test_constructs.py`, `tests/test_consecrated.py`, `tests/test_seals.py`

**Interfaces:**
- Produces: `transform(...)` returns `(python_src, SourceMap, ConstructFacts)`
  where `ConstructFacts` carries `consecrated: dict[int, str]` mapping a
  1-based Liturgy row to the name it seals.

The carrier is the blocker. `consecrated PORT: int = 8080` is a syntax error
today because `_consecrated_carrier` generates `PORT: __consecrated__ = 8080`
and the annotation slot is already taken.

**The change:** `consecrated NAME = v` generates `NAME = v`;
`consecrated NAME: T = v` generates `NAME: T = v`. In both cases the row and
name go into `ConstructFacts.consecrated`.

**Hazards:**
- `transform`'s return arity changes. Every caller must be found: `compiler`,
  `collisions`, `seals`, `form`, `tooling`, `loader`, and the tests. Prefer a
  small frozen dataclass over a bare tuple so a missed caller fails loudly.
- `rewrite._collect_consecrated` currently matches on the carrier annotation.
  It must take the facts instead, keyed by row. Its scope semantics must not
  change: it collects per *scope*, and the rebinding rejection depends on
  that. Do not flatten it.
- `seals.find_seals` matches `CONSECRATED_CARRIER` at module level. Same move.
- `LITANY_CARRIER` and `AUGUR_CARRIER` are **not** part of this task. Leave
  them exactly as they are; only `consecrated` changes.
- 148 `consecrated` references across 15 test files. Most will be unaffected
  (they test behaviour, not the carrier), but any asserting on generated
  Python containing `__consecrated__` must change.

**Steps:** write a failing test that `consecrated PORT: int = 8080` chants
and prints 8080; make it pass; keep the whole suite green. Ablate: revert the
side table and confirm the new test goes red.

---

### Task 2: The `unsanctioned` word

**Files:**
- Modify: `src/liturgy/lexicon.py`, `src/liturgy/constructs.py`,
  `editors/vscode-liturgy/syntaxes/liturgy.tmLanguage.json`
- Test: `tests/test_lexicon.py`, `tests/test_unsanctioned.py` (new)

`unsanctioned` is a modifier, not an alias; it has no Python spelling. It
joins `CONSTRUCT_KEYWORDS` alongside `consecrated`, `litany` and `augur`,
**not** `LEXICON`.

A new token pass splices the word and its following whitespace out, and
records the row:

```
unsanctioned rite legacy(x):   ->   rite legacy(x):        row recorded
    unsanctioned consecrated P = 1  ->  consecrated P = 1  row recorded
unsanctioned                   ->   (blank line)           file-level flag
```

`ConstructFacts` gains `unsanctioned_rows: set[int]` and
`unsanctioned_file: bool`.

**Hazards:**
- Splicing out the word must **not** disturb indentation. Replace the span
  from the word's start column through the following whitespace, so the rest
  of the line shifts left and the leading indentation is untouched. Verify
  with an indented method inside a `pattern`.
- The bare module-level form must leave a blank line, never delete the line.
- `unsanctioned` anywhere it does not belong (mid-expression, before a
  non-rite non-consecrated statement) is a heresy, not a silent no-op.
- `test_every_reserved_word_appears_in_the_grammar` in `tests/test_grammar.py`
  will go red until the VS Code grammar learns the word. That is the test
  doing its job; update the grammar.
- Adding to `RESERVED` makes `unsanctioned` unusable as an identifier, which
  is the reservation rule working as designed. `augur` will now flag it.

---

### Task 3: The enforcement rule

**Files:**
- Modify: `src/liturgy/rewrite.py`
- Test: `tests/test_sanction.py` (new)

In `ConstructPass`, beside the existing rejections, using `self._heresy`.

**Required:** every parameter of a `rite` annotated; a return annotation; every
`consecrated` binding annotated.

**Exempt:**
- `self`/`cls` as the *first* parameter only.
- `servitor` (lambda) entirely: Python cannot annotate lambda parameters.
- Any rite or binding whose row is in `unsanctioned_rows`.
- Every rite and binding when `unsanctioned_file` is set.
- `visit_Interactive`: the REPL. `commune` must not enforce.

**Messages** (house style, caret under the offending name):

```
TechHeresy: name is unsanctioned; every parameter must declare its archetype
TechHeresy: greet is unsanctioned; a rite must declare what it renders
TechHeresy: PORT is unsanctioned; a consecrated name must declare its archetype
```

**Hazards:**
- Positions come from `ast` and are byte offsets. Route through
  `char_offset` then the `SourceMap`, exactly as `collisions` does.
- `*args`/`**kwargs` are annotatable and are **not** exempt.
- Positional-only and keyword-only parameters must be covered:
  `node.args.posonlyargs`, `args`, `kwonlyargs`, `vararg`, `kwarg`.
- A nested rite inside an `unsanctioned` rite: decide and document whether
  exemption inherits. Recommend yes, and test it.

---

### Task 4: Examples and the corpus

**Files:**
- Modify: `examples/*.lit`
- Test: `tests/test_examples.py`, `tests/test_roundtrip.py`

All 5 example rites are unannotated and every one now fails to compile.
Annotate them. They are the first Liturgy anyone reads and must show the
language as it now is.

**The corpus sweep is NOT affected, checked before this plan shipped.**
`test_real_python_files_round_trip_through_liturgy` does
`transform(to_liturgy(src))[0] == src`: it transforms and never compiles, and
enforcement lives in the compile path. The 574-file sweep is untouched.
Task 1 changes `transform`'s return arity, so its `[0]` indexing must keep
working or be updated; that is the only interaction.

**But `transcribe` now emits litanies that do not compile.** Transcribed
Python is unannotated by definition, so `transcribe foo.py -o foo.lit &&
chant foo.lit` fails under enforcement.

*Ruling: transcribe warns; it does not prepend.* Prepending an `unsanctioned`
line was the obvious fix and it is wrong: verified that
`transform("unsanctioned\n" + lit)[0] == src` is **False**, so it breaks
transcribe's own round-trip self-check, which is the guarantee that makes the
verb trustworthy. Instead transcribe gains a line to its existing output-omens
warning naming that the litany will need annotations or an `unsanctioned`
marker. Cost if wrong: a user pastes one word at the top of the file.

---

### Task 5: Documentation

**Files:**
- Modify: `README.md`, `docs/LIBER-LITURGIAE.md`, `docs/liber-liturgiae.html`,
  `docs/liturgy-data-slate.html`, `docs/index.html`

A new **Chapter XII: The Declaration of Archetypes**, in house style: in-voice
frame, plain body. It must say:

- What is enforced, and that it is **presence, not correctness**: Liturgy
  cannot check that an annotation is true, and saying otherwise would promise
  what the language does not deliver.
- The exemptions, each with its reason.
- `unsanctioned` in both scopes.
- That `archetype` is already the word for `type`, and why the annotation
  itself gained no new word.

All 22 `rite` samples across the five surfaces must be annotated. A doc whose
examples do not compile is worse than no doc; run them.

Chapter IX's count of unwritten verbs is unaffected (`anoint` stays reserved),
but its "words meaning two things" list should note `Sanctioned` (True) beside
`unsanctioned`.

---

### Task 6: Release 0.4.0

Bump `pyproject.toml`, verify the wheel builds, run the suite on 3.12 and
3.14, tag, and write release notes leading with the breaking change.
