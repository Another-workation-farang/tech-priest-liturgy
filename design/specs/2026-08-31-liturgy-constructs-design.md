# Liturgy Constructs: Design

**Date:** 2026-08-31
**Status:** Approved
**Scope:** Spec II of III. Spec I (Core) is built and merged; Spec III (Tooling) follows.

## Purpose

Spec I made Liturgy a faithful reskin of Python: every keyword aliased, nothing
added. Spec II adds three constructs Python cannot express, so that Liturgy is
a superset in substance and not only in spelling.

| Construct | What it does | Why Python cannot |
|---|---|---|
| `consecrated` | A binding that may not be rebound | Python has no constants, only the ALL_CAPS honour system |
| `litany` | A block re-attempted on named failures | Everyone hand-rolls retry, usually wrongly |
| `augur` | Preconditions read before a rite's body | `assert` vanishes under `-O`, so it cannot guard a boundary |

### `noospheric` is cut

Spec I designed a fourth construct: a binding placed in a process-wide registry.
It is dropped, for two independent reasons.

It is a service locator, a pattern with well-known costs, which was flagged when
it was chosen. And with no runtime module (below), it has nowhere clean to live:
its desugaring would have to hide state on `builtins` and turn every read into a
dict lookup through it. Neither reason alone would be decisive. Together they
are.

## The governing constraint: no runtime

**Every construct desugars into self-contained generated Python.** Liturgy ships
no helper module, and the generated code imports nothing from Liturgy.

This is a deliberate trade. What it buys: a `.lit` file compiles to Python that
stands alone, nothing has to be installed alongside it, tracebacks contain no
Liturgy frames, and Spec III's `transcribe` stays coherent. What it costs is
stated where it bites: `consecrated` cannot be enforced at runtime, and a
failed augury cannot raise a Liturgy-specific class.

Where the cost was too high, the feature was cut rather than the constraint
bent. That is what happened to `noospheric`.

## Architecture

### Where the AST work lives

Spec I's `transform()` is text-to-text and the whole test suite is built on
that. It stays that way. A new function layers on top:

```python
def compile_litany(src: str, filename: str) -> types.CodeType
```

```
prayer.lit
   │
   ├─ transform() ───────>  Python text + SourceMap
   │                          • AliasPass      (Spec I)
   │                          • CarrierPass    (Spec II, appended)
   │                          • INVARIANT: never add or remove a line
   │
   ├─ ast.parse ─────────>  AST
   │                          • ConstructPass  (Spec II)
   │                          • restructures freely; text is not touched
   │
   └─ compile ───────────>  code object
```

`loader.LiturgyLoader.source_to_code`, `loader.chant` and `commune` change from
`compile(transform(...)[0], ...)` to `compile_litany(...)`. Nothing else moves.

**Rejected: doing it all at the token level.** `litany` must expand into a `for`
wrapping a `try`, which is more lines than it started with. The line invariant
forbids that outright. This is why Spec I put an AST stage in the pipeline.

**Rejected: extending `transform` to return an AST or code object.** It would
muddy the one clean function `_reverse`, the round-trip property and most of the
suite depend on, for no gain.

### Carriers

The carrier pass rewrites construct headers **in place, on one line**, into
valid Python. The AST pass then restructures without touching text at all, so
the line invariant is preserved textually and the AST pass is free.

| Surface | Carrier (same line) | AST pass produces |
|---|---|---|
| `consecrated PORT = 8080` | `PORT: __consecrated__ = 8080` | plain assign, plus compile-time rebinding checks |
| `litany(thrice, resting=2, curse=E):` | `with __litany__(thrice, resting=2, curse=E):` | a `for`/`try`/`break` retry loop |
| `augur:` | `with __augur__():` | one `if not cond: raise` per line |

Annotated assignments and `with` blocks are the carriers because both parse,
both are trivially addressable as AST nodes, and `__consecrated__`/`__litany__`
/`__augur__` are names nobody writes by accident.

*(Correction, post-review: "nobody writes by accident" was not enough. A
program that does write one, deliberately or via generated code, was
indistinguishable from a carrier, and `with __litany__(...) styled x:` was
silently rewritten into the retry loop, losing its binding. The carrier names,
and the `__liturgy_` bookkeeping prefix, are now reserved outright: the
carrier pass rejects any user-written occurrence outside attribute position
with a loud heresy, `augur` reports a `.py` binding one, and `transcribe`
compiles its output as a backstop.)*

### Why `litany`'s header is call-shaped

A prose header (`litany thrice, resting 2, curse TimeoutError:`) needs a real
mini-parser in the carrier pass to find where each expression begins and ends.
The call-shaped form needs a single token swap, `litany` to `with __litany__`,
and `curse=` survives untouched because Spec I's Rule 2 already protects
keyword-argument names.

`thrice` and `twice` substitute to `3` and `2`, so `litany(thrice, ...)` reads
as liturgy while `litany(retries, ...)` still works with a variable.

They cannot be ordinary lexicon entries. `SOFTWORDS` targets are validated with
`hasattr(builtins, target)` and `KEYWORDS` targets against `keyword.kwlist`;
`"3"` is neither a builtin nor a keyword, so either table would fail its own
invariant. They go in a fourth table, `NUMERALS`, which the alias pass
substitutes alongside the others but which is excluded from the builtin and
keyword validity checks. Bijectivity still applies to it.

Being alias-pass entries, they substitute **everywhere**, not only in a litany
header: `x = thrice` is `x = 3`. That is the intended reading of a numeral word,
and it is why they count toward the reservation set.

### Locations for synthesised nodes

The AST pass adds `for`, `try`, `if` and `raise` nodes that exist in no source
line. Every one gets `ast.copy_location` from its construct header. A traceback
through a desugared `litany` therefore points at the `litany` line, while the
body's own nodes keep their original locations untouched.

A test asserts that every node in the output tree has a position. A node without
one is a traceback without a line.

## The constructs

### consecrated

```
consecrated OMNISSIAH_PORT = 8080
```

Rebinding is rejected **at compile time** by the AST pass, within the scope
where the name was consecrated. The check covers assignment, augmented
assignment, walrus, `for` targets, `with ... as`, `del`, `import ... as`, and
unpacking targets.

Two further cases are rejected:

- **A second `consecrated` of the same name in the same scope.** Two
  declarations are a rebinding written twice.
- **A `consecrated` inside a loop body.** It rebinds on every iteration while
  looking like a single declaration.

Valid in any scope. Function scope is where the check is most complete, since
every rebinding is visible within the function.

**Limitation, stated plainly.** What the compiler cannot see, it cannot stop:
`setattr(mod, "PORT", x)`, `globals()["PORT"] = x`, assignment through the
module object from another module, and `exec` all get through. This is
enforcement, not a guarantee. The documentation says so in those words.

### litany

```
litany(thrice, resting=2, curse=TimeoutError):
    response = entreat(url)
```

- The first argument is the **total attempts**, not the number of retries.
- `resting=` is optional, in seconds, and defaults to no pause at all, so the
  common case emits no timing code whatsoever. When given, the pause is
  `__import__("time").sleep(...)`, which keeps the generated module standalone.
- `curse=` is **required and keyword-only**, and names an exception type or a
  tuple of them. Passing it positionally is a `TechHeresy`, so the filter can
  never be confused with the count.
  Nothing is caught implicitly. A retry block that catches everything will
  cheerfully retry a `TypeError` three times and re-raise it late; requiring the
  filter means the thing you typed is the thing you meant.

Three properties the desugaring must have:

1. **The count is evaluated exactly once**, bound to a temporary before the
   loop. Otherwise `litany(roll(), ...)` rolls twice and compares against a
   different number than it looped over.
2. **`cease` and `persist` at the top level of a litany body are rejected at
   compile time.** They would bind to the invisible retry loop rather than the
   loop the author meant: a silent wrong-behaviour bug with no plausible way to
   debug it. Nested inside a real loop within the body they are fine and left
   alone. `render` needs no special handling: returning from the function exits
   the retry naturally.
3. **A count below 1 must not silently skip the body.** Rejected at compile time
   when the count is a literal; guarded at runtime when it is an expression.

### augur

```
rite divide(a, b):
    augur:
        b be nay Void
        b != 0
    render a / b
```

Bare expressions, one per line. Each becomes `if not (expr): raise ...`.

Valid **only as the opening statement of a rite**, where a leading docstring
does not count as a statement for this purpose: a rite may have its docstring
and then its augury, which is the order anyone would write them in. That
restriction is what makes it a precondition rather than a scattered check, and
it is enforced.

It is a contract, not an assertion: it desugars to a real `if`/`raise` and runs
under `-O`. A precondition that vanishes in production cannot guard a trust
boundary, which is the only place one is worth writing.

**The message quotes the Liturgy source, not the generated Python**: `b be nay
Void`, not `b is not None`. The AST pass has the node's line and columns, the
SourceMap maps them back, and the original line is sliced. Where the slice
fails, `ast.unparse` is the fallback.

**What it raises, and why not `IllOmen`.** A Liturgy-specific exception class
would have to be importable at the raise site, and pure desugaring means the
generated module imports nothing from Liturgy: the same wall that stopped
`noospheric`. A failed augury therefore raises **`ImpureOffering`**
(`ValueError`) carrying the themed message. It needs no import, it is catchable
under a name already in the lexicon, and it is defensible on its own terms: the
caller made an impure offering.

## Errors

`TechHeresy(SyntaxError)` is the single compile-time rejection type, covering
every violation above. It lives in `constructs.py` and is raised only by the
compiler, never by generated code, which is why it *can* be a real class where
`IllOmen` could not.

It sets `filename`, `lineno`, `offset` and `text`, which is everything Spec I's
syntax-error rendering needs to give it file, line, source and caret without new
work. It is importable, so `curse TechHeresy` works when catching a failed
import.

`UnfinishedLitany` stays in `transform.py` where Spec I put it. Two error
classes in two modules is slightly untidy; refactoring Spec I code that is not
otherwise being touched costs more than it buys.

## The reservation set grows

`consecrated`, `litany`, `augur`, `thrice` and `twice` become reserved. The
documented count goes from 58 to 63.

The reserved set is no longer just `LEXICON`. `thrice` and `twice` are in
`NUMERALS`; `consecrated`, `litany` and `augur` are construct keywords the
carrier pass recognises and are in **no** alias table at all, since they map to
no Python word. A single `RESERVED` frozenset (the union of `LEXICON`,
`NUMERALS` and the construct keywords) becomes the one place that answers "is
this word taken", and every consumer uses it: the corpus sweep's skip logic, the
documented count, and Spec III's `augur` lint when it arrives.

**The carrier pass must fire only in statement position.** `litany(3)` in an
expression is somebody's function call; only `litany(...)` beginning a statement
whose logical line ends in `:` is a block header. The same holds for `augur:`.

This is the exact shape of the Critical finding in Spec I's final review, where
a rule fired on a name without checking its position and turned
`chain.invoke(x)` into `chain.import(x)`. It was found only by sweeping real
code. Spec II therefore inherits the same defences: named regression tests, and
the stdlib corpus sweep extended with the five new words.

## Implications for `transcribe` (Spec III)

Nothing breaks, but the boundary is worth fixing now: Python has no
`consecrated`, so `transcribe` can only ever emit alias-only Liturgy. Spec II's
constructs are write-only from Liturgy's side.

The round-trip property test stays valid, because reverse-aliased Python never
produces a construct header in statement position.

## Testing

Three tiers, matching Spec I's structure because it worked.

### 1. Carrier pass units: pure text-to-text, no AST, no import machinery

- Each construct's header rewrites correctly.
- The line invariant holds for every rewrite.
- Occurrences outside statement position are left untouched.

### 2. AST pass units

- Parse a carrier form, run `ConstructPass`, `ast.unparse` and assert the shape.
- **Every node in the output tree has a position.** Asserted over the whole
  tree, not sampled.
- The count temporary is bound once.

### 3. Integration: real `.lit` files via `chant` and via import

- A litany retries the right number of times and rests the right amount.
- A consecrated rebinding is rejected, with file, line and caret in the curse.
- A failed augury raises `ImpureOffering` carrying the Liturgy source text.

### Named regressions

Permanent, named tests, in the spirit of Spec I's:

- `litany(3)` as an ordinary function call in expression position is untouched.
- A user function named `augur`, called as `augur()`, is untouched.
- `cease` at the top level of a litany body is rejected.
- `consecrated` inside a loop body is rejected.

### Corpus and regression floor

The stdlib corpus sweep gains the five new reserved words in its skip logic and
remains the backstop for what hand-written tests miss. All 359 existing tests
must pass; `DEFAULT_PASSES` changing is the risk, and the round-trip property is
the tripwire.

## Documentation

In scope, and both copies, since the tome ships in two:

- `README.md`: the "not yet built" section loses three of its four entries.
- `docs/LIBER-LITURGIAE.md` and `docs/liber-liturgiae.html`: Chapter IX loses
  three entries; Chapters III to VII gain the new words, the new reserved count
  of 63, and the `consecrated` enforcement limitation stated plainly.

## Out of scope

- `noospheric`: cut, with reasons recorded above. Not deferred; a later spec
  wanting a process-wide registry should design it fresh against whatever
  constraints hold then.
- Spec III's verbs, including `augur` as a lint command. The construct and the
  verb share a name and do not collide: one is a word in a litany, the other a
  word typed at a terminal.
- Any Liturgy runtime module. If a future construct genuinely requires one, that
  is a decision to reopen deliberately, not to arrive at by accident.
