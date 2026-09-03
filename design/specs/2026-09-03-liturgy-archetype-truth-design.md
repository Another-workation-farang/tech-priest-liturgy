# Liturgy Archetype Truth: Design

**Date:** 2026-09-03
**Status:** Scheduled. Plan at `design/plans/2026-09-03-liturgy-archetype-truth.md`.
**Depends on:** Spec IV, Task 1 (carrier out of band): **satisfied** at
v0.4.0. Re-measured against the post-Spec-IV tree before planning:
`consecrated PORT: int = 8080` now generates `PORT: int = 8080` and mypy
type-checks *uses* of PORT, which the carrier previously made impossible.
`__consecrated__` no longer appears in any diagnostic; `__litany__` and
`__augur__` still do.

## Purpose

Spec IV guarantees presence and says plainly it cannot guarantee correctness.
This is how correctness would be delivered when it is worth doing.

**The finding that makes this tractable: Liturgy does not need a type
checker. It needs a translator.** Because the transform never adds or removes
a line, line N of the generated Python is line N of the litany, so an
existing checker's diagnostics already land on the right line, with no mapping
at all.

## Proof of concept, run before this document was written

`prayer.lit`:

```
rite greet(name: str) -> int:
    render name

rite add(a: int, b: int) -> int:
    render a + b

intone(add("one", 2))
```

Transformed to Python and handed to mypy 2.3.1:

```
prayer.py:2: error: Incompatible return value type (got "str", expected "int")
prayer.py:7: error: Argument 1 to "add" has incompatible type "str"; expected "int"
```

Lines 2 and 7 of `prayer.lit` are exactly `render name` and
`intone(add("one", 2))`. **The line numbers need no translation whatsoever.**
Only columns do, and `SourceMap.to_lit` already exists for precisely that:
it is what maps traceback carets today.

This is the whole feasibility argument. Everything below is detail.

## Architecture

Do not write a type checker. Delegate, and translate.

1. Transform each `.lit` into Python, keeping its `SourceMap`.
2. Hand the generated Python to mypy.
3. Map each diagnostic back: the line is already correct; the column goes
   through `char_offset` then `SourceMap.to_lit`.
4. Translate the message's vocabulary from Python to Liturgy.
5. Render it in house style, with the caret on the litany's own source line.

mypy is a third-party dependency, so it is an **optional extra**, exactly as
Pygments is for `[highlight]` and pytest is for `[trials]`. The core keeps
zero runtime dependencies. Absent the extra, the verb refuses cleanly the way
`prove` does.

## The carriers are visible to the checker

The blocking problem, and it is bigger than Spec IV's.

Constructs desugar through carrier names that exist only to be restructured by
a later AST pass. mypy sees the intermediate source and reports them as
undefined. Verified, all three:

```
c.py:1: error: Name "__consecrated__" is not defined  [name-defined]
l.py:1: error: Name "__litany__" is not defined  [name-defined]
```

`consecrated PORT = 8080` generates `PORT: __consecrated__ = 8080`, so mypy
does not merely emit a spurious error; it also learns `PORT` has an unknown
type and cannot check any *use* of it.

Spec IV Task 1 removes the `consecrated` carrier and generates
`PORT: int = 8080`, which mypy checks properly. That is why this spec depends
on it. `__litany__` and `__augur__` remain.

**Three ways out, in order of preference:**

1. **Extend the out-of-band pattern to all three carriers.** Spec IV
   establishes the mechanism for one; applying it to `litany` and `augur`
   makes the generated Python always valid Python meaning what the litany
   means. Cleanest, and worth doing on its own merits. Largest change.
2. **Filter the diagnostics.** Drop any `name-defined` error naming a known
   carrier. Cheap and zero risk to the language, but it only silences the
   noise: a `litany` block's own body still type-checks, so the loss is
   smaller than it looks.
3. **Stub the carriers for the checker.** Rejected: declaring them requires
   either adding a line, which the line invariant forbids, or a config
   mechanism mypy does not cleanly offer for non-imported names.

Recommend (2) first, since it ships the feature, then (1) as a follow-up.

## Message translation

mypy speaks Python. A litany's author has never written `def` or `return`.

```
mypy:     Incompatible return value type (got "str", expected "int")
Liturgy:  this rite renders a str where it declared an int
```

The vocabulary mapping already exists (`lexicon.INVERSE`) and `reverse.py`
already renders Python into Liturgy. Translation is a lookup over the
message's quoted type names and its Python keywords, not new machinery.

Messages that cannot be confidently translated are passed through verbatim
rather than mangled, and marked as coming from the checker. **A half-translated
diagnostic is worse than an honest untranslated one.**

## Where it lives

`augur --archetypes`, gated on the optional extra.

`augur` is already the verb that reads a litany for faults without chanting
it, and a false archetype is a fault. This adds no verb, spends no reserved
name, and leaves `anoint` unspent; Chapter IX's argument stands.

It is a **flag, not a default**: mypy on a large tree is slow, and `augur`'s
current contract is that it is fast enough to run constantly. Chapter XI's
"two checks, and no third" becomes "three, and the third is asked for".

## Multi-module

The hard part, and the reason this is not a weekend.

mypy follows imports. A litany importing another litany means the checker
needs *both* as Python, with module identity preserved. That implies a shadow
tree: transform every `.lit` in the project into a parallel directory whose
layout mirrors the original, then point mypy at it.

Consequences to design before building:

- Package structure must be mirrored, `__init__.lit` included.
- A `.lit` importing a `.py` and vice versa must resolve.
- The shadow tree is a build artifact and belongs under `__pycache__` or a
  sibling ignored directory, and `purge` should clear it.
- Cache invalidation: mypy's own incremental cache plus ours.

A first version may reasonably check **one file at a time with imports
unfollowed**, which catches the large majority of real errors and defers all
of the above. Say so in the docs rather than implying whole-project checking.

## Out of scope

- **Writing a checker.** Person-decades, and mypy exists.
- **Runtime type enforcement.** Generated guards would violate the no-runtime
  rule and change performance and semantics.
- **Making the checker's judgement authoritative.** `chant` must keep running
  code mypy dislikes. This is a reading rite, like the rest of `augur`.

## Plan sketch

| Task | Deliverable |
|---|---|
| 1 | `[archetypes]` extra; `augur --archetypes` refuses cleanly without it |
| 2 | Single-file path: transform, run mypy, map line and column back |
| 3 | Carrier-noise filter (option 2 above), with the three names covered |
| 4 | Message translation via `lexicon.INVERSE`, untranslatable passed through |
| 5 | House-style rendering with carets; `--plain` for CI |
| 6 | Shadow tree for multi-module, or documented single-file limitation |
| 7 | Documentation, stating plainly what the checker does and does not know |
