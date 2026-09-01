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

### The illumination of glyphs

Two illuminators are kept, one exact and one approximate. The exact one is a
Pygments lexer carried by the package itself as an optional extra:

```
$ pip install -e ".[highlight]"
$ pygmentize prayer.lit
```

It does not guess from a word-list; it asks the same token passes the
compiler runs which occurrences *are* Liturgy, so the three prohibitions of
Chapter VI and the construct-header rules of Chapter X hold in the colours
exactly as they hold in the transform, and the machine's own names of
Chapter VII are painted as the heresies they are. It is not a linter:
`span = 1` paints `span` as the builtin it becomes, and judging bindings
remains `augur`'s office.

The approximate one is a TextMate grammar for VS Code, in
`editors/vscode-liturgy` of the repository, installed by hand (its README
sets down how, and which context rules a line-based grammar can only
approximate). A test holds its word lists to the lexicon, so a word cannot
be reserved without the grammar learning it.

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
The flag is accepted before or after the verb — with one caveat inherited
from `python file.py` itself: anything after `chant`'s file belongs to the
litany, so for `chant` the flag goes before the filename.

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
printed as `f"{len=}"` intends. Note that this means the label in the output
is the generated Python's — `f"{measure(x)=}"` prints `len(x)=2` — because an
f-string fixes its debug text at compile time, after substitution.

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
SyntaxError: invalid syntax (render is Liturgy for return)
```

The parenthesis is the curse renderer's doing: when a syntax error points
into — or hard against — a word a substitution produced, the word is named,
so the message describes the litany rather than the Python it became.

### The quiet ones

Eight of the substituted words fail quietly instead, and these are the ones
to know. The five builtin aliases — `intone`, `measure`, `span`, `unseal`,
`hearken` — translate to `print`, `len`, `range`, `open` and `input`, which
are names, not keywords, so assigning to them is legal Python:

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

The three soft-keyword aliases are quiet the same way: `discern`, `wherein`
and `archetype` become `match`, `case` and `type`, which are ordinary
identifiers anywhere they are not heading their own statement. So
`discern = 5` compiles, runs, and has quietly bound the name `match`.

Two of the three constructs are quiet too, for a different reason. A
construct word is only a construct in the position its header occupies;
anywhere else it is an ordinary name, and the carrier pass leaves it alone.
So `litany = 5`, `litany: int = 5`, `rite augur(x):` and `pattern litany:`
all compile, and the name is yours until the day you want the construct on
that line:

```
litany = 5
augur = compute()
rite augur(x):
    render x
pattern litany:
    abide
```

Every line of that compiles. `consecrated` is the exception among the three:
it can only ever be a header, so `consecrated = 5` is a loud heresy. One
spelling of `augur` is refused as well: a bare, valueless annotation —
`augur: b != 0` — reads exactly like a one-line augury wherever it stands,
and treating it as the annotation it technically is would check nothing. An
augury's conditions belong on the lines beneath `augur:`, and the heresy says
so; an annotation *with* a value (`augur: int = 5`) is unmistakably yours and
compiles. Ten of the sixty-three words
are quiet, then — the five builtins, the three soft keywords, `litany`,
`augur` — and the rest are loud.

`span` in particular is a natural name for a range of text, and it is
precisely the wrong one. Eight of the ten no longer have to be carried in
your head: the builtins and the soft keywords each *become* another word,
and `liturgy augur` reports every binding that does. Chapter XI sets it down.

`litany` and `augur` are not reported, and should not be. A construct word is
never substituted, so there is nothing it silently becomes — the only hazard
is the one above, that you may one day want the construct on a line whose name
you have already spent. That one stays yours to track.

### The machine's own names

Three names appear in no table and are reserved all the same:
`__consecrated__`, `__litany__` and `__augur__` — the private carriers the
construct pass writes into the generated Python — along with every name
beginning `__liturgy_`, which the retry loop mints its bookkeeping under. A
litany that spoke one would be indistinguishable from the machinery itself,
so speaking one anywhere but after a dot is a loud heresy:

```
x = __litany__
```

```
TechHeresy: __litany__ is the machine's own name
```

Chapter XI's verbs know them too: `augur` reports a `.py` file that binds
one, and `transcribe` refuses to render such a file, because the litany it
would write cannot chant.

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
   SyntaxError: invalid syntax (render is Liturgy for return)
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

The same boundary explains `commune`. Enforcement is per compilation unit,
and every entry at the prompt is its own unit: by the time you type `PORT = 9`
the compiler has no record of the `consecrated PORT = 8080` you typed three
lines earlier, and the rebinding goes through.

```
>>> consecrated PORT = 8080
>>> PORT = 9
>>> intone(PORT)
9
```

Within a single entry — one line, or one block typed across several — the
rejection is exactly as it is in a file:

```
>>> consecrated PORT = 8080; PORT = 9
++ MACHINE CURSE ++
   the rite was ill-written at <commune:1>, line 1
       consecrated PORT = 8080; PORT = 9
                                ^
   TechHeresy: PORT is consecrated and may not be rebound
++ the machine spirit is displeased ++
```

(`<commune:1>` numbers the prompt entry. Every entry keeps its own recorded
source, which is what lets a curse — this one, or a runtime failure in a rite
defined many entries ago — quote the Liturgy that was actually typed.)

A litany is a file. The prompt is a conversation, and a conversation
remembers values, not declarations.

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

### The four verbs still unwritten

Four verbs are built; Chapter XI sets them down. Four names remain reserved on
the command line, and it is worth recording why each is still a name and
nothing more, rather than leaving the blanks unexplained.

`prove` — to run a litany's trials — is unbuilt because the trials already
run. The import hook is a real one, so pytest imports a `.lit` module like any
other, and a short `conftest.py` that installs the hook and hands
`pytest.Module` any `test_*.lit` collects them directly, failures quoting the
Liturgy source. A verb wrapping that would add a layer and no capability.

`sanctify` — to set a litany's form in order — is unbuilt because a formatter
is its own project rather than a verb on someone else's. Doing it properly
means a full-fidelity round-trip through comments, blank lines and string
quoting; doing it improperly means a tool that eats your source.

`forge` was in this list, and is not any longer. It was one of three words
reserved as flavour with no feature behind it; ahead-of-time compilation
turned out to be the feature it had been waiting for. Chapter XI sets it
down. The reservation did its work — the name was still there when something
worth spending it on arrived.

`consecrate` and `anoint` are unbuilt because there is still no feature
behind them. They were reserved as flavour — good words held back so that
nothing trivial could spend them later. They are held, not planned, and no
page is being left blank for them.

`augur` and `purge` each name two different things in this project. `augur`
is both Chapter X's source construct (preconditions) and Chapter XI's CLI
verb (lint); `purge` is both Chapter III's keyword alias for `del` and
Chapter XI's CLI verb (clearing caches). A source word and a CLI verb cannot
actually collide — they live in entirely different namespaces — but the same
word meaning two different things in the same project is exactly the kind of
thing worth spelling out rather than leaving implicit.

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
must be passed by keyword — spelled out, not smuggled in through a `**`
expansion; there is no spelling of `litany` that catches everything, on the
view that a retry block silently swallowing an exception it was never told
about is worse than no retry block at all. `resting=` is
optional. Left out, a litany moves to its next attempt with no pause and
generates no timing code whatsoever. Exhausting every attempt re-raises the
last failure, unchanged.

`count` and `resting` are each evaluated exactly once, however they are
spelled — a bare `thrice`, a variable, or a call — and each is guarded the
same two-tier way: a count below one, or a negative resting, is rejected at
compile time when written as a literal and at run time when computed. The
run-time check fires before the first attempt, so a bad value is its own
loud fault rather than something an outer `curse` mistakes for the body
failing again.

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
other statement — with one bare condition per line, the `augur:` itself
standing alone on its own. Each condition is
checked before the rite's own body runs. The first one that is false raises
`ImpureOffering`, with a message that quotes the *Liturgy* source of that
condition, not the compiled Python it became: `the omens forbid it -- b !=
0`. Anything in the block that is not a bare condition is rejected at
compile time: a statement of any kind, a constant (a docstring is not a
condition), a walrus assignment. A call is accepted, and its *truth* is the
omen — `augur:` over `seen.append(x)` fails every time, because `append`
renders Void. The augury judges the value of what you wrote; it cannot know
what you meant to check.

It is a contract, not an assertion, and the distinction is load-bearing: it
survives `chant`ing under `-O`, where a Python `assert` would compile away
to nothing. It raises `ImpureOffering` rather than some purpose-built
exception class of its own, because there is no Liturgy runtime package for
generated code to import from — its exceptions have to be ones Python
already provides.

A nested rite's own opening augury is independent of any augury on the rite
that contains it; each rite's opening belongs to that rite alone.

---

## Chapter XI — The Reading of Omens

*Two verbs chant. Four do not. An adept who only ever chants learns of his
errors from the machine, at the hour the machine chooses. These four are the
rites of asking first.*

`augur`, `transcribe`, `forge` and `purge` are the built tooling verbs. None
of them runs your litany. `augur` reads one, `transcribe` writes one, `forge`
compiles one without chanting it, and `purge` clears what chanting left
behind.

### augur — the omens read before the chant

Not to be confused with Chapter X's `augur:` construct, which is source and
guards a rite. This is a command-line verb, and it guards a file.

```
$ liturgy augur quiet.lit
++ THE OMENS ARE TROUBLED ++
   quiet.lit, line 1
       span = "text range"
       ^^^^
   span is reserved; it becomes range -- silently
```

That is the trap of Chapter VII, found before it can be sprung. `--plain`
gives one parseable line per finding, for an editor or a build log:

```
$ liturgy augur --plain quiet.lit
quiet.lit:1:1: span is reserved; it becomes range -- silently
```

The trailing `-- silently` is the important half. It appears when the
substitution target is an ordinary name rather than a Python keyword, which
is exactly the case where the file compiles and the harm is deferred. A
finding without it is a collision that will announce itself loudly somewhere;
a finding with it is one that will not.

Arguments may be files or directories, and a directory is walked for `.lit`
and `.py` files — `augur` reads plain Python too, because a `.py` file in a
Liturgy project is a file whose names a litany may one day import. The walk
prunes the usual noise: names beginning with a dot, `__pycache__`, and any
directory holding a `pyvenv.cfg` — a vendored virtual environment would
otherwise drown real findings under every third-party `.py` that binds
`render` or `span`. A directory named directly as an argument is always
read, hidden or not: naming it is asking. Arguments that overlap report
each finding once. The exit
status is 0 when nothing was reported and 1 when anything was. A directory
reached through a symlink, or a hidden `.lit`/`.py` file inside a walked
directory, is named in the report rather than passed over in silence — a
reader that quietly does not read a file is worse than no reader. (A
symlinked directory the walk would prune anyway, a symlinked `.venv` say, is
pruned as quietly as a real one.)

### The two checks, and no third

`augur` makes exactly two.

**Words that become another word, used as your own names.** A binding
collides two ways, and both are reported. Either you wrote the reserved word
and the substitution produced the bound name — `span = ...` becoming
`range = ...` — or one of Chapter VI's exemptions protected the word from
substitution and left you bound to it whole.

This check reaches the sixty words that have a Python spelling, not all
sixty-three. The three construct words are outside it by construction: they
are never substituted, so no binding of one can quietly come to mean
something else. `consecrated` is still caught — by the second check, as a
compile failure — and `litany` and `augur` are genuinely not faults. The
machine's own carrier names (Chapter VII) are within it: they have no
Python spelling to become, but a `.py` file that binds one is a file no
litany can import by that name, and the finding says so.

**That the litany compiles.** For a `.lit` file, `augur` compiles the source
after gathering collisions, so a file `augur` calls clean is a file `chant`
will accept. The two must not be able to disagree about that.

There is deliberately no third. No line-length rule, no unused-import check,
no naming convention. `augur` reports the class of fault that is specific to
Liturgy — the class no other tool in your setup can see — and leaves the rest
to the tools that already do it well. It is not a general linter and is not
going to become one.

### The collision Chapter VI does not cover

The third prohibition leaves an invocation's targets unsubstituted. That is
what makes `within json invoke loads` work. It also means a target bound
under a reserved name stays bound under it:

```
within json invoke loads styled render
```

`render` is not substituted here — the exemption protects it — so the module
is genuinely bound to the name `render`. Every *later* mention of `render` is
outside the exemption and becomes `return`, so the litany fails at the point
of use, with a syntax error that says nothing about the import that caused
it. This is the subtle one, and it is why `augur` treats an import target as
a binding like any other:

```
$ liturgy augur imp.lit
++ THE OMENS ARE TROUBLED ++
   imp.lit, line 1
       within json invoke loads styled render
                                       ^^^^^^
   render is reserved; it becomes return
```

The caret is the point. Four of the six words on that line are Liturgy's own,
and only the last of them is yours to have got wrong.

Chapter VI's exemptions govern what is substituted. They say nothing about
what is safe to be bound to, and the two are not the same question.

### transcribe — a Python file rendered into the proper tongue

```
$ liturgy transcribe greet.py
rite greet(name):
    should nay name:
        render "Ave Omnissiah"
    render f"Ave {name}"


foreach i among span(2):
    intone(greet(""))
```

Given `-o`, it writes the file instead of printing it and reports the count:

```
$ liturgy transcribe greet.py -o greet.lit
++ 8 lines transcribed ++
```

`transcribe` refuses in preference to producing something subtly wrong. It
refuses a source that will not parse, a source it cannot decode, and — the
case that matters — a source binding a name Liturgy reserves, because no
correct Liturgy spelling of that program exists:

```
$ liturgy transcribe shadow.py
++ CANNOT TRANSCRIBE: 1 COLLISION ++
  shadow.py:1  span         -> reserved (range)
rename these, then chant again
```

That is the same rule `augur` reports, computed by the same code, so the two
verbs cannot drift apart about what counts as a collision.

The last line of defence is broader than the collision rule: the output is
compiled before anything is written or printed. A Python program only the
compile can catch — one that binds a bare `consecrated`, or speaks one of
the machine's own names in a position the binding scan does not see — is
refused as one no litany can express:

```
$ liturgy transcribe cons.py
++ CANNOT TRANSCRIBE: the output would not chant ++
   line 1: consecrated must be followed by a name
rewrite or rename what it names, then transcribe again
```

The same rule is applied a second time, to the Liturgy about to be written.
Transcription can introduce a collision the Python never had — `input` is
rendered `hearken`, and `hearken` is reserved. That output is not wrong: it
round-trips, and it chants exactly as the Python ran. So it is a warning,
not a refusal:

```
$ liturgy transcribe codec.py -o codec.lit
++ 2 lines transcribed ++
++ THE OUTPUT CARRIES 1 COLLISION ++
  codec.lit:1  hearken      -> reserved (input)
augur will flag these; the litany is correct and chants as written
```

When the litany goes to stdout the warning goes to stderr instead, so a
redirected file receives the words and nothing else.

### The self-check before the writing

Nothing reaches disk unverified. `transcribe` transforms its own output back
into Python and compares it against the source it read. If the two differ,
the output is wrong, and it is not written:

```
++ CANNOT TRANSCRIBE: the output does not round-trip ++
   this is a fault in Liturgy, not in your source
```

This is the property test the suite runs over the standard library, applied
to one real file at the moment it matters. A destination file gets a second
check at the byte level: the exact bytes about to be written are decoded the
way a consumer honouring their own `coding:` cookie would decode them, and
compared again. Line endings and the source's declared encoding are carried
through unchanged, so the transcribed file differs from its source in its
words and in nothing else.

### forge — the bytecode beaten out beforehand

`forge` compiles litanies to bytecode ahead of the import that would
otherwise have to do it. Given no paths it works on the current directory,
recursing; given paths it takes those.

```
$ liturgy forge
   forged mod.lit
   forged sub/two.lit
++ 2 litanies forged ++
```

Only `.lit` files are forged. Turning `.py` into `.pyc` is `compileall`'s
work, and Liturgy has nothing to add to it.

**It does not chant what it forges.** That is the whole difference between
forging a litany and importing one, and it is why a litany whose top level
prints, or writes a file, or opens a socket, can be forged in perfect
safety. The compiling is done by the import system's own `get_code`, which
compiles and caches without executing.

Run again, a forge that finds its work already done says so rather than
repeating it:

```
$ liturgy forge
++ 0 litanies forged, 2 already current ++
```

The distinction is measured, not guessed: the cache file's timestamp is read
either side of the compile, and only a change to it counts as a forging.
`--anew` forges regardless.

### Why ordinary `.pyc`, and not a `.litc` of our own

A themed extension was considered and rejected. `SourceLoader.get_code`
reaches for `cache_from_source` as a module-level function rather than a
method on itself, so a subclass cannot redirect it; changing the extension
would mean reimplementing eighty-odd lines of private import machinery and
carrying that fork across every Python version this project supports. The
extension is cosmetic. The loader it would destabilise is what makes a curse
quote Liturgy at all.

So the bytecode goes where all bytecode goes, under `__pycache__`, in the
ordinary spelling. `purge` clears it, `.gitignore` ignores it, and every tool
that has ever understood a Python cache understands this one.

### When the machine will not keep what is beaten

An interpreter started with `-B`, or with `PYTHONDONTWRITEBYTECODE` set in
the environment, discards every cache write. Forging under it would compile
each litany, report success, and leave nothing behind. `forge` refuses
instead:

```
++ CANNOT FORGE: this interpreter will not write bytecode ++
   -B or PYTHONDONTWRITEBYTECODE is in force
```

A litany that will not compile is named, with the line, and the walk carries
on to the next:

```
++ CANNOT FORGE: broken.lit line 1 SyntaxError: 'return' outside function (render is Liturgy for return) ++
++ 0 litanies forged, 2 already current ++
```

The exit status is 0 when everything asked for was forged or already
current, and 1 if the interpreter refused the whole run or any single litany
failed.

### purge — the clearing of relics

`purge` removes every `__pycache__` directory beneath the working directory,
and, given `--heresies`, the heresy record of Chapter VIII along with them.

It is the only verb that destroys anything, so it is guarded. It refuses
outright unless the tree holds at least one `.lit` file:

```
   no .lit file found; refusing to delete anything
```

A recursive delete launched from the wrong directory is a bad afternoon, and
the presence of a litany is a cheap proxy for being where you meant to be.
Symlinked directories are never entered.

The reporting is guarded in the same spirit. Each removal is named on its own
line, and that line is printed only once the delete beneath it has actually
succeeded — the report never claims a deletion that did not happen. A
directory that will not go, for want of permission or because it vanished
between the walk and the delete, is reported and stepped over rather than
raising; one unreadable cache must not strand the rest. The run ends with a
count of what actually went:

```
++ 0 relics purged ++
```

The exit status is 0 when everything asked for went, and 1 if the guard
refused or any single removal failed.

---

## Appendix — The Full Concordance

Liturgy to Python, then Python to Liturgy. The mapping is a bijection: no two
ritual words share a Python word, and no Python word has two ritual spellings.
A test asserts it, because the reverse direction is what Chapter XI's
`transcribe` reads.

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
