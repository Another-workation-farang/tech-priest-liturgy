# LIBER LITURGIAE

### The Rites of the Machine Tongue, Set Down for Adepts of the Second Class

*Transcribed from the pattern-archives of Forge World Tertius Minoris.*
*Bear it with you. Do not lend it. Do not annotate it in ink.*

> **Canonical source.** This file is the authority. A published Artifact
> renders the same text as a page; if the two disagree, this one is right, and
> the other needs the same edit.

---

## Chapter I — Of the Machine Tongue

*The Omnissiah does not speak as men speak. He speaks in current and in
interrupt, and the adept who would be understood must shape his mouth to the
machine's grammar rather than demand the machine shape itself to his.*

*Liturgy is that shaping. It is not a new tongue. It is the old tongue,
spoken with the proper reverence.*

Liturgy is a superset of Python. Every keyword has a ritual spelling: `if` is
`should`, `def` is `rite`, `return` is `render`. A `.lit` file is tokenized,
its ritual words are substituted back to their Python spellings, and the
result is compiled exactly as a `.py` file would be. Underneath, it is
Python — the same objects, the same scoping, the same control flow, the same
standard library.

### The promise, and its fine print

> **All valid Python is valid Liturgy, except programs that use a Liturgy word
> as an identifier.** Liturgy reserves more words than Python does.

`print` still works in a `.lit` file. So does `def`. Substitution runs one
way — ritual spelling to Python spelling — so the Python spellings are never
touched. What breaks is a program that names a variable `rite`, or `render`,
or `curse`.

This is the same fine print Perl's source filters carried. It is stated as a
rule rather than worked around, because working around it would require the
transform to understand scope, and it does not need to.

Chapter VII treats the consequences in full. Read it before you name anything.

---

## Chapter II — The Rite of Installation

*Before the machine will hear you, it must be told that you exist.*

Liturgy requires **Python 3.12 or later**. This is not deference to fashion.
On 3.12 and after, PEP 701 causes the internals of an f-string to tokenize as
real name tokens, so `f"{measure(x)}"` substitutes correctly. On 3.11 and
earlier the entire f-string is a single opaque string token and the
substitution silently does not happen. Supporting both would mean two
different meanings for identical source, which is worse than supporting one.

```
$ pipx install .
```

### chant — to execute a litany

```
$ liturgy chant hello.lit
Ave Omnissiah
```

`chant` runs a `.lit` file with `__main__` semantics, the way `python file.py`
runs a Python one. Arguments after the filename are passed to the prayer.

### commune — to hold converse

```
$ liturgy commune
++ COMMUNION ESTABLISHED ++
>>> rite fib(n):
...     should n < 2:
...         render n
...     render fib(n-1) + fib(n-2)
...
>>> intone([fib(i) foreach i among span(8)])
[0, 1, 1, 2, 3, 5, 8, 13]
```

An interactive session. It knows the difference between a litany you have not
finished typing and one you have typed wrongly, and will keep prompting for
the first while reporting the second.

### Importing

A `.lit` file imports like any module once the hook is installed, which both
verbs do for you. Liturgy may import Python; Python may import Liturgy.

```
within reliquary invoke bless
invoke json
```

---

## Chapter III — The Lesser Rites

*Thirty-eight words. The adept commits them to memory, or to a wafer, or to
an implant. There is no dishonour in the wafer.*

Every Python keyword has exactly one ritual spelling. A test iterates the live
`keyword.kwlist` on every run, so a future Python release that adds a keyword
fails the suite loudly rather than leaving it unthemed.

### Binding and naming

| Liturgy | Python | |
|---|---|---|
| `rite` | `def` | declare a rite |
| `pattern` | `class` | declare a pattern |
| `servitor` | `lambda` | a rite too small to name |
| `styled` | `as` | bind under another name |
| `universal` | `global` | bind at module scope |
| `adjacent` | `nonlocal` | bind in the enclosing scope |
| `archetype` | `type` | declare a type alias |

### Truth and the Void

| Liturgy | Python |
|---|---|
| `Sanctioned` | `True` |
| `Heretical` | `False` |
| `Void` | `None` |

### Branching

| Liturgy | Python |
|---|---|
| `should` | `if` |
| `lest` | `elif` |
| `otherwise` | `else` |
| `discern` | `match` |
| `wherein` | `case` |

### Iteration

| Liturgy | Python |
|---|---|
| `foreach` | `for` |
| `among` | `in` |
| `whilst` | `while` |
| `cease` | `break` |
| `persist` | `continue` |

### Rendering and emanation

| Liturgy | Python |
|---|---|
| `render` | `return` |
| `emanate` | `yield` |

### Logic

| Liturgy | Python |
|---|---|
| `likewise` | `and` |
| `elsewise` | `or` |
| `nay` | `not` |
| `be` | `is` |

### Warding

| Liturgy | Python |
|---|---|
| `attempt` | `try` |
| `curse` | `except` |
| `regardless` | `finally` |
| `proclaim` | `raise` |
| `attest` | `assert` |

### Invocation

| Liturgy | Python |
|---|---|
| `invoke` | `import` |
| `within` | `from` |

### Rites of the distant machine

| Liturgy | Python |
|---|---|
| `remote` | `async` |
| `attend` | `await` |

### Lesser observances

| Liturgy | Python |
|---|---|
| `abide` | `pass` |
| `purge` | `del` |
| `anointed` | `with` |

### Numeral words

Two counting words, spelled out because they name an attempt count, not a
value in the data a rite works on:

| Liturgy | Python |
|---|---|
| `twice` | `2` |
| `thrice` | `3` |

### A worked litany

```
pattern Reliquary:
    rite __init__(self, relics):
        self.relics = relics

    rite blessed(self):
        render [r foreach r among self.relics should r.startswith("sanctified")]


r = Reliquary(["sanctified cog", "profane wire", "sanctified oil"])
intone(measure(r.blessed()))
```

```
$ liturgy chant reliquary.lit
2
```

---

## Chapter IV — Sanctioned Builtins

*Five only. The Cult does not multiply names without cause, and every name
taken is a name the adept may no longer use for his own purposes.*

| Liturgy | Python |
|---|---|
| `intone` | `print` |
| `measure` | `len` |
| `span` | `range` |
| `unseal` | `open` |
| `hearken` | `input` |

The set is deliberately small. Each addition widens the reserved-word surface
described in Chapter VII, so growth is a considered act rather than a reflex.

---

## Chapter V — Of Curses and Their Reading

*When the machine spirit is displeased it does not fall silent. It tells you
precisely what offended it, in what rite, and at what word. The adept who does
not read the curse has wasted the machine's courtesy.*

### The names of curses

| Liturgy | Python |
|---|---|
| `PrimalCurse` | `BaseException` |
| `MachineCurse` | `Exception` |
| `ImpureOffering` | `ValueError` |
| `PatternMismatch` | `TypeError` |
| `LostPattern` | `KeyError` |
| `BeyondTheManifest` | `IndexError` |
| `AbsentAugmetic` | `AttributeError` |
| `DivisionByTheVoid` | `ZeroDivisionError` |
| `ForbiddenLore` | `ImportError` |
| `RelicNotFound` | `FileNotFoundError` |
| `SpiralOfMadness` | `RecursionError` |
| `TheRiteIsEnded` | `StopIteration` |
| `UnknownInvocation` | `NameError` |
| `MotiveFailure` | `RuntimeError` |
| `RiteUnwritten` | `NotImplementedError` |

An exception with no ritual name keeps its own. The lookup walks the class
hierarchy, so `ModuleNotFoundError` renders as `ForbiddenLore` by descent from
`ImportError`, rather than appearing untranslated in a translated curse.

### Reading a curse

```
++ MACHINE CURSE ++
   the rite was broken at the threshold of prayer.lit, line 6
       invoke_spirit(7)
       ^^^^^^^^^^^^^^^^
   the rite was broken at prayer.lit, line 3, in rite invoke_spirit
       render tome / 0
              ^^^^^^^^
   DivisionByTheVoid: division by zero
++ the machine spirit is displeased ++
```

Four things are true of this that are not true of a naive translation layer:

- **The line numbers are the Liturgy line numbers.** The transform never adds
  or removes a line, so line N of the generated Python is line N of your
  source. Nothing is remapped because nothing moved.
- **The carets point at the Liturgy columns.** Words do change width —
  `should` is six characters and `if` is two — so a column map is kept and
  consulted when a curse is rendered.
- **The source shown is what actually ran.** The exact text compiled is
  recorded at compile time, so editing the file after import does not cause
  the curse to quote a line that never executed.
- **"at the threshold of"** marks module-level code. Module level is not a
  rite, and the curse does not claim it is.

Frames belonging to Liturgy itself — the loader, the transform, the import
machinery — are suppressed, exactly as CPython hides its own import internals.
Frames from libraries your litany called into are kept, because those are your
answer rather than noise.

### Errors before execution

A litany that will not compile has no frames at all. The curse still names the
file, the line, the source text and the column:

```
++ MACHINE CURSE ++
   the rite was ill-written at prayer.lit, line 1
       x = (1, 2
           ^
   UnfinishedLitany: '(' was never closed
```

`UnfinishedLitany` is a `SyntaxError` subclass, so `curse SyntaxError` catches
it wherever you would expect.

### --profane

*There are occasions — the reporting of a fault to a distant forge, chiefly —
when the plain tongue serves better than the proper one. It is permitted. It
is not encouraged.*

```
$ liturgy --profane chant prayer.lit
```

Renders an ordinary Python traceback. `LITURGY_PROFANE=1` does the same.

---

## Chapter VI — The Three Prohibitions

*The reservation of words binds the adept's own naming. It cannot bind the
naming of others. A pattern drawn from a distant forge may call its own parts
whatever it likes, and the litany must still be able to speak to it.*

Substitution is therefore forbidden in three positions.

### The first: after a dot

A name following `.` is never substituted. Without this, `template.render()`
would become `template.return()` — a syntax error — and every library with a
`.render()`, `.pattern` or `.span()` would break on contact.

```
invoke re

intone(re.compile("x+").pattern)
intone(re.match("x+", "xxy").span())
```

```
$ liturgy chant attributes.lit
x+
(0, 2)
```

Both survive, though `pattern` and `span` are reserved words.

### The second: in keyword-argument position

A name immediately followed by `=` inside a call is never substituted, so
`func(intone=True)` does not silently become `func(print=True)`.

The rule makes one exception, for the f-string debug form. In `f"{measure=}"`
the `=` is not a keyword argument, so substitution proceeds and the value is
printed as `f"{len=}"` intends.

### The third: within an invocation

Inside an `invoke` or `within` statement, only the statement's own keywords
are substituted. The targets are left alone.

```
within json invoke loads styled parse_json

intone(parse_json('{"a": 1}'))
```

```
$ liturgy chant invocation.lit
{'a': 1}
```

`loads` is untouched; `within`, `invoke` and `styled` are translated. Relative
invocations work as expected — `within . invoke sibling`, and deeper.

---

## Chapter VII — Of Words Reserved

*A word given to the Machine God is no longer yours. Choose your own names
knowing which are already spoken for.*

Sixty-three words are reserved: thirty-eight rites, five builtins, fifteen
curses, two numerals, and three constructs. Using one as your own identifier
is an error. Most such errors are loud, and a loud error costs you a minute.

```
render = compute()
```

```
SyntaxError: invalid syntax
```

### The quiet ones

Two of the builtin aliases fail quietly instead, and these are the ones to
know. `span` and `measure` translate to `range` and `len` — which are names,
not keywords, so assigning to them is legal Python:

```
span = "text range"
intone(span)
```

This runs. It prints `text range`. What it compiled to is:

```python
range = "text range"
print(range)
```

You have shadowed a builtin. Nothing complains now. The complaint arrives
later and elsewhere, when something calls `span(10)` and receives a string.
The same holds for `measure`, `unseal` and `hearken`.

Until the `augur` rite of Chapter IX exists to warn you, this is a thing to
carry in your head. `span` in particular is a natural name for a range of
text, and it is precisely the wrong one.

### Calling is not defining

The first prohibition protects your *use* of a library's `.render()`. It does
not let you *declare* one, because a declaration is not in attribute position:

```
pattern Template:
    rite render(self):
        render "rendered"
```

```
   the rite was ill-written at template.lit, line 2
       rite render(self):
            ^^^^^^
   SyntaxError: invalid syntax
```

Calling `t.render()` is fine. Naming a rite `render` is not. If you must
implement an interface whose method name is a reserved word, that method must
be written in a `.py` file — which a litany may freely import.

### The limits of consecrated

`consecrated` reserves a word the same way any other construct does, and it
is worth being exact about what its enforcement covers, because the word
"enforced" invites more confidence than the mechanism can support. The
rejection happens at compile time, against the AST the compiler can see:
rebindings, a second `consecrated` of the same name, a `consecrated` inside
a loop body. What the compiler cannot see, it cannot stop — `setattr`,
`globals()`, assignment through the module object, and `exec` all get
through untouched. This is enforcement, not a guarantee.

---

## Chapter VIII — Of Heresy

*The rites have names. Use them.*

The mundane verbs work. `run` invokes `chant`; `repl` invokes `commune`. They
work because at some hour of the night you will type `run`, and a tool that
refuses on a point of doctrine is a tool you will stop using.

They are nonetheless noted.

```
$ liturgy run hello.lit
++ TECH-HERESY DETECTED ++
++ this rite is named CHANT. the omission is noted. ++
Ave Omnissiah
```

The rebuke escalates across invocations — *the omission is noted*, then *the
transgression is recorded in your permanent record*, then *the Inquisition has
been notified* — and saturates there.

Three properties are deliberate:

- It is written to **stderr**, so `liturgy run x.lit | jq` is unaffected.
- It **does not change the exit code**. Heresy is a moral failing, not a
  runtime failure.
- It can be **silenced**, by `--absolved` or `LITURGY_PIOUS=0`, because a
  build log that carries it on every line is a build log nobody reads.

---

## Chapter IX — Rites Not Yet Written

*The Quest for Knowledge is not concluded. Most of these pages are left
blank deliberately; do not report their blankness as a fault. One entry
below was struck rather than left blank, and that is recorded too.*

### The one construct cut, not deferred

Three constructs of the second spec are built; Chapter X sets them down in
full. A fourth was designed alongside them and did not survive: `noospheric`,
a binding placed in a process-wide registry rather than module scope. It was
**cut, not deferred** — it is a service locator, and Liturgy generates code
with no runtime of its own for a registry like that to live in. There is no
clean place left to put it.

### Verbs of the third spec

Reserved now so that nothing else claims the names: `augur` (to read a litany
for faults without chanting it), `prove` (to run its trials), `sanctify` (to
set its form in order), `forge`, `consecrate`, `purge`, `anoint`, and
`transcribe` — to render a Python file into Liturgy.

The `augur` verb is the one that matters most, since it is what would catch the
quiet reservations of Chapter VII.

`augur` and `purge` each name two different things in this project. `augur`
is both Chapter X's built source construct (preconditions) and this
still-unbuilt CLI verb (lint); `purge` is both Chapter III's built keyword
alias for `del` and this still-unbuilt CLI verb (clearing caches). A source
word and a CLI verb cannot actually collide — they live in entirely
different namespaces — but the same word meaning two different things in the
same project is exactly the kind of thing worth spelling out rather than
leaving implicit.

---

## Chapter X — The Greater Rites

*Three constructs the second spec adds. Python has no word for any of them —
Liturgy needed new grammar, not new spelling, to say what they say.*

Each is a compile-time transformation, not a call into some runtime library.
A carrier pass rewrites the construct's header, in place, into ordinary
Python that parses; a second pass over the resulting tree then restructures
it into real semantics, or rejects the misuse outright. Nothing beyond the
standard library is imported to make any of the three work — there is no
Liturgy runtime for them to depend on.

### consecrated — a binding that will not move

```
consecrated PORT = 8080
```

`consecrated NAME = value` declares a binding once. Every later assignment
to that name that the compiler can see, in the scope where it was declared —
a plain assignment, an augmented assignment, an annotated assignment, a
walrus, a `foreach` target, a `with ... styled` target, `purge`, a binding
`invoke`/`within`, or a name reached through destructuring — is rejected
before the litany runs. So is a second `consecrated` of the same name, and a
`consecrated` written inside a loop body, which would rebind on every
iteration while reading like one declaration.

A nested rite may use the same name freely; that is a new, local binding,
not a rebinding of the enclosing one. Rebinding through `universal` inside a
nested rite is still caught, because a `universal` declaration followed by
an assignment is a real write back into the declaring scope, and the
compiler can see it there too.

Chapter VII, "The limits of consecrated," sets down what this enforcement
does not reach.

### litany — a rite re-chanted on failure

```
litany(thrice, resting=2, curse=TimeoutError):
    send_offering()
```

`litany(count, resting=..., curse=...):` runs its body once, and if it
raises one of the exceptions named by `curse=`, runs it again — up to
`count` **total attempts**, not `count` retries. `curse=` is required and
must be passed by keyword; there is no spelling of `litany` that catches
everything, on the view that a retry block silently swallowing an exception
it was never told about is worse than no retry block at all. `resting=` is
optional. Left out, a litany moves to its next attempt with no pause and
generates no timing code whatsoever. Exhausting every attempt re-raises the
last failure, unchanged.

`count` is evaluated exactly once, however it is spelled — a bare `thrice`,
a variable, or a call. A count below one is rejected: at compile time when
it is written as a literal, at run time when it is computed.

`cease` and `persist` written directly in a litany's own body are rejected
at compile time, because they would bind to the retry loop the construct
generates, not to anything the author wrote. The same two words inside a
real `foreach` or `whilst` nested in that body are untouched — there, they
bind to that loop, exactly as expected.

### augur — a precondition, not an assertion

```
rite divide(a, b):
    augur:
        b be nay Void
        b != 0
    render a / b
```

`augur:` opens a rite — after its docstring if it has one, never after any
other statement — with one bare condition per line. Each condition is
checked before the rite's own body runs. The first one that is false raises
`ImpureOffering`, with a message that quotes the *Liturgy* source of that
condition, not the compiled Python it became: `the omens forbid it -- b !=
0`. Anything in the block that is not a bare condition — an assignment, a
call kept for its side effect — is rejected at compile time; an augury holds
conditions, not statements.

It is a contract, not an assertion, and the distinction is load-bearing: it
survives `chant`ing under `-O`, where a Python `assert` would compile away
to nothing. It raises `ImpureOffering` rather than some purpose-built
exception class of its own, because there is no Liturgy runtime package for
generated code to import from — its exceptions have to be ones Python
already provides.

A nested rite's own opening augury is independent of any augury on the rite
that contains it; each rite's opening belongs to that rite alone.

---

## Appendix — The Full Concordance

Liturgy to Python, then Python to Liturgy. The mapping is a bijection: no two
ritual words share a Python word, and no Python word has two ritual spellings.
A test asserts it, because the reverse direction is what a future `transcribe`
will need.

### Rites

| Liturgy | Python | Liturgy | Python |
|---|---|---|---|
| `abide` | `pass` | `nay` | `not` |
| `adjacent` | `nonlocal` | `otherwise` | `else` |
| `among` | `in` | `pattern` | `class` |
| `anointed` | `with` | `persist` | `continue` |
| `archetype` | `type` | `proclaim` | `raise` |
| `attempt` | `try` | `purge` | `del` |
| `attend` | `await` | `regardless` | `finally` |
| `attest` | `assert` | `remote` | `async` |
| `be` | `is` | `render` | `return` |
| `cease` | `break` | `rite` | `def` |
| `curse` | `except` | `Sanctioned` | `True` |
| `discern` | `match` | `servitor` | `lambda` |
| `elsewise` | `or` | `should` | `if` |
| `emanate` | `yield` | `styled` | `as` |
| `foreach` | `for` | `universal` | `global` |
| `Heretical` | `False` | `Void` | `None` |
| `invoke` | `import` | `wherein` | `case` |
| `lest` | `elif` | `whilst` | `while` |
| `likewise` | `and` | `within` | `from` |

### Builtins

| Liturgy | Python |
|---|---|
| `hearken` | `input` |
| `intone` | `print` |
| `measure` | `len` |
| `span` | `range` |
| `unseal` | `open` |

### Curses

| Liturgy | Python |
|---|---|
| `AbsentAugmetic` | `AttributeError` |
| `BeyondTheManifest` | `IndexError` |
| `DivisionByTheVoid` | `ZeroDivisionError` |
| `ForbiddenLore` | `ImportError` |
| `ImpureOffering` | `ValueError` |
| `LostPattern` | `KeyError` |
| `MachineCurse` | `Exception` |
| `MotiveFailure` | `RuntimeError` |
| `PatternMismatch` | `TypeError` |
| `PrimalCurse` | `BaseException` |
| `RelicNotFound` | `FileNotFoundError` |
| `RiteUnwritten` | `NotImplementedError` |
| `SpiralOfMadness` | `RecursionError` |
| `TheRiteIsEnded` | `StopIteration` |
| `UnknownInvocation` | `NameError` |

### Numerals

| Liturgy | Python |
|---|---|
| `thrice` | `3` |
| `twice` | `2` |

---

*Thus concludes the Liber Liturgiae.*
*Praise the Omnissiah, who is the Machine, and the Machine, which is knowledge.*
