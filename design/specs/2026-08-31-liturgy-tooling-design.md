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
merely a reserved word appearing somewhere. `template.render()` and
`f(intone=1)` are correct code and are not collisions: neither binds anything.

`within jinja2 invoke render` **is** a collision, and this corrects an earlier
draft of this spec which listed it as an exemption. Spec I's third rule stops
the *substitution* firing on an import target, without which the statement would
become `import return` and fail to compile. But the resulting binding is still
`render`, and every later *reference* to it substitutes to `return`:

    within json invoke loads styled render
    intone(render("{}"))

compiles to `from json import loads as render` / `print(return("{}"))` — a
syntax error. The import brings in a name nothing can reach. The exemption is
about what the transform does; the collision is about what the resulting program
can do, and the two are not in conflict.

### Two clauses

A binding at line L collides if either holds:

- **(a) A substitution at line L produced the bound name.** The author wrote a
  Liturgy word and it became a Python binding — `span = 5` becoming `range = 5`.
- **(b) The bound name is itself a `LEXICON` key.** The binding survived
  unsubstituted, because an exemption protected it, but every reference to it
  will substitute — the import case above.

Clause (b) alone is the whole `.py` rule, since a `.py` file has no
substitutions. So the two file types share one implementation with one branch
rather than two separate scans.

Binding analysis reuses `rewrite._stored_names`, which Spec II hardened to
cover assignment, augmented assignment, walrus, `for` targets, `with ... as`,
`del`, import aliases, `except ... as`, match captures, and `def`/`class`
names. Reimplementing that would be a second definition of the same rule, and
this project has been bitten four separate times by two things that should
agree quietly drifting apart.

### Two paths, because the file types differ

- **`.lit`** — run `transform()` and `alias_pass()`, parse the generated
  Python, walk `_stored_names`, and apply both clauses.
- **`.py`** — parse directly and apply clause (b) only. This answers a different
  question — *would this transcribe?* — with the same code. `span = 5` is fine
  Python, survives `to_liturgy` untouched, and becomes `range = 5` when
  compiled.

### Quiet and loud

Each collision records which it is:

- **Quiet** — the substitution target is not a Python keyword, so the file
  compiles and silently shadows. `span`, `measure`, `unseal`, `hearken`, and
  every curse name (`MachineCurse = 5` becomes `Exception = 5`, which is legal).
  These are `augur`'s reason to exist.
- **Loud** — the target is a Python keyword, so compilation fails anyway.
  `augur` still reports them, earlier and with a better message than the
  compiler gives.

### Where the position comes from

Not from the AST node. `_stored_names` yields the *statement* node for `for`,
`def`, `class`, `except ... as` and imports, so its column is the statement's
start, not the bound name's. A prototype that read the word at that column
produced five false negatives.

Clause (a) instead takes its position straight from the `Substitution` the alias
pass already produced — exact, and already in Liturgy coordinates, so nothing
needs mapping back through the `SourceMap` at all. Clause (b) has no
substitution to draw on and falls back to the node's column, which for the five
statement-node shapes is the statement's start. Line is always exact; column is
approximate only in clause (b), and only for those shapes.

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

Accepts files or directories, recursing for `.lit` and `.py`. *(Refined
post-review: the walk prunes dot-directories, `__pycache__` and anything
holding a `pyvenv.cfg` — a vendored virtual environment drowned real findings
— while a directory named directly is always read, and overlapping arguments
report each finding once.)*

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
as a clean bill of health. A file that tokenises but fails later — a
`TechHeresy`, a parse error — gets the compile failure alone as well: the
collision scan runs through the same `transform()`, so the failure arrives
before any collision does. Fixing the heresy and re-running is what surfaces
the collisions, and the exit code is `1` either way, so nothing in CI turns
on the difference.

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

Permanent, in this project's tradition. The first two shapes caused a Critical
in Spec I's final review and must never be reported as collisions, because
neither binds anything:

- `template.render()` — attribute position
- `f(intone=1)` — keyword-argument position

And the counterpart, which must always be reported, because it does bind:

- `within jinja2 invoke render` — the import compiles, and binds a name every
  later reference substitutes away from

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
