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
> `measure` (or `discern`, or any of the ten quiet words) silently shadows
> the name it aliases and fails somewhere else entirely,
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

These two run litanies; the [seven tooling verbs](#augur-transcribe-forge-consecrate-sanctify-prove-and-purge)
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

## Importing a litany from plain Python

Everything above goes through the `liturgy` command, and that is the only
place the import hook gets installed — `chant`, `commune` and `prove` each
install it on the way in. Any other Python entry point cannot see a `.lit`
file at all:

```
$ python -c "import mymod"        # mymod.lit is right there
ModuleNotFoundError: No module named 'mymod'
```

If you want `.lit` importable from an ordinary `python`, a web server, a
notebook, or anything else that is not our CLI, install the hook into the
environment with a `.pth` file. Python executes any line in a `.pth` that
starts with `import`, at interpreter start:

```bash
echo 'import liturgy.loader; liturgy.loader.install()' > "$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')/liturgy-hook.pth"
```

After that, litanies import like anything else:

```
$ python -c "import mymod; print(mymod.greet())"
ave, Omnissiah
```

Delete the file to undo it — there is no other state, and the previous
behaviour comes straight back.

Three things to know before you do this:

- **It costs every interpreter start in that environment**, whether or not
  litanies are involved — about 10-20ms here, mostly `importlib.metadata`.
  A bare `python -c "pass"` went from ~0.02s to ~0.03s.
- **It is per-environment**, and it writes into site-packages. Do it in a
  virtualenv, not a system Python.
- **It gets you imports, not test collection.** Plain `pytest` still reports
  `no tests ran` for a `test_*.lit`, because collection is a separate hook
  from importing. Use [`prove`](#prove--run-a-litanys-trials), or the
  `conftest.py` it replaces.

There is no verb for this. `anoint` was the obvious name and is deliberately
still unspent — see [What's not built yet](#whats-not-built-yet).

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

One family of names is reserved beyond the tables below: `__consecrated__`,
`__litany__`, `__augur__` and anything beginning `__liturgy_` — the private
carriers and bookkeeping the construct compiler writes into generated code.
A litany that spelled one would be indistinguishable from the machinery, so
using one anywhere but after a dot is a loud compile error rather than a
silent rewrite.

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
of retries. `curse=` names what to catch and is required and keyword-only
(spelled out — not passed through `**`), so nothing is caught by accident;
`resting=` is optional and, left out,
pauses for nothing between attempts. Count and resting are each evaluated
once and guarded up front — a count below one or a negative resting is
rejected at compile time as a literal, before the first attempt otherwise.
`cease`/`persist` written at the
litany's own level are rejected at compile time — they would bind to the
retry loop the construct generates, not anything you wrote — but the same
words inside a real loop in the body are fine.

`augur:` is a set of bare conditions, one per line, allowed only at the
opening of a rite (a docstring may come first). A statement, a constant, or
a walrus in the block is rejected at compile time; a call is a condition,
judged by the truth of what it renders. It is a contract, not an
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

Pass `--absolved` — before or after the verb, as you like — to suppress the
rebuke for a single invocation:

```
$ liturgy --absolved run hello.lit
Ave Omnissiah
```

or set `LITURGY_PIOUS=0` in the environment to suppress it everywhere (it
must be exactly `"0"` — `false`, empty, or anything else still counts as
impious). Calling a rite by its proper name, `chant` or `commune`, never
triggers a rebuke in the first place.

## `augur`, `transcribe`, `forge`, `consecrate`, `sanctify`, `prove` and `purge`

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

`augur` makes exactly two checks. First, every binding whose name is one of
the sixty words that become another word, by either route: you wrote the
reserved word and it was substituted, or an exemption protected the word and
you are now bound to it unsubstituted. (A `.py` file binding one of the
machine-reserved dunders above is reported under this check too — a litany
could never import it by that name.) Second, for a `.lit` file, that it
actually compiles, so `augur` and `chant` cannot disagree about whether a file
is well-formed.

The three construct words are outside the first check and belong outside it:
they are never substituted, so a binding of one cannot quietly come to mean
something else. `consecrated = 5` is caught anyway, by the second check, as a
compile failure. `litany = 5` and `augur = 6` are reported by neither, because
neither is a fault — the name is yours until the day you want the construct on
that line.

It stops there on purpose. There is no line-length rule, no unused-import
check, no naming convention — `augur` is not a general linter and is not
going to grow into one. It reports the class of fault that is specific to
Liturgy, which is the class no other tool in your setup can see.

Arguments may be files or directories; a directory is walked for `.lit` and
`.py` files, pruning the usual noise — dot-directories, `__pycache__`, and
anything holding a `pyvenv.cfg`, so a vendored virtual environment does not
drown real findings under third-party code. A directory you name directly is
always read, hidden or not, and overlapping arguments report each finding
once. Exit status is 0 when nothing was reported and 1 when anything
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

The rule is applied to the output as well, as a warning rather than a
refusal. Rendering Python into Liturgy can *introduce* a collision the source
never had — `def encode(self, input)` becomes `rite encode(self, hearken)`,
and `hearken` is reserved. The file is correct and chants exactly as the
Python ran, so it is written; `transcribe` just says what `augur` will say
about it, instead of leaving you to find out:

```
$ liturgy transcribe codec.py -o codec.lit
++ 2 lines transcribed ++
++ THE OUTPUT CARRIES 1 COLLISION ++
  codec.lit:1  hearken      -> reserved (input)
augur will flag these; the litany is correct and chants as written
```

Writing to stdout instead, the warning goes to stderr, so a redirected file
gets the litany and nothing else.

Before anything reaches disk it round-trips its own output: the generated
Liturgy is transformed back to Python and compared against the source, and if
the two differ, nothing is written and the failure is reported as a fault in
Liturgy rather than in your file. The output is also compiled, so a Python
program no litany can express — one binding a bare `consecrated`, or using a
machine-reserved dunder — is refused as "the output would not chant" instead
of written broken. A destination file gets a second, byte-level
round-trip in the source's own declared encoding. Line endings and a PEP 263
`coding:` cookie are preserved, so the output differs from the input in its
words and in nothing else.

### `forge` — compile litanies to bytecode

`forge` compiles `.lit` files to bytecode ahead of the import that would
otherwise do it. With no paths it walks the working directory; with paths it
takes those.

```
$ liturgy forge
   forged mod.lit
   forged sub/two.lit
++ 2 litanies forged ++
```

Only `.lit` files are forged — `.py` to `.pyc` is `compileall`'s job, and
Liturgy adds nothing to it.

**It does not execute what it compiles.** That is the difference between
forging a litany and importing one, and it means a litany whose top level
prints or writes files can be forged safely. The compile runs through the
import system's own `get_code`, so the bytecode is byte-for-byte what an
import would have produced and CPython decides whether an existing cache is
still valid.

A second run reports rather than repeats:

```
$ liturgy forge
++ 0 litanies forged, 2 already current ++
```

That distinction is measured, not guessed — the cache file's mtime is read
either side of the compile, and only a change counts as a forging. `--anew`
forges regardless.

Bytecode is written as ordinary `.pyc` under `__pycache__`. A themed `.litc`
extension was considered and rejected: `SourceLoader.get_code` calls
`cache_from_source` as a module-level function rather than a method, so a
subclass cannot redirect it, and changing the extension would mean
reimplementing ~84 lines of private `importlib._bootstrap_external` machinery
and maintaining that fork across every supported Python. The extension is
cosmetic; the loader it would destabilise is what makes tracebacks quote
Liturgy. Standard `.pyc` also means `purge` and `.gitignore` keep working
untouched.

Under `-B` or `PYTHONDONTWRITEBYTECODE` every cache write is discarded, so
forging would report success and produce nothing. It refuses instead:

```
++ CANNOT FORGE: this interpreter will not write bytecode ++
   -B or PYTHONDONTWRITEBYTECODE is in force
```

A litany that will not compile is named with its line, and the walk
continues:

```
++ CANNOT FORGE: broken.lit line 1 SyntaxError: 'return' outside function (render is Liturgy for return) ++
++ 0 litanies forged, 2 already current ++
```

Exit status is 0 when everything was forged or already current, 1 if the
interpreter refused the run or any single litany failed.

### `consecrate` — check consecrated names across the tree

`consecrated` is enforced per compilation unit, so the compiler cannot see a
rebinding that arrives from another file. `consecrate` walks the tree twice —
once to learn what is sealed, once to find what reaches a seal — and reports
the pair.

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
(`config.PORT = 9`), `setattr` with a literal name, and deletion. A `.py`
file counts as much as a litany — it imports through the same hook and can
reach the same attribute.

**It is a report, not an enforcement.** Nothing here stops a rebinding at run
time. Two of the escapes named in the disclaimer stay invisible and are not
guessed at: `globals()["PORT"] = 9` names nothing a walk can match, and
neither does `setattr(config, name, 9)` with a computed attribute. The
literal form is read; the computed form is not.

Only module-level seals are checked — a `consecrated` inside a rite is not
reachable as `module.NAME`, so nothing outside the file could breach it.
Modules are matched by basename, and two litanies sharing one are called out
rather than reported on confidently:

```
++ config is the name of 2 litanies; seals for it are matched by basename ++
```

`--plain` emits `file:line:col:` lines for editors and CI, and nothing else:

```
$ liturgy consecrate --plain
server.lit:4:12: PORT is consecrated in config.lit line 1 and assigned here
```

Exit status is 0 when every seal held, 1 when any was reached or any litany
could not be read.

### `sanctify` — set a litany's form in order

`sanctify` reshapes the whitespace between tokens and nothing else:
indentation to four spaces per level, trailing whitespace gone, blank-line
runs capped at two, exactly one final newline.

```
$ liturgy sanctify --check
   unclean prayer.lit
++ 1 unclean, 0 already in order ++

$ liturgy sanctify
   sanctified prayer.lit
++ 1 sanctified, 0 already in order ++
```

`--check` writes nothing and exits 1 if anything is unclean — the shape CI
wants. Only `.lit` files are touched; formatting Python is ruff's or black's
job, and neither can read a litany, which is why this exists.

**It does not use `ast.unparse`.** That would reformat everything in three
lines and drop every comment and blank line on the way. Nothing here
re-flows an expression, re-quotes a string, or moves a token.

Three shapes are deliberately left alone, each one a thing a careless
formatter gets wrong:

- **A multi-line string's interior** — its trailing spaces and indentation
  are its value.
- **A bracket continuation** — `tokenize` emits no `INDENT` for one, and the
  author's alignment is a choice.
- **A standalone comment before a block's first statement** — `tokenize`
  reports it *before* the `INDENT`, so a running depth counter indents it to
  the enclosing level and silently walks it out of the block it introduces.

**The guarantee is checked, not claimed.** Before returning, `sanctify`
re-reads its own output and compares the significant token stream (comments
included) and the compiled AST against the original. If either differs it
refuses and leaves the file untouched:

```
++ CANNOT SANCTIFY: prayer.lit the meaning would have changed ++
```

That check caught a real defect during development rather than writing a
damaged file. Swept over the stdlib corpus, 574 files sanctified with zero
non-idempotent results; the 50 refusals were all files that do not parse as
Liturgy.

Encoding, line endings and BOM are preserved as `transcribe` preserves them.

### `prove` — run a litany's trials

`prove` runs pytest with the import hook installed and `test_*.lit`
collected. That is the whole verb.

```
$ liturgy prove
test_rites.lit .F                                                        [100%]

=================================== FAILURES ===================================
__________________________ test_the_omnissiah_is_not ___________________________

    rite test_the_omnissiah_is_not():
>       attest measure("cog") == 99
               ^^^^^^^^^^^^^^^^
E       AssertionError

test_rites.lit:5: AssertionError
========================= 1 failed, 1 passed in 0.01s ==========================
```

Failures quote Liturgy at the litany's own line number, because the loader
does not override `get_source` and pytest reads it the same way a traceback
does.

Every argument passes straight through to pytest — paths, `-k`, `-x`, `-v`:

```
$ liturgy prove -q -k pleased
.                                                                        [100%]
1 passed, 1 deselected in 0.00s
```

Exit status is pytest's own, unflattened: 0 all passed, 1 failures, 5 nothing
collected.

**This is convenience, not capability, and the README will not pretend
otherwise.** Everything `prove` does was already reachable with a
`conftest.py` that calls `install()` and adds a `pytest_collect_file` for
`test_*.lit`. `prove` supplies that as a plugin so no project needs the
boilerplate, and so the answer is in `--help` rather than in the docs.

pytest is an optional extra; without it the verb refuses rather than
tracebacking:

```
++ CANNOT PROVE: pytest is not installed ++
   the trials need it:  pip install 'liturgy[trials]'
```

One limitation worth knowing: pytest rewrites assertions in `.py` files to
show the operands of a failed comparison, and does not do so for a litany.
`attest measure("cog") == 99` reports `AssertionError` and the source line,
not `3 == 99` — the rewriting works on Python source pytest imports itself,
and a litany arrives already compiled by our loader.

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

## Syntax highlighting

Two highlighters ship with the repository, one exact and one approximate.

**Pygments** (exact). The package carries an optional lexer, registered under
the names `liturgy` and `lit` and claiming `*.lit`:

```
$ pip install -e ".[highlight]"
$ pygmentize examples/fibonacci.lit
```

It is driven by the compiler's own token passes rather than a keyword regex,
so the three prohibitions hold in the colours exactly as they hold in the
transform: `template.render()` paints `render` as a plain attribute,
`func(intone=True)` a plain keyword argument, an invocation's targets stay
the module's own, and `litany = 5` is your name while `litany(...):` is a
construct header. The machine's own names paint as errors. Highlighting is
not a linter, though — `span = 1` still paints `span` as the builtin it
becomes; `augur` is the verb that judges bindings.

**VS Code** (approximate). A TextMate grammar lives in
[`editors/vscode-liturgy`](editors/vscode-liturgy/); its README covers
installation (a `vsce package` or a symlink — it is not on the marketplace)
and lists the places where a line-based grammar can only approximate the
transform's context rules. `tests/test_grammar.py` holds its word lists to
the lexicon, so a new reserved word cannot ship without joining the grammar.

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
  File "/Users/messagematrix/workspace/laboratory/tech-priest-liturgy/src/liturgy/cli.py", line 113, in main
    return _chant(args.file, args.args)
  File "/Users/messagematrix/workspace/laboratory/tech-priest-liturgy/src/liturgy/loader.py", line 128, in chant
    exec(compile_litany(src, path), module.__dict__)
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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
constructs above. Spec III is the CLI verb surface, and seven of its eight
verbs — `augur`, `transcribe`, `forge`, `consecrate`, `sanctify`, `prove`,
`purge` — are built and documented above.

One name is still nothing but a name the command line refuses to hand to
anything else:

- **`anoint`** — reserved as flavour. There is still no feature behind it,
  only a good word nobody wanted a later contributor to spend on something
  trivial. It is held, not planned, and holding it is the point: an unspent
  name is worth more than one spent on something trivial. `forge` and
  `consecrate` were reserved the same way until features turned up for them,
  and `prove` and `sanctify` were each declined on their merits before being
  built on better terms.

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
