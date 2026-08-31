# Liturgy

Liturgy is a superset of Python whose surface syntax is the ritual language
Warhammer 40,000 tech-priests use to address machine spirits. `if` becomes
`should`, `def` becomes `rite`, `except` becomes `curse`, and so on for every
keyword Python has — but underneath, it is still Python. A `.lit` file
tokenizes, has its keywords aliased back to their Python spellings, and
compiles exactly the way a `.py` file would, so everything you already know
about control flow, closures, exceptions, and the rest of the language
carries over unchanged.

The joke is the reason to start, but it is not really the point. Doing it
honestly — matching line numbers in tracebacks, correct column carets under a
syntax error, an import hook that behaves like a real one, a REPL that can
tell "unfinished" apart from "wrong" — turns into a fairly thorough tour of
how CPython actually loads and runs source. That tour is the part worth the
time.

> ## Do not use this in production
>
> Liturgy is a toy, built for fun and for the excuse it gave to go rummaging
> around in CPython's import machinery. It is not a serious language and it is
> not maintained as one.
>
> It is **incomplete** — the third of three planned specs is three verbs
> into an eight-verb surface, and five of those names are still nothing but
> reserved words.
>
> It is **breakable**. Some of it is documented: naming a variable `span` or
> `measure` silently shadows a builtin and fails somewhere else entirely,
> `consecrated` cannot stop `setattr` or `globals()`, and any word Liturgy
> reserves is a word your program may not use as an identifier. `augur` will
> now find that first class of sharp edge for you, which is not the same as
> the sharp edge not being there. The rest is the ordinary risk of a project
> written in a few days by one person and reviewed by nobody who has to live
> with it.
>
> Run it on prayers you would not mind losing.

## Ave Omnissiah

Save this as `hello.lit`:

```
intone("Ave Omnissiah")
```

then:

```
$ liturgy chant hello.lit
Ave Omnissiah
```

`intone` is Liturgy for `print`. `chant` is Liturgy for "run this file."

## Installation

Liturgy needs Python 3.12 or later — see [why](#why-python-312) below — and
has no runtime dependencies of its own.

```
$ git clone git@github.com:Another-workation-farang/tech-priest-liturgy.git
$ cd tech-priest-liturgy
$ python3.12 -m venv .venv
$ source .venv/bin/activate
$ pip install -e .
```

That installs the `liturgy` console script.

## `chant` and `commune`

These two run litanies; the [three tooling verbs](#augur-transcribe-and-purge)
further down read, translate and tidy them. `chant <file.lit> [args...]`
executes a Liturgy file the way
`python file.py` executes a Python one: the file becomes `__main__`,
`sys.argv` is set up the same way, and a plain `should __name__ == "__main__":`
block at the bottom works exactly as expected (see `examples/fibonacci.lit`).

`commune` opens an interactive session — Liturgy's REPL:

```
$ liturgy commune
++ COMMUNION ESTABLISHED ++
++ cogitator 3.14.7 attends your litanies ++
>>> intone("Ave Omnissiah")
Ave Omnissiah
>>>
++ communion ended. the Omnissiah is served. ++
```

(exit with Ctrl-D.) It handles multi-line input the same way the standard
REPL does — an open `should` block or an unclosed bracket just waits for the
rest, rather than complaining.

## The superset promise

> **All valid Python is valid Liturgy, except programs that use a Liturgy word
> as an identifier.** Liturgy reserves more words than Python does.

That second sentence is the entire mechanism. Aliasing runs one direction
only, Liturgy word to Python word, so `print` and `def` still work fine
inside a `.lit` file — nothing stops you from writing plain Python if you
want to. The only way to break is to use one of Liturgy's own words — `rite`,
`should`, `intone`, and the rest of the table below — as a variable,
function, or class name, the same way ordinary Python won't let you name
something `def`.

Three exceptions keep this from breaking on real code you do not control:

- A word immediately after a `.` is never substituted, so `template.render()`
  stays `template.render()` instead of becoming `template.return()`.
- A word in keyword-argument position (`name=`) inside a call is never
  substituted, so `func(intone=True)` does not turn into `func(print=True)`.
- Inside `import` / `from` statements, only the statement's own keywords are
  substituted — `from jinja2 import render` is left alone, not mangled into
  `... import return`.

Those three rules exist because you control your own identifiers, but you do
not control a library's.

## The lexicon

### Keywords

Every one of Python's 35 keywords, plus its 3 soft keywords (`match`, `case`,
`type`), has a Liturgy name. This table is exhaustive — there is no Python
keyword left in its original spelling.

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

### Builtins

A deliberately short list of aliased builtins. Each addition here widens the
set of words a Liturgy program cannot use as an identifier, so growth is
treated as a considered act rather than a reflex:

| Liturgy | Python |
|---|---|
| `intone` | `print` |
| `measure` | `len` |
| `span` | `range` |
| `unseal` | `open` |
| `hearken` | `input` |

### Numerals

Two spelled-out numbers, useful chiefly as a `litany`'s attempt count:

| Liturgy | Python |
|---|---|
| `twice` | `2` |
| `thrice` | `3` |

### Exceptions

Built-in exception types get names too, both for `curse ... styled` (Python's
`except ... as`) clauses and for how a machine curse prints an unhandled
exception's type:

| Liturgy | Python |
|---|---|
| `MachineCurse` | `Exception` |
| `PrimalCurse` | `BaseException` |
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

## The three constructs

Spec II adds three things Python has no name for. Save this as
`constructs.lit`:

```
consecrated MAX_ATTEMPTS = 3


rite divide(a, b):
    augur:
        b be nay Void
        b != 0
    render a / b


rite flaky(attempts):
    attempts.append(1)
    proclaim MotiveFailure("the spirit is silent")


rite main():
    intone(f"++ 6 / 2 is {divide(6, 2)} ++")

    attempt:
        divide(1, 0)
    curse ImpureOffering styled omen:
        intone(f"++ {omen} ++")

    seen = []
    attempt:
        litany(MAX_ATTEMPTS, resting=0, curse=MotiveFailure):
            flaky(seen)
    curse MotiveFailure:
        intone(f"++ attempts: {measure(seen)} ++")


should __name__ == "__main__":
    main()
```

```
$ liturgy chant constructs.lit
++ 6 / 2 is 3.0 ++
++ the omens forbid it -- b != 0 ++
++ attempts: 3 ++
```

`consecrated NAME = value` is a binding the compiler will not let you
rebind: a second assignment, a second `consecrated` of the same name, and a
`consecrated` inside a loop body are all rejected at compile time. The
limitation is real and worth stating plainly: what the compiler cannot see,
it cannot stop. `setattr`, `globals()`, assignment through the module
object, and `exec` all get through. This is enforcement, not a guarantee.

`litany(thrice, resting=2, curse=TimeoutError):` re-chants its body when it
raises. The first argument is the *total* number of attempts, not the number
of retries. `curse=` names what to catch and is required and keyword-only,
so nothing is caught by accident; `resting=` is optional and, left out,
pauses for nothing between attempts. `cease`/`persist` written at the
litany's own level are rejected at compile time — they would bind to the
retry loop the construct generates, not anything you wrote — but the same
words inside a real loop in the body are fine.

`augur:` is a set of bare conditions, one per line, allowed only at the
opening of a rite (a docstring may come first). It is a contract, not an
assertion — it survives `-O` — and a failing condition raises
`ImpureOffering` with a message that quotes the *Liturgy* source of the
condition that failed, not the compiled Python. It is not a
Liturgy-specific exception class because the no-runtime rule holds here too:
generated code imports nothing from Liturgy.

A fourth construct, `noospheric` — a process-wide registry — was designed
alongside these three but cut rather than built: it is a service locator,
and with no runtime, it had nowhere clean to live.

## Heresy: calling the rite by its mundane name

`chant` and `commune` have plain-English aliases, `run` and `repl`, because
muscle memory is muscle memory. Using them works, but each invocation is
logged and rebuked, and the rebuke escalates:

```
$ liturgy run hello.lit
++ TECH-HERESY DETECTED ++
++ this rite is named CHANT. the omission is noted. ++
Ave Omnissiah
$ liturgy run hello.lit
++ TECH-HERESY DETECTED ++
++ this rite is named CHANT. the transgression is recorded in your permanent record. ++
Ave Omnissiah
$ liturgy run hello.lit
++ TECH-HERESY DETECTED ++
++ this rite is named CHANT. the Inquisition has been notified. ++
Ave Omnissiah
```

It saturates there — a fourth invocation gets the same "Inquisition" rebuke,
not a fourth escalation. The count lives in a small state file
(`$XDG_STATE_HOME/liturgy/heresies.json`, or `~/.local/state/liturgy/heresies.json`
if that variable is unset), so it persists across runs; losing an increment
to a concurrent write would only affect the joke, not correctness.

Pass `--absolved` to suppress the rebuke for a single invocation:

```
$ liturgy --absolved run hello.lit
Ave Omnissiah
```

or set `LITURGY_PIOUS=0` in the environment to suppress it everywhere (it
must be exactly `"0"` — `false`, empty, or anything else still counts as
impious). Calling a rite by its proper name, `chant` or `commune`, never
triggers a rebuke in the first place.

## `augur`, `transcribe` and `purge`

Three tooling verbs are built. They do not run your litany; they read it,
translate into it, or clean up after it.

### `augur` — read a litany for faults without chanting it

`augur` exists for the failure mode the disclaimer at the top of this file
and the superset promise above both warn about: a Liturgy word used as your
own name. Most of those are loud, but `span = "text range"` compiles, runs,
and shadows `range` for the rest of the program. Nothing complains until
something else calls `span(10)` and gets a string back. This is the thing
that complains at the right moment:

```
$ liturgy augur quiet.lit
++ THE OMENS ARE TROUBLED ++
   quiet.lit, line 1
       span = "text range"
       ^^^^
   span is reserved; it becomes range -- silently
```

`--plain` emits one parseable line per finding, for an editor or a CI log:

```
$ liturgy augur --plain quiet.lit
quiet.lit:1:1: span is reserved; it becomes range -- silently
```

The trailing `-- silently` marks the dangerous half of the finding: the
substitution target is an ordinary name rather than a Python keyword, so the
file compiles and the damage is deferred. Without it, the collision is loud
somewhere — still worth reporting, but it will announce itself.

`augur` makes exactly two checks. First, every binding whose name is a
reserved word, by either route: you wrote the reserved word and it was
substituted, or an exemption protected the word and you are now bound to it
unsubstituted. Second, for a `.lit` file, that it actually compiles, so
`augur` and `chant` cannot disagree about whether a file is well-formed.

It stops there on purpose. There is no line-length rule, no unused-import
check, no naming convention — `augur` is not a general linter and is not
going to grow into one. It reports the class of fault that is specific to
Liturgy, which is the class no other tool in your setup can see.

Arguments may be files or directories; a directory is walked for `.lit` and
`.py` files. Exit status is 0 when nothing was reported and 1 when anything
was. A directory reached through a symlink is named rather than skipped in
silence, because a linter that quietly does not read a file is worse than no
linter.

### `transcribe` — render a Python file into Liturgy

```
$ liturgy transcribe greet.py
rite greet(name):
    should nay name:
        render "Ave Omnissiah"
    render f"Ave {name}"


foreach i among span(2):
    intone(greet(""))
```

With `-o`, it writes instead of printing:

```
$ liturgy transcribe greet.py -o greet.lit
++ 8 lines transcribed ++
```

`transcribe` refuses rather than producing something subtly wrong. It refuses
a source that does not parse, and it refuses a source that binds a name
Liturgy reserves — because there is no correct Liturgy spelling of a program
whose variable is called `span`:

```
$ liturgy transcribe shadow.py
++ CANNOT TRANSCRIBE: 1 COLLISION ++
  shadow.py:1  span         -> reserved (range)
rename these, then chant again
```

That is the same collision rule `augur` reports, from the same code, so the
two verbs cannot drift apart about what counts.

Before anything reaches disk it round-trips its own output: the generated
Liturgy is transformed back to Python and compared against the source, and if
the two differ, nothing is written and the failure is reported as a fault in
Liturgy rather than in your file. A destination file gets a second, byte-level
round-trip in the source's own declared encoding. Line endings and a PEP 263
`coding:` cookie are preserved, so the output differs from the input in its
words and in nothing else.

### `purge` — clear generated caches

`purge` removes every `__pycache__` directory beneath the working directory,
and with `--heresies`, the heresy state file as well.

It is the only verb that deletes anything, so it is guarded: it refuses
outright unless the tree holds at least one `.lit` file, on the grounds that a
recursive delete launched from the wrong directory is a bad afternoon.

```
   no .lit file found; refusing to delete anything
```

Symlinked directories are never entered. Each removal is reported on its own
line, naming the directory, and that line is printed only after the delete has
actually succeeded — the report never claims a deletion that did not happen. A
directory that cannot be removed is reported and skipped rather than aborting
the run, so one unreadable cache does not strand the rest; the run still ends
with a count of what went:

```
++ 0 relics purged ++
```

Exit status is 0 when everything asked for went, and 1 if the guard refused or
any single removal failed.

## When a rite breaks

An unhandled exception in a `.lit` file does not print a Python traceback by
default — it prints a machine curse, using Liturgy's names for both the
exception type and the frame:

```
$ liturgy chant examples/bad.lit
++ MACHINE CURSE ++
   the rite was broken at the threshold of /Users/messagematrix/workspace/laboratory/tech-priest-liturgy/examples/bad.lit, line 1
       intone(1 / 0)
              ^^^^^
   DivisionByTheVoid: division by zero
++ the machine spirit is displeased ++
```

(`liturgy` always resolves the file to an absolute path before running it,
which is why the path above is not simply `bad.lit`; on your machine it will
be wherever you put the file.) The line and the caret position are exact —
Liturgy keeps a column-level source map from the token-substitution pass
specifically so this works, even though, say, `render` and `return` are
different lengths.

Frames from Liturgy's own launcher machinery — the loader, the console-script
entry point — are dropped, so the curse starts at your code. Anything further
down the stack that isn't a `.lit` frame, stdlib or third-party, prints as an
ordinary Python frame, untouched; only `.lit` frames get the treatment.

Sometimes you want the plain traceback back — to paste into a bug report, or
to grep for a real exception class name. `--profane`, or `LITURGY_PROFANE=1`
in the environment, gives you an ordinary Python traceback instead:

```
$ liturgy --profane chant examples/bad.lit
Traceback (most recent call last):
  File "/Users/messagematrix/workspace/laboratory/tech-priest-liturgy/.venv/bin/liturgy", line 6, in <module>
    sys.exit(main())
             ~~~~^^
  File "/Users/messagematrix/workspace/laboratory/tech-priest-liturgy/src/liturgy/cli.py", line 74, in main
    return _chant(args.file, args.args)
  File "/Users/messagematrix/workspace/laboratory/tech-priest-liturgy/src/liturgy/loader.py", line 102, in chant
    exec(compile(py, path, "exec", dont_inherit=True), module.__dict__)
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/messagematrix/workspace/laboratory/tech-priest-liturgy/examples/bad.lit", line 1, in <module>
    intone(1 / 0)
          ^^^^^
ZeroDivisionError: division by zero
```

## Why Python 3.12

This is not an arbitrary floor. Liturgy substitutes keywords at the token
level, and starting with Python 3.12 (PEP 701) the tokenizer emits real
`NAME` tokens for the interpolated parts of an f-string, so
`f"{measure(x)}"` substitutes correctly — `measure` genuinely is code there,
and the surrounding literal text is a separate, untouched token. (The closing
line of `examples/fibonacci.lit` does exactly this, with `measure` counting
the numbers recited.) Before 3.12,
the tokenizer treats an entire f-string as one opaque `STRING` token, so the
same substitution silently does nothing. Supporting both Python versions
would mean the same piece of source means two different things depending on
which interpreter ran it, and that is not a trade-off worth making. Liturgy
requires Python >= 3.12.

## What's not built yet

Spec I gets you alias-only Liturgy: writing, running, and debugging `.lit`
files with an honest import hook and honest tracebacks. Spec II adds the three
constructs above. Spec III is the CLI verb surface, and three of its eight
verbs — `augur`, `transcribe`, `purge` — are built and documented above.

The other five are still nothing but names the command line refuses to hand
to anything else:

- **`prove`** (test runner) — pytest already runs `.lit` tests, because the
  import hook is a real one. A few lines of `conftest.py` — `install()`, plus a
  `pytest_collect_file` that hands `pytest.Module` any `test_*.lit` — is
  enough to collect them directly, failures quoting the Liturgy source and
  all. A Liturgy-branded wrapper around that would add a layer and no
  capability.
- **`sanctify`** (formatter) — a formatter is its own project. Doing it
  properly means a full-fidelity round-trip through comments, blank lines and
  string quoting, and doing it improperly means a tool that eats your source.
  Neither is a weekend.
- **`forge`**, **`consecrate`**, **`anoint`** — reserved as flavour. There
  was never a feature behind them, only three good words nobody wanted a
  later contributor to spend on something trivial. They are held, not
  planned.

Two names are reused deliberately across the two namespaces, and it is worth
saying so plainly rather than letting it confuse anyone later: `augur` is both
a Spec II source construct (preconditions) and the Spec III CLI verb (lint),
and `purge` is both a Spec I keyword alias for `del` and the Spec III CLI verb
(clearing caches). A source keyword and a CLI verb cannot actually collide
with each other — they live in entirely different namespaces — but the same
word meaning two different things in the same project is exactly the kind of
thing worth spelling out instead of leaving implicit.

The full design is in
[`design/specs/2026-08-30-liturgy-core-design.md`](design/specs/2026-08-30-liturgy-core-design.md);
the task-by-task implementation plan for Core is in
[`design/plans/2026-08-30-liturgy-core.md`](design/plans/2026-08-30-liturgy-core.md).
