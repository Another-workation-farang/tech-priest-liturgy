# Liturgy Sanction — Design

**Date:** 2026-09-03
**Status:** Approved
**Scope:** Spec IV. Specs I (Core), II (Constructs) and III (Tooling) are built
and merged at v0.3.0.

## Purpose

Python encourages type hints and enforces nothing. Liturgy enforces them.

A litany must declare the archetype of every rite's parameters, every rite's
return, and every consecrated binding. What cannot be declared is exempt by
construction; what an author deliberately will not declare is exempt by saying
so. Everything else is a heresy at compile time.

This is **presence, not correctness.** Liturgy can guarantee an annotation
exists. It cannot guarantee the annotation is true — that is a type checker,
and writing one is not in scope for a language with no runtime and no
dependencies. The documentation must say so in the same breath it announces
the feature, or the feature promises something it does not deliver. Chapter VII
already sets the precedent for that honesty with `consecrated`.

## What is enforced

| Shape | Requirement |
|---|---|
| `rite f(x):` | every parameter annotated, and a return annotation |
| `consecrated NAME = v` | annotated |

Nothing else. Plain assignments, loop targets, comprehension variables, `with`
targets and exception names are all unannotated in idiomatic Python and
enforcing them would make the language unusable rather than strict.

### Exempt by construction

- **`self` and `cls`** — the first parameter of a method, matching what every
  Python type checker does with `--disallow-untyped-defs`.
- **`servitor` (lambda)** — Python has no syntax for annotating a lambda's
  parameters. `lambda x: int = 1` is a syntax error, so a rule requiring it
  would forbid the construct outright. Verified before this spec was written.
- **`commune` (the REPL)** — every entry is its own compilation unit and a
  prompt that rejects `rite f(x):` is not a REPL anyone will use. Enforcement
  is off at the prompt, and Chapter VIII's existing note about per-unit
  enforcement is the precedent.
- **`.py` files** — Liturgy compiles `.lit`. A Python file is Python's business.

### Exempt by declaration: `unsanctioned`

One new reserved word, and the only one this spec adds.

```
unsanctioned rite legacy(x):
    render x

unsanctioned consecrated PORT = 8080
```

As a **modifier**, it exempts the single rite or binding it precedes. Standing
**alone on a line at module level**, it exempts the whole litany:

```
unsanctioned

rite one(a):
    render a

rite two(b):
    render b
```

The word was chosen against a collision check over all 63 reserved words and
the 10 CLI verbs. Rejected candidates and their nearest existing word:
`inscribed` (0.74 to `transcribe`), `ascribed` (0.78), `attested` (0.86 to
`attest`), `patterned` (0.88 to `pattern`), `forged` (0.91 to `forge`),
`ordained` (0.62 to `anointed`). `unsanctioned` collides with nothing.

Note `Sanctioned` (capital S) is already `True`. The two are distinguished by
case and by position, and a reader meets them in unrelated contexts. This is
recorded rather than discovered later.

## Why no new word for the annotation itself

An earlier design gave the annotation operator its own word — `anoint`, then
`wrought` or `designated`. It was cut, twice, and the reasoning belongs in the
record:

- `anoint` is one letter from `anointed`, which is already `with`. Two
  near-identical words in the same namespace with unrelated meanings is a worse
  trap than the doubled `augur` and `purge`, which live in different namespaces
  and cannot collide.
- Any such word solves only half the problem. A rite's return uses `->`, and
  `rite f(x wrought int) begets str:` needs a *second* reserved word to stay
  consistent. Two words for what Python spells with punctuation.
- Rite annotations already work today, spelled `:` and `->`. The feature the
  user actually asked for is enforcement, and enforcement needs no new
  vocabulary.

`archetype` is already `type` and `pattern` is already `class`. The type
vocabulary is spent, and spent well.

## The blocker: the carrier occupies the annotation slot

`consecrated PORT: int = 8080` is a **syntax error today**:

```
       consecrated PORT: int = 8080
                       ^
   SyntaxError: invalid syntax (PORT is Liturgy for PORT: __consecrated__)
```

`constructs._consecrated_carrier` desugars `consecrated NAME = v` into
`NAME: __consecrated__ = v`. The construct smuggles itself through the
annotation slot, so a consecrated name cannot carry a type at all. Enforcing
annotations on consecrated bindings is impossible until this changes.

### The fix: carry consecration out of band

The carrier exists so an AST pass can find consecrated declarations. But
`transform` already knows which rows carried `consecrated` — it produced the
substitution. That knowledge can travel beside the generated source instead of
inside it.

`transform` gains a side table of construct facts: the rows that declared
`consecrated`, and the name each declared. `consecrated PORT: int = 8080` then
generates `PORT: int = 8080`, and `consecrated PORT = 8080` generates
`PORT = 8080`, with the seal recorded out of band in both cases.

Four modules read the carrier today and must move to the side table:

| Module | Use |
|---|---|
| `constructs.py` | produces `NAME: __consecrated__` |
| `rewrite.py` | `_collect_consecrated`, `_is_consecrated` |
| `collisions.py` | documents the carrier shape |
| `seals.py` | finds module-level seals for `consecrate` |

There are 148 `consecrated` references across 15 test files. This is the
deepest change to the language since Spec II, and it is a prerequisite, not a
nice-to-have.

**It is also a fix on its own merits.** A legal-looking line being a syntax
error for an internal reason is a defect regardless of this spec.

## Where enforcement lives

`rewrite.ConstructPass`, beside the existing compile-time rejections. It shares
their machinery: one traversal, `TechHeresy`, and positions mapped back to
Liturgy through the `SourceMap`. Because it lives in the compile path, it fires
identically for `chant`, `augur` and `prove` — the spec's standing invariant
that augur cannot disagree with chant is preserved by construction.

`augur` therefore reports unannotated rites without a line of its own.

## Errors

House style, positions in Liturgy coordinates, caret under the offending name.

```
++ MACHINE CURSE ++
   the rite was ill-written at prayer.lit, line 3
       rite greet(name):
                  ^^^^
   TechHeresy: name is unsanctioned; every parameter must declare its archetype
++ the machine spirit is displeased ++
```

A missing return annotation points at the rite's own name. A bare
`consecrated PORT = 8080` points at `PORT`.

## What this breaks

Everything, deliberately. 0 of the 5 rites in `examples/` are annotated, and
there are 22 `rite` samples across the five documentation surfaces. All of them
are rewritten as part of this work, not after it. A release whose own examples
do not compile is worse than no release.

This is a breaking change, and correct for a minor bump before 1.0.

## Out of scope

- **Type correctness.** Stated above and stated again in the docs.
- **A per-line escape.** `unsanctioned` is per-rite and per-file. A third
  granularity can be added if the first two prove insufficient.
- **Enforcing annotations on plain assignments.** Idiomatic Python does not
  annotate them and neither will Liturgy.
- **`anoint`.** Still reserved, still unspent. Chapter IX's argument stands.
