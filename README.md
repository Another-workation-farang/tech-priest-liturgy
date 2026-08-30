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
$ git clone <url-of-this-repository>
$ cd tech-priest-liturgy
$ python3.12 -m venv .venv
$ source .venv/bin/activate
$ pip install -e .
```

That installs the `liturgy` console script.

## `chant` and `commune`

Two verbs exist. `chant <file.lit> [args...]` executes a Liturgy file the way
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
and the surrounding literal text is a separate, untouched token. Before 3.12,
the tokenizer treats an entire f-string as one opaque `STRING` token, so the
same substitution silently does nothing. Supporting both Python versions
would mean the same piece of source means two different things depending on
which interpreter ran it, and that is not a trade-off worth making. Liturgy
requires Python >= 3.12.

## What's not built yet

This is Spec I of three — Core. It gets you alias-only Liturgy: writing,
running, and debugging `.lit` files with an honest import hook and honest
tracebacks. Two more specs are designed but not implemented:

- **Spec II — constructs.** An AST-level pass adding four things Python has
  no name for: `consecrated` (a constant that is actually enforced, not just
  a naming convention), `litany` (a retry block), `augur` (precondition
  contracts on a rite's arguments), and `noospheric` (a process-wide
  registry).
- **Spec III — tooling.** A CLI verb surface: `augur` (lint), `prove` (test
  runner), `sanctify` (formatter), `transcribe` (translate plain Python into
  Liturgy), plus `forge`, `consecrate`, `purge`, and `anoint`. Core already
  reserves all eight names on the command line, so Spec III has nowhere left
  to collide.

Two of those names are reused deliberately across the two namespaces, and it
is worth saying so plainly rather than letting it confuse anyone later:
`augur` is both a Spec II source construct (preconditions) and a Spec III CLI
verb (lint), and `purge` is both a Spec I keyword alias for `del` and a
Spec III CLI verb (clearing caches). A source keyword and a CLI verb cannot
actually collide with each other — they live in entirely different
namespaces — but the same word meaning two different things in the same
project is exactly the kind of thing worth spelling out instead of leaving
implicit.

The full design is in
[`docs/superpowers/specs/2026-08-30-liturgy-core-design.md`](docs/superpowers/specs/2026-08-30-liturgy-core-design.md);
the task-by-task implementation plan for Core is in
[`docs/superpowers/plans/2026-08-30-liturgy-core.md`](docs/superpowers/plans/2026-08-30-liturgy-core.md).
