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

Fifty-eight words are reserved: thirty-eight rites, five builtins, fifteen
curses. Using one as your own identifier is an error. Most such errors are
loud, and a loud error costs you a minute.

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

*The Quest for Knowledge is not concluded. These pages are left blank
deliberately; do not report their blankness as a fault.*

### Constructs of the second spec

Four constructs are designed and unbuilt. None of them parse today.

| | Purpose |
|---|---|
| `consecrated` | A binding that may not be altered. Python has no constants, only the convention of shouting; a consecrated binding would be enforced, and rebinding one would raise `TechHeresy`. |
| `litany` | A block re-chanted on failure — retry with rests between attempts. |
| `augur` | Conditions read before a rite's body runs. Preconditions as contract. |
| `noospheric` | A binding placed in a process-wide registry rather than module scope. |

### Verbs of the third spec

Reserved now so that nothing else claims the names: `augur` (to read a litany
for faults without chanting it), `prove` (to run its trials), `sanctify` (to
set its form in order), `forge`, `consecrate`, `purge`, `anoint`, and
`transcribe` — to render a Python file into Liturgy.

The `augur` verb is the one that matters most, since it is what would catch the
quiet reservations of Chapter VII.

`augur` and `purge` each appear twice above — once as a construct or rite, once
as a verb of the command line. They do not collide: one is a word in a litany,
the other a word typed at a terminal. The overlap is noted here so that it
reads as intentional.

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

---

*Thus concludes the Liber Liturgiae.*
*Praise the Omnissiah, who is the Machine, and the Machine, which is knowledge.*
