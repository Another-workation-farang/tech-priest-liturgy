# Liturgy Tooling — Design

**Date:** 2026-08-31
**Status:** Approved
**Scope:** Spec III of III. Specs I (Core) and II (Constructs) are built and merged.

## Purpose

Specs I and II made Liturgy a language. Spec III makes it usable on code you
did not write in it, and catches the one class of mistake the compiler cannot.

Three verbs:

| Verb | What it does |
|---|---|
| `augur` | Read a litany for faults without chanting it |
| `transcribe` | Render a Python file into Liturgy |
| `purge` | Clear generated caches |

## Five reserved verbs are NOT built, deliberately

Spec I reserved eight CLI verb names so nothing else would claim them. That was
right. Building all eight because the names exist would be backwards.

- **`prove`** (test runner) — `pytest` already works on `.lit` files once the
  import hook is installed. A themed wrapper adds flavour, not capability.
  Deferred.
- **`sanctify`** (formatter) — a real formatter is a large, fiddly project, and
  the value for a toy language is low. Deferred.
- **`forge`, `consecrate`, `anoint`** — reserved as flavour with no feature
  behind them. They stay reserved and undefined. Inventing purposes for them
  during a spec is how features nobody needs get built.

The names remain in `RESERVED_VERBS`, so a later spec still has nowhere to
collide.

## The collision rule

Both `augur` and `transcribe` need one primitive: **find reserved words used as
identifiers**. It lives in one place, `collisions.py`, so the two verbs cannot
drift apart about what counts.

### What a collision is

A collision is **a binding whose source-language name is reserved** — not
merely a reserved word appearing somewhere. Spec I's three exemptions mean
`template.render()`, `f(intone=1)` and `from jinja2 import render` are all
correct code, and none of them is a collision.

Binding analysis reuses `rewrite._stored_names`, which Spec II hardened to
cover assignment, augmented assignment, walrus, `for` targets, `with ... as`,
`del`, import aliases, `except ... as`, match captures, and `def`/`class`
names. Reimplementing that would be a second definition of the same rule, and
this project has been bitten four separate times by two things that should
agree quietly drifting apart.

### Two paths, because the file types differ

- **`.lit`** — run `transform()`, parse the generated Python, walk
  `_stored_names`, then map each binding's position back through the
  `SourceMap` to recover the word the author actually typed. If that word was
  substituted, it is a collision.
- **`.py`** — parse directly, walk `_stored_names`, and flag any bound name
  that is a `LEXICON` key. This answers a different question — *would this
  transcribe?* — with the same machinery. `span = 5` is fine Python, survives
  `to_liturgy` untouched, and becomes `range = 5` when compiled.

### Quiet and loud

Each collision records which it is:

- **Quiet** — the substitution target is not a Python keyword, so the file
  compiles and silently shadows. `span`, `measure`, `unseal`, `hearken`, and
  every curse name (`MachineCurse = 5` becomes `Exception = 5`, which is legal).
  These are `augur`'s reason to exist.
- **Loud** — the target is a Python keyword, so compilation fails anyway.
  `augur` still reports them, earlier and with a better message than the
  compiler gives.

### A known imprecision, stated rather than hidden

`_stored_names` yields the *statement* node for `except ... as` and for import
aliases, because `ExceptHandler.name` is a plain string and carries no position
of its own. For those two shapes the reported line is exact but the column is
the statement's, not the name's. Acceptable for a linter; recorded so nobody
later reads it as a bug.

## Architecture

| File | Responsibility |
|---|---|
| `src/liturgy/collisions.py` (new) | `Collision`, `find_collisions(src, filename, *, liturgy: bool)`. The one definition. `liturgy=True` takes the transform-and-map-back path; `False` parses directly. The caller decides from the file extension rather than the function sniffing it, so a caller with source but no filename still works. |
| `src/liturgy/reverse.py` (new) | `to_liturgy(src)`, **promoted from `tests/_reverse.py`**. |
| `src/liturgy/tooling.py` (new) | The three verb implementations, thin over the modules above. |
| `src/liturgy/cli.py` (modify) | Three verbs move from `RESERVED_VERBS` into real subparsers. |

Module dependency order gains: `collisions` and `reverse` sit above `rewrite`
and `transform`; `tooling` above both and below `cli`.

### On promoting the reverse pass

Spec II deliberately moved `_reverse.py` **out** of the shipped wheel, on the
grounds that test-only code should not ship. Spec III reverses that, and
correctly: under this spec it stops being a test double and becomes the
feature. The round-trip property test then imports the shipped module instead
of a private twin, which makes that test stronger rather than weaker.

## The verbs

### augur

```
liturgy augur [--plain] PATH...
```

Accepts files or directories, recursing for `.lit` and `.py`.

It checks exactly two things, and does not grow into a general linter. Unused
imports, shadowed names, complexity — that is ruff's job, ruff is better at it,
and Liturgy has no business competing.

1. **Compile the file without running it.** That surfaces everything the
   compiler catches: syntax errors, `TechHeresy`, construct misuse. Because it
   is the same code path, `augur` can never disagree with `chant`.
2. **Scan for collisions the compiler cannot catch.** This is its unique
   competence.

On a `.py` file only the second check runs.

**When the two checks conflict.** The collision scan needs the `SourceMap`,
which needs `transform()` to succeed. A `.lit` file that will not tokenise has
no map, so there is nothing to scan against. In that case `augur` reports the
compile failure alone and says so explicitly — `omens unread: the litany does
not tokenise` — rather than silently reporting zero collisions, which would read
as a clean bill of health. A file that tokenises but fails later (a
`TechHeresy`, a parse error) still gets both checks, because the map exists.

**Exit codes:** `0` clean, `1` findings. The convention CI expects.

**Output** is themed by default:

```
++ THE OMENS ARE TROUBLED ++
   prayer.lit, line 3
       span = "text range"
       ^^^^
   span is reserved; it becomes range
```

`--plain` emits `file:line:col: message`, the format every editor and CI
system already parses. This mirrors the `--profane` escape hatch Spec I
established for curses, so it is a pattern users have already met.

### transcribe

```
liturgy transcribe SOURCE.py [-o OUT.lit]
```

Collisions are checked first. **Any collision refuses the whole file**, listing
every one, exit `1`. A half-transcribed file that looks fine and breaks later is
the worst available outcome; refusing is honest, and the fix — rename, retry —
is the author's to make. `augur` on the same `.py` file gives the identical
report before you commit to it.

Clean input is transcribed to `-o` or to stdout.

**It verifies its own output before writing.** `transform()` is run over the
generated Liturgy and the result compared to the input; a mismatch refuses
rather than writing a file that lies about being correct. This is the
round-trip property test applied to one real file, so the machinery already
exists and the check costs nothing.

### purge

```
liturgy purge [--heresies]
```

Removes `__pycache__` directories beneath the working directory, printing each.
`--heresies` also clears the heresy escalation state file.

**It is the only destructive verb, so it is guarded.** It refuses unless the
working directory contains at least one `.lit` file — a recursive delete in the
wrong directory is a bad afternoon — and it never follows symlinks.

That guard protects the recursive part. `--heresies` removes one known file at
a fixed path outside the project, so the guard is irrelevant to it; it is
reported by full path before deletion so there is no doubt what went.

## Testing

Three tiers, matching Specs I and II.

### 1. Collision units — pure, no CLI

- Every binding shape `_stored_names` knows, in both `.lit` and `.py` form.
- Quiet-versus-loud classification, including a curse name as a quiet case.
- Position accuracy, including the two shapes documented above as
  column-approximate.

### 2. Named regressions

Permanent, in this project's tradition. These three shapes caused a Critical in
Spec I's final review and must never be reported as collisions:

- `template.render()` — attribute position
- `f(intone=1)` — keyword-argument position
- `from jinja2 import render` — import target

### 3. Integration — each verb through the real CLI

- `augur`: exit codes, both output formats, a directory argument, a `.py`
  argument.
- `transcribe`: a clean file round-trips; a colliding file is refused with
  every collision listed; the self-check catches a deliberately broken reverse
  pass.
- `purge`: removes what it says, and refuses outside a Liturgy project.

### 4. Corpus cross-check

Point `augur --plain` at the stdlib corpus the round-trip sweep already uses.
Every file `augur` flags should be exactly a file the sweep skips. Two
independent implementations of "this file uses a Liturgy word as an identifier"
agreeing is a strong check on both — and the sweep is what caught the Critical
that hand-written tests missed in Spec I.

## Documentation

README and both tome copies: a new chapter for the three verbs, `augur`'s
quiet-collision check named as the answer to Chapter VII's "the quiet ones",
and Chapter IX updated to record which five verbs remain unbuilt and why.

## Out of scope

- `prove`, `sanctify`, `forge`, `consecrate`, `anoint` — see above.
- Any linting beyond the reservation rule.
- Editor integration. `--plain` emits the standard format; wiring it into an
  editor is the user's business, not a feature to build.
