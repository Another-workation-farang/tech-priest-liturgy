# Liturgy: Core Design

**Date:** 2026-08-30
**Status:** Approved
**Scope:** Spec I of III (Core). Specs II (Constructs) and III (Tooling) follow separately.

## Purpose

Liturgy is a superset of Python whose surface syntax is the ritual language
Warhammer 40,000 tech-priests use to address machine spirits.

Two goals, in order:

1. **Near-term:** something genuinely usable. Real scripts, honest tracebacks,
   correct line numbers, an escape hatch to plain Python.
2. **Long-term:** a deep exercise in CPython machinery: import hooks, token
   stream rewriting, AST transformation, traceback remapping. The theme is the
   excuse; the internals are the destination.

Prior art was surveyed. `Mechanicum` (esolangs.org) is a standalone Ad-Mech
esolang with no published implementation and no relation to Python.
`LinguaTechnisTranslator` is a binary encoder with 40K flavour text. No 40K
superset of Python exists. The Perl precedent is Damian Conway's
`Lingua::tlhInganHol::yIghun`, which worked via source filters; Liturgy's
equivalent is the import hook.

## Decomposition

| Spec | Scope | Outcome |
|---|---|---|
| **I. Core** (this doc) | Lexicon, token pass, source map, import hook, curse rendering, `chant` + `commune`, heresy aliases | Write and *debug* alias-only Liturgy comfortably |
| II. Constructs | AST layer: `consecrated`, `litany`, `augur`, `noospheric` | Use constructs Python cannot express |
| III. Tooling | `augur` lint, `prove`, `sanctify`, `transcribe`, remaining verbs | Live in it |

The interface between I and II is the pass list in `transform()` (below).
Spec II appends one pass and changes nothing else.

## The superset promise

Aliasing is one-way at the token level: Liturgy words become Python words.
`print` and `def` therefore still work inside a `.lit` file. The only breakage
is a program using a *Liturgy* word as an identifier.

> **All valid Python is valid Liturgy, except programs that use a Liturgy word
> as an identifier.** Liturgy reserves more words than Python does.

This is stated as a rule rather than handled as a special case: no scope
analysis, no shadowing detection in the token pass. It is the same fine print
Perl's source filters carry.

## Architecture

The load-bearing decision is that the hard logic has **zero coupling to
CPython's import machinery**.

| Module | Purpose | Depends on |
|---|---|---|
| `lexicon.py` | Alias tables; pure data plus lookup | none |
| `sourcemap.py` | `SourceMap`: `(line, col)` <-> `(line, col)` | none |
| `transform.py` | `transform(src) -> (str, SourceMap)` | lexicon, sourcemap |
| `loader.py` | Path hook, `LiturgyLoader`, `chant` execution | transform, curse |
| `curse.py` | Traceback remapping and rendering | sourcemap, lexicon |
| `cli.py` | Verb dispatch and argument parsing | loader, heresy |
| `heresy.py` | Escalating rebuke, state file | none |

`transform` is a pure function from string to string. The bulk of the test
suite therefore runs with no import hook, no subprocess, and no mutation of
`sys.meta_path`.

### Pipeline

```
prayer.lit
   │
   ├─ tokenize ──────────>  token stream
   │                          • AliasPass: rite->def, should->if, render->return
   │                          • INVARIANT: never add or remove a line
   │                          • emits SourceMap (column deltas only)
   │
   ├─ ast.parse ─────────>  AST        [Spec II transforms here]
   │
   ├─ compile ───────────>  code object
   │
   └─ MachineCurse ──────>  traceback themed and column-remapped
```

## Lexicon

Three tables, separated because they carry different risk.

```python
KEYWORDS  = {...}   # Python keywords: reserved, unambiguous
SOFTWORDS = {...}   # builtins
CURSES    = {...}   # exception types
```

### KEYWORDS (complete; every entry in `keyword.kwlist`)

| Liturgy | Python | | Liturgy | Python |
|---|---|---|---|---|
| `Heretical` | `False` | | `should` | `if` |
| `Void` | `None` | | `invoke` | `import` |
| `Sanctioned` | `True` | | `among` | `in` |
| `likewise` | `and` | | `be` | `is` |
| `styled` | `as` | | `servitor` | `lambda` |
| `attest` | `assert` | | `adjacent` | `nonlocal` |
| `remote` | `async` | | `nay` | `not` |
| `attend` | `await` | | `elsewise` | `or` |
| `cease` | `break` | | `abide` | `pass` |
| `pattern` | `class` | | `proclaim` | `raise` |
| `persist` | `continue` | | `render` | `return` |
| `rite` | `def` | | `attempt` | `try` |
| `purge` | `del` | | `whilst` | `while` |
| `lest` | `elif` | | `anointed` | `with` |
| `otherwise` | `else` | | `emanate` | `yield` |
| `curse` | `except` | | `discern` | `match` |
| `regardless` | `finally` | | `wherein` | `case` |
| `foreach` | `for` | | `archetype` | `type` |
| `within` | `from` | | | |
| `universal` | `global` | | | |

### SOFTWORDS (initial set, deliberately small)

`intone`->`print`, `measure`->`len`, `span`->`range`, `unseal`->`open`,
`hearken`->`input`.

Kept minimal in Core. Each addition widens the reserved-word surface, so
growth is a considered act, not a reflex.

### CURSES

`MachineCurse`->`Exception`, `PrimalCurse`->`BaseException`,
`ImpureOffering`->`ValueError`, `PatternMismatch`->`TypeError`,
`LostPattern`->`KeyError`, `BeyondTheManifest`->`IndexError`,
`AbsentAugmetic`->`AttributeError`, `DivisionByTheVoid`->`ZeroDivisionError`,
`ForbiddenLore`->`ImportError`, `RelicNotFound`->`FileNotFoundError`,
`SpiralOfMadness`->`RecursionError`, `TheRiteIsEnded`->`StopIteration`,
`UnknownInvocation`->`NameError`, `MotiveFailure`->`RuntimeError`,
`RiteUnwritten`->`NotImplementedError`.

`TechHeresy` is reserved for Spec II and defined by it.

### Invariants (enforced by tests, not convention)

1. **Bijectivity.** No two Liturgy words map to the same Python word, and no
   Python word is the target of two Liturgy words. Core needs only the forward
   direction, but curse rendering needs the reverse and Spec III's `transcribe`
   needs the whole inverse. A lexicon that has quietly become non-invertible is
   painful to repair later.
2. **Total keyword coverage.** Every entry in the live `keyword.kwlist` has
   exactly one alias. Iterating the runtime list means a new Python release
   fails the suite loudly rather than leaving a keyword silently unthemed.
   Verified against Python 3.14: full coverage, no gaps.

`_` (soft keyword: the `match` wildcard) is deliberately unaliased. It is also
the conventional throwaway binding, and reserving it would cost more than the
theme gains.

## Token pass

### Splicing, not `untokenize`

`tokenize.untokenize` reformats with 2-tuples and reconstructs whitespace
unreliably with 5-tuples. Both destroy the line correspondence everything
downstream depends on.

Every NAME token is single-line by construction, so every substitution is
line-local. Collect substitutions as `(row, col_start, col_end, replacement)`
and splice them into the original lines **right-to-left per line**, so earlier
column offsets remain valid. The line invariant then holds by construction.

Using `tokenize` at all is what gives string-and-comment safety for free: a
NAME token never occurs inside a string literal or comment.

### Minimum Python 3.12

On 3.12+, f-string internals tokenize into real NAME tokens, so `f"{rite}"`
substitutes correctly (that genuinely is code) while surrounding literal text
is `FSTRING_MIDDLE` and untouched. On 3.11 and earlier the entire f-string is
one opaque STRING token and silently does not substitute. Supporting both would
mean two different semantics for the same source. **Requires Python >= 3.12.**

### Context rules (mandatory)

Naive NAME substitution breaks against real libraries. These are correctness
requirements, not polish:

| Rule | Failure it prevents |
|---|---|
| Skip a NAME whose previous significant token is `.` | `template.render()` -> `template.return()`, a syntax error. Any library with `.render()`, `.pattern`, `.span()` breaks instantly. |
| Skip a NAME immediately followed by `=` at paren-depth > 0 | `func(intone=True)` -> `func(print=True)`, silently wrong. |
| Substitute nothing inside `import` / `from` statements except the statement keywords | `from jinja2 import render` -> `... import return`, a syntax error. |

The reservation rule covers identifiers *you* write. These three cover
everyone else's, which you do not control.

### Pass interface

```python
def transform(src: str, passes: Sequence[TokenPass] = DEFAULT_PASSES)
        -> tuple[str, SourceMap]:
```

Core ships `AliasPass`. Spec II appends `CarrierPass`, which desugars construct
headers into valid Python carriers (annotated assignments and `with` blocks)
for its AST pass to rewrite.

## Source map

The line invariant means line fidelity is **free**: line N of the generated
Python is line N of the Liturgy, always. `SourceFileLoader.get_source` already
returns the original `.lit` text, so `linecache` and standard tracebacks show
Liturgy source with no remapping.

The SourceMap therefore exists for exactly one purpose: **column accuracy**,
the `^^^^` carets in 3.11+ fine-grained tracebacks.

Structure: `dict[int, list[Span]]` keyed by line, populated only for lines that
changed, binary search on column, identity fallback for absent lines. Most
lines never appear.

### Rejected alternative: padding

Most Liturgy words are longer than their Python target, so replacements could
be padded with trailing spaces (`if    `), keeping columns byte-identical and
eliminating the SourceMap entirely. It works and produces valid Python.

It costs a lexicon constraint, though, and the constraint already bites: three
entries violate it (`persist`/`continue` is shorter, `be`/`is` and `nay`/`not`
are merely equal), so adopting padding would mean renaming words to satisfy the
transform rather than the theme.

Rejected primarily because Spec II makes it impossible: `consecrated X = 1` ->
`X: __Consecrated__ = 1` *expands*, and no padding shrinks it back. Building
padding in Core means deleting it in Spec II.

## Loader

Registered as a path hook rather than a bare `meta_path` finder:

```python
FileFinder.path_hook((LiturgyLoader, ['.lit']))
```

This is the idiomatic route for a new extension and inherits `FileFinder`'s
directory caching and path handling. Installation inserts ahead of the default
hook, then clears `sys.path_importer_cache` and calls
`importlib.invalidate_caches()`. Omitting either makes the hook appear inert.

`LiturgyLoader` subclasses `SourceFileLoader` and overrides exactly one method,
`source_to_code`, which runs `transform()` and compiles the result.
`get_source` is deliberately **not** overridden; the inherited implementation
already returns original `.lit` text.

### Bytecode caching

Inheriting `SourceFileLoader` gives `__pycache__` for free, but a cached `.pyc`
cannot carry a SourceMap. Rather than persisting or disabling it, the map is
**computed lazily, only when a curse is being rendered.** Exceptions are rare
and re-transforming one file is negligible. The map is never needed at import
time, so caching and mapping never interact.

### `chant` execution

`chant` needs `__main__` semantics, which the import system will not provide.
It reads the file, registers the original source in `linecache`, transforms,
compiles, and execs into a fresh namespace with `__name__ = "__main__"` and
`__file__` set to the `.lit` path.

## Curse rendering

A `sys.excepthook` and matching `threading.excepthook` that theme **only frames
originating in `.lit` files**. Frames from libraries render normally, so a
traceback through third-party code stays readable.

```
++ MACHINE CURSE ++
   the rite was broken at prayer.lit, line 12, in rite invoke_spirit
       render tome / Void
                     ^^^^
   DivisionByTheVoid: the Void accepts no dividend
++ the machine spirit is displeased ++
```

The exception name comes from inverting `CURSES`; the caret column comes from
the SourceMap.

### Robustness rules

- The hook wraps everything in `try/except` and falls back to
  `sys.__excepthook__`. **An excepthook that raises destroys the original
  error**: the worst available failure mode.
- If the `.lit` file has moved or changed since import, the map is
  unavailable: degrade to an unmapped traceback rather than render wrong
  carets.
- `--profane` (and `LITURGY_PROFANE=1`) emits a plain traceback, for pasting
  into bug reports.

## CLI

Core ships two verbs plus their heretical aliases.

| Verb | Alias | Action |
|---|---|---|
| `chant <file.lit> [args...]` | `run` | Execute |
| `commune` | `repl` | Interactive session |

The full verb surface (`augur`, `prove`, `sanctify`, `forge`, `consecrate`,
`purge`, `anoint`, `transcribe`) is specified in Spec III. Core reserves the
names.

Two names are reused across namespaces by design, and the docs must be explicit
about it: `augur` is both a Spec II source construct (preconditions) and a
Spec III CLI verb (lint); `purge` is both a Spec I keyword alias for `del` and a
Spec III CLI verb (clear caches). Source keywords and CLI verbs never collide
mechanically, but the overlap will confuse readers if left unremarked.

### `commune`

Subclasses `code.InteractiveConsole`, transforming in `runsource` before
compiling. The wrinkle is incomplete input: `tokenize` raises on an unterminated
block, and the REPL must read that as "keep reading," not as an error: a
tokenize failure at end-of-input becomes the `None` return that signals
continuation. Getting this wrong makes multi-line rites impossible to type, so
it carries dedicated tests.

### Heresy machinery

Invoking a mundane alias works, and rebukes:

```
$ liturgy run prayer.lit
++ TECH-HERESY DETECTED ++
++ this rite is named CHANT. the omission is noted. ++
```

- Written to **stderr**, never stdout, so piped output stays clean.
- **Exit code unchanged.** Heresy is a moral failing, not a runtime failure.
- Silenced by `LITURGY_PIOUS=0` or `--absolved`, so CI logs are not flooded.
- The rebuke escalates across invocations (noted -> recorded in your permanent
  record -> the Inquisition has been notified) via a counter in a small JSON
  state file.
- If the state file cannot be written, fail silently. The CLI must never break
  over the joke.

## Testing

TDD throughout. Three tiers mirroring the module boundaries.

### 1. Transform units: the bulk, no import machinery

- Table-driven across every lexicon entry.
- **Property: identity.** Python source containing no Liturgy words transforms
  to itself, byte for byte.
- **Property: parseability.** Transform output always `ast.parse`s.
- **Property: round-trip.** Take real Python files, mechanically reverse-alias
  them into Liturgy, transform back, assert equality. Exercises bijectivity and
  the entire lexicon at once.

### 2. Source map units

- Every substitution maps back to its originating token.
- Mapping is monotonic within a line.
- Absent lines resolve by identity.

### 3. Integration

- `.lit` files in `tmp_path`, hook installed, imports asserted.
- Traceback tests raise from a known line and assert the rendered curse points
  at the correct `.lit` line **and** caret column.
- Subprocess tests for both verbs, the rebuke on stderr, and the unchanged
  exit code.
- Excepthook failure injection: a corrupted map must still produce the original
  exception.

### Named regressions

The three context rules each get a permanent, named test:
`template.render()`, `func(intone=True)`, `from jinja2 import render`. These are
the failures that would make Liturgy unusable against real libraries.

## Out of scope for Core

- The four constructs (`consecrated`, `litany`, `augur`, `noospheric`): Spec II.
- Remaining CLI verbs: Spec III.
- `transcribe` (Python -> Liturgy): Spec III; bijectivity is maintained now so
  it stays possible.
- A PEP 263 codec. Rejected outright: a codec is text-to-text and runs before
  the parser, so it can never perform Spec II's AST work. Offering one for the
  alias-only subset would create a second entry point that silently supports
  fewer features.
- A user-extensible lexicon (per-forge dialects). Tables stay pure data so this
  remains easy, but nothing in Core reads alias definitions from disk.
