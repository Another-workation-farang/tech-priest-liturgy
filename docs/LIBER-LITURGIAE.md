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
>>> rite fib(n: int) -> int:
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

### When the hook must outlive the verb

"Which both verbs do for you" is the whole of it: `chant`, `commune` and
`prove` install the hook on their way in, and nothing else does. An
interpreter started any other way — `python -m`, a server, a notebook — cannot
see a litany at all.

```
$ python -c "import mymod"
ModuleNotFoundError: No module named 'mymod'
```

The hook can be installed into an environment instead of into a command. A
`.pth` file in site-packages is executed at interpreter start, and any line
of one beginning with `import` runs:

```bash
echo 'import liturgy.loader; liturgy.loader.install()' > "$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')/liturgy-hook.pth"
```

Thereafter a litany imports from anywhere:

```
$ python -c "import mymod; print(mymod.greet())"
ave, Omnissiah
```

Deleting the file undoes it completely; there is no other state.

Three things are worth knowing before an adept does this. It costs every
interpreter start in that environment, litany or no litany — some ten to
twenty milliseconds, most of it reading installed-package metadata. It
writes into site-packages, so it belongs in a virtual environment and not in
a machine's own Python. And it buys importing, not collection: plain pytest
still finds no trials in a `test_*.lit`, because collecting a file and
importing one are different offices. Chapter XI's `prove` is the verb for
that.

There is deliberately no verb for anointing an environment. `anoint` was the
obvious name and Chapter IX sets down why it remains unspent.

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
    rite __init__(self, relics: list[str]) -> Void:
        self.relics = relics

    rite blessed(self) -> list[str]:
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

Sixty-four words are reserved: thirty-eight rites, five builtins, fifteen
curses, two numerals, and four construct words. Using one as your own
identifier is an error. Most such errors are loud, and a loud error costs you a minute.

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

Two of the four construct words are quiet too, for a different reason. A
construct word is only a construct in the position its header occupies;
anywhere else it is an ordinary name, and the carrier pass leaves it alone.
So `litany = 5`, `litany: int = 5`, `rite augur(x: int) -> int:` and
`pattern litany:` all compile, and the name is yours until the day you want
the construct on that line:

```
litany = 5
augur = compute()
rite augur(x: int) -> int:
    render x
pattern litany:
    abide
```

Every line of that compiles. `consecrated` and `unsanctioned` are the two
that are not quiet: each can only ever be a header or a modifier, so
`consecrated = 5` and `unsanctioned = 5` are both loud heresies. One
spelling of `augur` is refused as well: a bare, valueless annotation —
`augur: b != 0` — reads exactly like a one-line augury wherever it stands,
and treating it as the annotation it technically is would check nothing. An
augury's conditions belong on the lines beneath `augur:`, and the heresy says
so; an annotation *with* a value (`augur: int = 5`) is unmistakably yours and
compiles. Ten of the sixty-four words are quiet, then — the five builtins,
the three soft keywords, `litany`, `augur` — and the rest are loud.

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
`__consecrated__`, `__litany__` and `__augur__` — the private names the
construct compiler claims for itself — along with every name
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
    rite render(self) -> str:
        render "rendered"
```

```
   the rite was ill-written at template.lit, line 2
       rite render(self) -> str:
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

### The one verb still unwritten

Seven verbs are built; Chapter XI sets them down. One name remains reserved
on the command line, and it is worth recording why it is still a name and
nothing more, rather than leaving the blank unexplained.

`forge`, `consecrate`, `prove` and `sanctify` were all in this list once.
Each left it for its own reason, and the reasons are worth keeping: `forge`
and `consecrate` were words reserved as flavour that turned out to have
features waiting for them; `prove` was declined for adding a layer and no
capability, and was built anyway once it was clear that boilerplate every
project must copy is itself a cost; `sanctify` was declined because a
formatter done improperly eats your source, and was built only once it could
check that it had not.

`anoint` is unbuilt because there is still no feature behind it. It is the
last of the reserved names, held rather than planned — and holding it is the
point. A name still unspent is worth more than a name spent on something
trivial. No page is being left blank for it.

`augur` and `purge` each name two different things in this project. `augur`
is both Chapter X's source construct (preconditions) and Chapter XI's CLI
verb (lint); `purge` is both Chapter III's keyword alias for `del` and
Chapter XI's CLI verb (clearing caches). A source word and a CLI verb cannot
actually collide — they live in entirely different namespaces — but the same
word meaning two different things in the same project is exactly the kind of
thing worth spelling out rather than leaving implicit.

`Sanctioned` and `unsanctioned` belong on the same list, and they are the
closer pair of the three: both are source words. `Sanctioned` is Chapter
III's alias for `True`; `unsanctioned` is Chapter XII's modifier waiving the
archetype rule, and one is not the negation of the other. They are told apart
by case and by position — one is a value, the other stands at the head of a
statement — and no table can confuse them, since `unsanctioned` has no Python
spelling to be substituted for. It is written down here rather than
discovered later.

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

`consecrated` is the one that no longer needs a carrier at all. It used to
generate `NAME: __consecrated__ = value` and let the second pass read the
consecration back off the annotation, which cost the author the annotation
slot; what the header declared now travels beside the generated Python
instead, and `consecrated PORT: int = 8080` generates exactly
`PORT: int = 8080`.

### consecrated — a binding that will not move

```
consecrated PORT: int = 8080
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

The archetype is not decoration. Chapter XII requires it of every
`consecrated` binding, and `consecrated PORT = 8080` without one is a heresy.
That the annotation slot is free to be spent this way is recent: the construct
used to reach the compiler through it.

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
rite divide(a: float, b: float) -> float:
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

*Two verbs chant. Six do not. A seventh chants only what you wrote to be
chanted. An adept who only ever chants learns of his errors from the
machine, at the hour the machine chooses. These are the rites of asking
first.*

`augur`, `transcribe`, `forge`, `consecrate`, `sanctify`, `prove` and
`purge` are the built tooling verbs. `augur` reads a litany, `transcribe`
writes one, `forge` compiles one without chanting it, `consecrate` checks
the seals across all of them, `sanctify` sets one's form in order, and
`purge` clears what chanting left behind. `prove` is the exception that
does run a litany — but only the trials you wrote to be run.

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
sixty-four. The four construct words are outside it by construction: they
are never substituted, so no binding of one can quietly come to mean
something else. `consecrated` and `unsanctioned` are still caught — by the
second check, as a compile failure — and `litany` and `augur` are genuinely
not faults. The machine's own names (Chapter VII) are within it: they have no
Python spelling to become, but a `.py` file that binds one is a file no
litany can import by that name, and the finding says so.

**That the litany compiles.** For a `.lit` file, `augur` compiles the source
after gathering collisions, so a file `augur` calls clean is a file `chant`
will accept. The two must not be able to disagree about that. This is also
why Chapter XII's archetype rule needs no line of `augur`'s own: an
undeclared parameter is a compile failure, so the second check reports it
without being taught anything.

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
++ THE OUTPUT WILL NOT CHANT AS WRITTEN ++
  greet.py:1  name is unsanctioned; every parameter must declare its archetype
Python does not require archetypes and Liturgy does. declare one for every
parameter and return and every consecrated name, or write `unsanctioned`
before a rite to exempt it -- or alone on the first line to exempt the file.
rite greet(name):
    should nay name:
        render "Ave Omnissiah"
    render f"Ave {name}"


foreach i among span(2):
    intone(greet(""))
```

The warning is Chapter XII's, and unannotated Python earns it by definition:
Python does not require archetypes and Liturgy does, so a faithful
transcription of a bare `def` is a litany that will not chant until an adept
annotates it or marks it `unsanctioned`. Nothing is prepended on the adept's
behalf — an `unsanctioned` line ahead of the litany would break the
round-trip self-check below, which is the whole reason the verb can be
trusted. Python that *was* annotated transcribes to a litany that chants, and
is not warned about at all.

Given `-o`, it writes the file instead of printing it and reports the count:

```
$ liturgy transcribe greet.py -o greet.lit
++ 8 lines transcribed ++
++ THE OUTPUT WILL NOT CHANT AS WRITTEN ++
  greet.lit:1  name is unsanctioned; every parameter must declare its archetype
Python does not require archetypes and Liturgy does. declare one for every
parameter and return and every consecrated name, or write `unsanctioned`
before a rite to exempt it -- or alone on the first line to exempt the file.
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
refused as one no litany can express. That compile asks whether the output is
a *program*, not whether it satisfies Chapter XII: the archetype rule is
suppressed for it, which is why a missing annotation is the warning above and
not a refusal here.

```
$ liturgy transcribe cons.py
++ CANNOT TRANSCRIBE: the output would not chant ++
   line 1: consecrated must be followed by a name
rewrite or rename what it names, then transcribe again
```

The same rule is applied a second time, to the Liturgy about to be written.
Transcription can introduce a collision the Python never had — `input` is
rendered `hearken`, and `hearken` is reserved. That output is not wrong: it
round-trips, and its words are faithful. So it is a warning, not a refusal:

```
$ liturgy transcribe codec.py -o codec.lit
++ 2 lines transcribed ++
++ THE OUTPUT CARRIES 1 COLLISION ++
  codec.lit:1  hearken      -> reserved (input)
augur will flag these; the words are faithful and run the same
++ THE OUTPUT WILL NOT CHANT AS WRITTEN ++
  codec.lit:1  input is unsanctioned; every parameter must declare its archetype
Python does not require archetypes and Liturgy does. declare one for every
parameter and return and every consecrated name, or write `unsanctioned`
before a rite to exempt it -- or alone on the first line to exempt the file.
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

### consecrate — the seals read across every litany

Chapter VII sets out what `consecrated` can and cannot enforce, and is exact
about the boundary: rejection happens at compile time, against the AST the
compiler can see, and enforcement is per compilation unit. A second litany
reaching in through the module object is, to the compiler, another file
entirely.

`consecrate` reads the whole tree instead of one unit at a time. It walks
twice — once to learn what is sealed, once to find what reaches a seal — and
reports the pair:

```
$ liturgy consecrate
++ THE SEAL IS BROKEN ++
   config.lit, line 1
       consecrated PORT = 8080
                   ^^^^
   PORT is consecrated here, and reached in:
     assigned  server.lit:4

++ 1 seal broken, 1 held ++
```

Three shapes are read: assignment through the module object
(`config.PORT = 9`), `setattr` with a literal name, and deletion. All three
are named plainly enough in the source for a walk to find them. A `.py` file
counts as much as a litany — it imports through the same hook, and can reach
the same attribute.

### What consecrate still cannot see

It is a report, not an enforcement. Nothing here stops a rebinding at run
time; it tells you the rebinding is written down somewhere.

Two of Chapter VII's escapes remain invisible, and are not guessed at.
`globals()["PORT"] = 9` names nothing a walk can match. Neither does
`setattr(config, name, 9)`, where the attribute is computed — the literal
form is read, the computed form is not, and reporting a maybe would make the
verb worth less than silence.

Only module-level seals are checked. A `consecrated` inside a rite is not
reachable as `module.NAME`, so no other file could breach it if it tried.

Modules are matched by basename, which is how `config.PORT` finds
`config.lit`. Two litanies sharing a basename make that ambiguous, and the
verb says so rather than reporting confidently:

```
++ config is the name of 2 litanies; seals for it are matched by basename ++
```

`--plain` emits `file:line:col:` lines for editors and CI, and nothing else:

```
$ liturgy consecrate --plain
server.lit:4:12: PORT is consecrated in config.lit line 1 and assigned here
```

The exit status is 0 when every seal held, and 1 when any was reached or any
litany could not be read.

### sanctify — a litany's form set in order

`sanctify` reshapes the whitespace between a litany's tokens and changes
nothing else. Indentation becomes four spaces to the level, trailing
whitespace goes, runs of blank lines are capped at two, and the file ends
with exactly one newline.

```
$ liturgy sanctify --check
   unclean prayer.lit
++ 1 unclean, 0 already in order ++

$ liturgy sanctify
   sanctified prayer.lit
++ 1 sanctified, 0 already in order ++
```

`--check` writes nothing and exits 1 if anything is unclean, which is the
form a chant-hall's own trials want.

Only `.lit` files are touched. Formatting Python is `ruff`'s work or
`black`'s, and neither of them can read a litany — which is the whole reason
this verb exists.

### What sanctify refuses to do

Chapter IX declined a formatter twice, and the second reason was the real
one: done improperly, it eats your source. `ast.unparse` would give a full
reformatting in three lines and drop every comment and blank line on the
way. It is not used here, and this verb re-flows no expression, re-quotes no
string, and moves no token.

Three shapes are left alone on purpose, each of which a careless formatter
gets wrong:

- **The interior of a multi-line string.** Its trailing spaces and its
  indentation are its value, not its layout.
- **A bracket continuation.** The machine emits no indentation token for
  one, and how an adept aligns a continued line is a choice.
- **A standalone comment before a block's first statement.** The machine
  reports it *before* the indentation token, so a formatter counting depth
  as it reads will indent that comment to the enclosing level and quietly
  walk it out of the block it introduces. Here such a comment takes the
  depth of the statement it belongs to.

### The guarantee, checked rather than claimed

Before returning anything, `sanctify` reads its own output back and compares
two things against the original: every token that carries meaning —
comments emphatically included — and the tree the litany compiles to. If
either differs, the verb refuses and the file is left exactly as it was.

```
++ CANNOT SANCTIFY: prayer.lit the meaning would have changed ++
```

That check is not decoration. It caught a real defect while this verb was
being written, and refused rather than writing the damaged file.

Encoding, line endings and a BOM are preserved exactly as `transcribe`
preserves them. A litany that does not parse is refused and left untouched,
and one refusal does not end the walk.

### prove — the trials of a litany

`prove` runs pytest with the import hook installed and `test_*.lit`
collected. That is the whole verb.

```
$ liturgy prove
test_rites.lit .F                                                        [100%]

=================================== FAILURES ===================================
__________________________ test_the_omnissiah_is_not ___________________________

    rite test_the_omnissiah_is_not() -> Void:
>       attest measure("cog") == 99
               ^^^^^^^^^^^^^^^^
E       AssertionError

test_rites.lit:5: AssertionError
========================= 1 failed, 1 passed in 0.01s ==========================
```

The failure quotes Liturgy — `rite`, `attest`, `measure`, at the litany's own
line number — because the loader does not override `get_source`, and pytest
reads the source the same way a traceback does.

Every argument goes straight to pytest: paths, `-k`, `-x`, `-v`, any of it.

```
$ liturgy prove -q -k pleased
.                                                                        [100%]
1 passed, 1 deselected in 0.00s
```

The exit status is pytest's own, passed through rather than flattened: 0 all
passed, 1 failures, 5 nothing collected. A runner that reported those three
alike would be worse than none.

### What prove is, and is not

It is convenience, and the chapter will not pretend otherwise. Everything
`prove` does was already available: the hook is a real one, so pytest imports
a `.lit` module like any other, and this `conftest.py` collects the trials
without any verb at all.

```python
import pytest
from liturgy.loader import install
install()

def pytest_collect_file(parent, file_path):
    if file_path.suffix == ".lit" and file_path.name.startswith("test_"):
        return pytest.Module.from_parent(parent, path=file_path)
```

`prove` supplies exactly that as a plugin. What it buys is that a project
needs no `conftest.py`, and that the way to run a litany's trials is
discoverable from `--help` rather than from this page. Chapter IX declined
the verb once for adding a layer and no capability; the layer was built
anyway, on the grounds that seven lines of boilerplate every project must
copy is itself a cost.

pytest is an optional extra. Without it the verb refuses rather than
tracebacking:

```
++ CANNOT PROVE: pytest is not installed ++
   the trials need it:  pip install 'liturgy[trials]'
```

One limitation is worth stating plainly: pytest rewrites assertions in `.py`
files to show the operands of a failed comparison, and it does not do this
for a litany. `attest measure("cog") == 99` reports `AssertionError` and the
source line, not `3 == 99`. The rewriting works on Python source pytest
itself imports, and a litany arrives already compiled by our loader.

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

## Chapter XII — The Declaration of Archetypes

*An offering laid before the machine without its nature declared is an
offering the machine must guess at, and the machine does not guess. Name the
archetype of everything you hand a rite, and of everything the rite hands
back. If you will not name it, say so aloud: an omission spoken is a
decision, and an omission unspoken is a fault.*

Python invites type hints and enforces nothing. A `def` carrying no
annotation anywhere on it is perfectly ordinary Python, and no interpreter
will ever complain. Liturgy requires them. A litany must declare the
archetype of every rite's parameters, of every rite's return, and of every
`consecrated` binding. An undeclared one is a heresy at compile time,
alongside the rest of Chapter X's rejections.

`archetype` was already Liturgy for `type`, and `pattern` already `class`, so
the vocabulary this chapter needs was spent before the rule existed. The rule
adds exactly one word, and that word is for refusing the rule.

### What the machine requires

```
rite greet(name):
    intone(f"Ave {name}")
```

```
++ MACHINE CURSE ++
   the rite was ill-written at prayer.lit, line 1
       rite greet(name):
                  ^^^^
   TechHeresy: name is unsanctioned; every parameter must declare its archetype
++ the machine spirit is displeased ++
```

Declare the parameter and the fault moves to the return, reported against the
rite's own name — the AST gives a function's name no position of its own, so
the caret is placed by hand:

```
   the rite was ill-written at prayer.lit, line 1
       rite greet(name: str):
            ^^^^^
   TechHeresy: greet is unsanctioned; a rite must declare what it renders
```

A rite that renders nothing renders `Void`, and `-> Void` is the idiomatic
way to say so:

```
rite greet(name: str) -> Void:
    intone(f"Ave {name}")
```

A `consecrated` binding is the third shape, and the fault points at the name:

```
   the rite was ill-written at prayer.lit, line 1
       consecrated PORT = 8080
                   ^^^^
   TechHeresy: PORT is unsanctioned; a consecrated name must declare its archetype
```

`consecrated PORT: int = 8080` is the cure, and it is **newly legal**. In
every version before this one it was a syntax error, for a reason that was
nobody's business but the compiler's: the construct smuggled itself through
the annotation slot, generating `PORT: __consecrated__ = 8080`, so the slot a
consecrated name needed was already occupied. Consecration travels beside the
generated Python now, and the slot is the author's again.

Nothing else is required. Plain assignments, `foreach` targets, comprehension
variables, `anointed ... styled` targets and the name a `curse` binds all go
unannotated in idiomatic Python, and demanding an archetype for each of them
would make the language tiresome rather than strict.

Every parameter position Python can annotate is required, which is all of
them: positional-only, ordinary, keyword-only, `*args` and `**kwargs`.

The rule lives in the compile path, beside the other construct rejections,
rather than in a tool of its own that might come to disagree with the
compiler. `chant`, `prove` and `augur` therefore all report it, identically,
because all three compile:

```
$ liturgy augur --plain prayer.lit
prayer.lit:1:1: TechHeresy: name is unsanctioned; every parameter must declare its archetype
```

### Presence is not correctness

**Liturgy can see that an annotation is written. It cannot see whether it is
true.**

`rite count(n: str) -> int:` satisfies this rule completely while being a lie
in both halves, and nothing in the language will ever say so. Checking that
an archetype describes the value that actually arrives is a type checker's
work, and a type checker is a different program of a different size. One has
been designed. It is not scheduled, and until it exists this page will not
imply it.

This is the same boundary Chapter VII draws around `consecrated`, drawn again
for the same reason: the word "enforced" invites more confidence than the
mechanism can support. What is enforced is that you thought about the
archetype long enough to write one down. Whether you were right is between
you and a type checker.

### What cannot be declared is exempt

Four exemptions, and each is a thing the rule could not ask for without
asking for the impossible.

**`self` and `cls`** — in the *first* positional slot of a method, and only
there. A receiver's archetype is the pattern it is declared in, and spelling
it out is noise that every Python type checker also waives. A later parameter
named `self` is an ordinary parameter wearing the name and gets no pass.

**`servitor`** — a lambda, entirely. Python has no syntax for annotating
one's parameters; `servitor x: int = 1` is not a stricter lambda, it is a
syntax error. A rule requiring what cannot be written would forbid the
construct outright, so the rule stops at the door.

**`commune`** — the prompt does not enforce. Every entry is its own
compilation unit, so there is nowhere to put an exemption that would still be
in force on the next line, and a prompt that rejects `rite f(x):` is not a
prompt anyone will use twice. Chapter VII's note about `consecrated` being
enforced per compilation unit is the precedent; this is the same boundary seen
from the other side.

```
>>> rite greet(name):
...     intone(f"Ave {name}")
...
>>> greet("adept")
Ave adept
```

**`.py` files** — Liturgy compiles `.lit`. A Python file is Python's own
business, whether a litany imports it or `augur` reads it.

### unsanctioned — the omission spoken aloud

The fifth exemption is not something the machine works out. It is something
you say, and `unsanctioned` is the word for saying it. It is the one word this
rule adds to the tongue, and it has no Python spelling at all: the transform
splices it away and records what it marked, so a litany using it compiles to
exactly the Python it would have compiled to without it.

As a **modifier** it exempts the one rite, or the one binding, it precedes:

```
unsanctioned rite legacy(x):
    render x

unsanctioned consecrated PORT = 8080
```

It reaches a `remote rite` as well — the word between the modifier and `rite`
is `async`, and an exemption that stopped at the sight of it would be a rule
about spelling rather than about rites.

**An exempted rite exempts everything nested inside it.** A closure or a
`pattern` written within an `unsanctioned` rite is exempt too. The
alternative — waiving the header and then nagging about a two-line helper
three lines below it — would make the modifier useless on exactly the old
code it exists for, and there is no second word to reach for. A nested rite
that wants the rule back can be lifted out of the exempted one.

Standing **alone on a line at the margin**, `unsanctioned` exempts the whole
litany:

```
unsanctioned

rite one(a):
    render a

rite two(b):
    render b
```

That is deliberately blunt. There is no per-line form: two granularities are
what the language offers, and a third can be argued for once the first two
have proved insufficient.

Anywhere else the word is a heresy rather than a silent no-op, because a
modifier that looks applied and is not is worse than no modifier at all:

```
unsanctioned x = 5
```

```
   TechHeresy: unsanctioned marks a rite or a consecrated name
```

```
x = unsanctioned
```

```
   TechHeresy: unsanctioned cannot stand mid-statement
```

The two positions Chapter VI spares are spared here as well: after a dot the
word is another object's attribute, and in keyword-argument position it is the
callee's parameter. Neither is a word in your litany.

Note that `Sanctioned`, with a capital S, is Liturgy for `True` and has
nothing to do with any of this. Chapter IX keeps the list of words this
project spends twice, and the pair is on it.

### Why the annotation itself gained no word

An earlier design gave the annotation operator a ritual spelling of its own —
`anoint`, then `wrought`, then `designated`. Each was cut, and the reasons are
worth keeping.

`anoint` is one letter from `anointed`, which is already `with`. Two
near-identical words in one namespace with unrelated meanings is a worse trap
than the doubled `augur` and `purge`, which live in different namespaces and
cannot collide.

Any such word also solves only half the problem. A rite's return is spelled
`->`, so `rite f(x wrought int) begets str:` needs a *second* reserved word to
stay consistent — two words for what Python spells with punctuation, and two
more names an adept may not use.

And the annotations themselves already worked. `:` and `->` have always been
legal in a litany; what was missing was the requirement, and a requirement
needs no vocabulary of its own. `archetype` is `type`, `pattern` is `class`,
and the type vocabulary is spent — spent well, and spent already.

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
