# Liturgy Anoint: Design

**Date:** 2026-11-07
**Status:** Approved
**Scope:** Spec VI. Specs I to IV are built and merged; Spec V (archetype
truth) is scheduled. This spec spends `anoint`, the last reserved CLI verb.
A second step, the audible Binharic Chant, is designed separately and is out
of scope here.

## Purpose

Tech-priests do not hand each other litanies. A litany is how a priest writes
to the machine; the machine keeps its own tongue. `anoint` renders a litany
into that tongue: a native executable, one file, that runs on a machine with
no Python and no Liturgy installed and can be passed around like any other
program.

Speed is not the point. Nuitka compiles to C and may run some code faster,
but the documentation must not promise it, and nothing in this spec is judged
by it.

The executable must still curse like a litany. When it fails, it renders a
machine curse naming the `.lit` file, the `.lit` line, the litany source line
and the ritual name of the error, exactly as `liturgy chant` would, without
importing anything from Liturgy at runtime.

## What the user sees

```
$ liturgy anoint hymn.lit
++ ANOINTING hymn.lit ++
   4 litanies rendered, the machine tongue is being forged
++ hymn.lit IS ANOINTED: ./hymn ++
$ ./hymn
...
```

- **Input:** one `.lit` file, the program's entry point.
- **Output:** one executable. By default it is named after the litany's stem
  and written next to it (`hymn`, or `hymn.exe` on Windows). `-o/--out PATH`
  chooses another path, as `transcribe` already does.
- **Nothing else is left behind.** Nuitka's build folders and the staged
  Python live in a temporary directory that is removed afterwards, whether the
  build succeeded or failed.

*(Correction, post-review: the output path is checked more strictly than
"replaces an existing file". `-o` naming an existing directory is refused
(`++ CANNOT ANOINT: {dest} is a directory ++`), `-o` naming one of the
litany's own gathered `.lit` or `.py` sources is refused
(`++ CANNOT ANOINT: {dest} is one of the litany's own sources ++`), and an
output directory that does not exist is refused (`{dir} does not exist`).
Each refusal happens before anything is built, so nothing is destroyed. The
status lines as built also differ from the sketch above in two details: the
second reads `2 litanies rendered; the machine tongue is being forged`, with
a semicolon, and the last prints the output's absolute path, not `./hymn`.)*
- The exact wording of the status lines is the builder's call, in the house
  style of the other verbs (`++ ... ++` banners, `CANNOT ANOINT` on refusal).
- **Nuitka's own output streams through, between anoint's banners.** It is
  not captured or hidden. Capturing it would swallow Nuitka's questions (it
  asks before downloading a compiler) and leave the user at what looks like a
  hang, and it would hide Nuitka's warnings about imports it could not find,
  which are the only early sign of an executable that will fail at run time.
  *(My call, after the builder check.)*

## Dependency

Nuitka is an optional extra, `liturgy[anoint]`, alongside `archetypes`,
`highlight` and `trials`. The core keeps `dependencies = []`.

Without Nuitka, `anoint` refuses before doing any work, the way
`augur --archetypes` refuses without mypy:

```
++ CANNOT ANOINT: nuitka is not installed ++
   anointing needs it:  pip install 'liturgy[anoint]'
```

Nuitka also needs a C compiler. Finding one, or offering to download one, is
Nuitka's job. `anoint` does not pass `--assume-yes-for-downloads`: Nuitka asks
the user itself, in the terminal, before it downloads anything.

The pinned minimum is whatever Nuitka release supports Python 3.12 to 3.14;
the spike used Nuitka 4.3.4 on Python 3.14.10 (macOS arm64).

## How it works

Four stages. Every one was exercised in the spike (see *Evidence*).

### 1. Gather the litanies

Every `.lit` file under the entry litany's directory, recursively, is
rendered, skipping directories whose names start with `.` and `__pycache__`.
Tracing imports instead was considered and rejected: it duplicates what
Nuitka already does for the `.py` side and needs Liturgy's own import
resolution reimplemented.

Any litany that fails to compile stops the anointing, reported the way
`forge` reports it (`++ CANNOT ANOINT: path line N SyntaxError: ... ++`).
A litany the program never imports still has to compile. That is accepted:
it is the same rule `forge` applies to a directory, and a project that keeps
broken litanies beside its program can move them or anoint from a
subdirectory.

### 2. Render each litany as Python

Constructs (`augur:`, `litany`, `consecrated`) are desugared on the AST, after
parsing, so no Python *text* exists that keeps a litany's line numbers. Nuitka
compiles text. So each litany goes through the compiler's existing
`_artifacts` (the same passes `chant` compiles with, sanction included) and the
resulting tree is written out with `ast.unparse`.

`ast.unparse` renumbers every line. That is why the curse needs a line map
(stage 3). The rule that line N of generated Python is line N of the Liturgy
still holds for everything `chant` runs; this generated text is a build
intermediate that nothing but Nuitka reads, and the line map is what keeps
the user from ever seeing its numbers.

Each rendered file is written into the temporary staging directory at the
same relative path, with a `.py` suffix (`pkg/cog.lit` becomes
`pkg/cog.py`, `pkg/__init__.lit` becomes `pkg/__init__.py`).

*(Correction, post-review: `stage` refuses an entry litany that is not among
the gathered files, with `UnctionFault`, rather than staging a tree whose entry
module does not exist. `anoint` reports it as one `CANNOT ANOINT` line.)*

Every plain `.py` file under the same directory, with the same skip rule, is
copied into the staging directory at its relative path. The staging
directory is then a complete mirror of the project in Python, and the only
project root Nuitka needs. This is required, not tidiness: the README's
*Codices* section documents mixed packages in both directions (a `.lit`
package holding a `.py` module, a `.py` package holding a `.lit` module), and
Python commits to whichever directory holds a package's `__init__`, so a
staged directory searched ahead of the real one would lose half of every
mixed package. *(My call, after the builder check; the first draft did not
copy `.py` files and broke this.)*

Modules outside the entry litany's directory (the standard library,
installed packages) are found by Nuitka the usual way. Litanies outside it,
reached through `PYTHONPATH` or an installed package, are **not** gathered
and so are not in the executable; neither is a litany imported only
dynamically (`importlib.import_module` with a computed name), which Nuitka
cannot follow. Such an executable builds, with Nuitka warning about the
missing module in its streamed output, and fails at run time with
`ForbiddenLore`. That is documented, not prevented: refusing on Nuitka's
missing-module warnings would also refuse every optional import guarded by
`try`/`except ImportError`.

### 3. Build the line map

For each litany, walk the rewritten tree and the tree re-parsed from its
unparsed text side by side, and record, for every statement, its generated
line and the `.lit` line it came from. The two trees are structurally
identical (see *Evidence*), so the walk cannot fall out of step; if it ever
does, `anoint` must refuse loudly rather than bake a wrong map.

The walk uses `ast.iter_fields` recursion, not `ast.walk`: it needs the two
trees in lockstep, which a flattening walk does not guarantee. This is not a
new exception to the CLAUDE.md rule on `ast.walk`.

Statements generated by a construct carry the construct's own line, so a
fault inside `litany`'s retry loop points at the `litany(...)` line, as it
does under `chant`.

### 4. Bake the curse and compile

`anoint` writes one more generated module into the staging directory,
`__liturgy_curse.py`, holding:

- **the tables:** for each rendered module, keyed by its path relative to the
  staging root, the `.lit` path to display, the line map, and the `.lit`
  source lines; and the curse names for the builtin exceptions, taken from
  the lexicon at anoint time;
- **the renderer:** the code that turns an exception into a machine curse
  using only those tables;
- **the installation:** `sys.excepthook` and `threading.excepthook` set to
  that renderer.

The entry litany's rendered module gets `import __liturgy_curse` as its first
statement after any docstring and `from __future__` imports, so the hook is in
place before the litany's first line runs. Nothing else in the program
imports it. The `__liturgy_` prefix is the one the constructs already use for
generated names.

Nuitka is then run in single-file mode on the staged entry module, following
imports, and its executable is moved to the output path.

*(Correction, final review: line maps record every located node, not only
statements, so a fault on a decorator, an `except` clause or a `case` pattern
reports its own line. `stage` skips a `.py` whose same-directory `.lit` twin was
gathered, since `chant`'s loader prefers the `.lit`, and refuses a root file that
would stage as `__liturgy_curse.py`. The `-o` source guard compares with
`os.path.samefile`, not path strings, so case and symlink aliases are caught.
Nuitka runs with the output directory as its cwd, so a project module named
`glob` or `shutil` cannot shadow Nuitka's own imports, and `--follow-imports` is
dropped as onefile's default. An unwritable output directory is refused up
front, and a failed final move is a refusal, not a traceback.)*

## The curse in the executable

### One renderer, not two

`curse.py` is split. The part that walks frames, drops launcher frames,
follows `__cause__`/`__context__` chains and exception groups, names curses
and formats the banner moves into a module that imports nothing from
Liturgy. `curse.py` keeps what needs Liturgy (reading recorded source,
re-running the transform for column maps) and calls into that module, so
`chant` renders exactly what it renders today.

`anoint` copies that module's source text verbatim into `__liturgy_curse.py`
beneath the baked tables. There is exactly one renderer to maintain. A test
holds the copy honest: for the same failing litany, a curse rendered by
`chant` and one rendered by the baked module must agree line for line, once
carets are dropped and paths are made relative. The failing statements in
that test sit on one line each, since multi-line statements legitimately
differ (below).

How the pure module is shaped (callbacks, a small lookup object, plain
dicts) is the builder's call, provided `curse.py`'s existing behaviour and
tests are unchanged.

### What survives and what does not

| In a curse | Under `chant` | In an anointed executable |
|---|---|---|
| ritual curse name | yes | yes |
| `.lit` file | yes, absolute path | yes, relative to the entry litany's directory |
| `.lit` line | yes | yes; for a statement spanning several lines, its first line |
| litany source line | yes | yes, from the baked tables |
| chained and grouped curses | yes | yes |
| curses raised in threads | yes | yes |
| caret under the failing columns | yes | **no** |
| frames from non-litany code | yes | yes, as plain `File "...", line N` |

Carets are lost because Nuitka's frames report line numbers but no column
positions (`colno` is `None`); there is nothing to map. This is a property of
Nuitka, not a choice, and the documentation says so.

The same cause blurs statements that span several lines. `ast.unparse` puts
a whole statement on one generated line, and without columns nothing tells
its parts apart, so a fault on line 3 of a four-line call is reported at the
call's first line, with that line's source. `chant` would name line 3.
Accepted and documented. *(My call, after the builder check.)*

Paths are shown relative to the entry litany's directory (`hymn.lit`,
`pkg/cog.lit`). `chant`'s absolute paths would bake the builder's home
directory and user name into a file meant to be handed to other people, and
would name files that do not exist on their machine. *(My call, after the
builder check.)*

A single-file executable unpacks itself into a temporary directory at
startup, so frame paths point there, not at the build machine. The tables are
therefore keyed by path relative to the directory holding
`__liturgy_curse.py`, never by absolute path.

### `--profane`

The global `--profane` flag and `LITURGY_PROFANE=1` govern the `liturgy`
process, as for every verb. The executable is a separate program: it always
installs its curse renderer. It does not read `LITURGY_PROFANE`, because a
plain traceback from it would point at unparsed generated lines that match
no file the user has. *(Builder: if this turns out wrong in use, it is a
one-line change.)*

### Does this honour "No runtime"?

Yes, by the same reasoning as the constructs. Nothing in the executable
imports Liturgy. `__liturgy_curse.py` is generated Python written into the
program at build time, as a desugared `litany` is. It happens to contain a
copy of Liturgy's own rendering code; the rule is about what is imported at
runtime, and nothing is.

## The verb

- `anoint` leaves `RESERVED_VERBS`. That set is then empty and nothing
  consults it, so the constant and its tests are removed rather than kept
  empty. *(My call; a builder may keep it if removing it disturbs more than
  it should.)*
- It accepts the global `--absolved`/`--profane` flags like every verb.
- It takes exactly one litany. Anointing several entry points at once is not
  supported.
- Exit status: 0 anointed, 1 refused or failed.

## Platforms

`anoint` ships verified on **macOS, Linux and Windows**, each building for
itself (there is no cross-compiling). "Verified" means the end-to-end test
below has passed on each of the three, on Python 3.12 and 3.14, and every
platform-specific claim in the docs was produced on that platform.

Only macOS has been run so far. The other two are verified by **GitHub
Actions**, since the repository has no CI and no Linux or Windows machine is
at hand: a new workflow runs `anoint`'s own tests, the Nuitka end-to-end one
included, on a matrix of `macos-latest`, `ubuntu-latest` and
`windows-latest` by Python 3.12 and 3.14. *(My call: CI is how "verify all
three" gets done without borrowing machines. Pushing to run it is the user's
go-ahead, as any push is.)*

What each platform adds:

- **Windows.** The executable is `hymn.exe`. Table keys are stored with `/`
  and frame paths are normalised (`os.path.relpath`, `os.path.normcase`,
  separators to `/`) before lookup. Nuitka uses MSVC when it finds it and
  otherwise asks to download a MinGW or Zig compiler; with Nuitka's output
  streamed, that question reaches the user. The renderer must not lose a curse
  to the console's encoding: a litany line the console cannot encode is
  printed with replacement characters rather than falling back to a plain
  traceback.
  *(Correction, post-review: on Windows Nuitka is always handed an output name
  ending in `.exe`, whatever `-o` says, and the finished file is then moved to
  the `-o` path exactly as spelled, so `-o hymn` yields a file named `hymn`.
  This was built after the draft above and is unverified until the CI matrix
  runs.)*
  *(Correction, post-CI: the first CI run showed that the download question
  that matters on Windows is not a compiler but Dependency Walker, which
  Nuitka cannot build a single-file executable without. Its prompt defaults
  to no where nothing can answer, so the first Windows jobs failed with
  `FATAL: Nuitka does not work in '--mode=standalone' or '--mode=onefile' on
  Windows without dependency walker.` `anoint` still never pre-consents; the
  workflow warms Nuitka's cache with one `--assume-yes-for-downloads` build of
  a trivial script on Windows runners, and the docs tell users the same.
  On Linux the `patchelf` wheel sufficed on `ubuntu-latest`.)*
- **Linux.** Nuitka's single-file mode needs `patchelf`. The extra installs it
  on Linux where a wheel makes that possible
  (`patchelf; sys_platform == "linux"`); if Nuitka still cannot find it, its
  own message says so, in the streamed output. The builder verifies which of
  these holds on `ubuntu-latest` and documents the result.
- **macOS.** A downloaded executable is quarantined by Gatekeeper; the docs
  give the one command that clears it. Signing and notarization stay out of
  scope.

Making the **whole existing suite** pass on Linux and Windows is not part of
this spec: it has only ever run on macOS, and whatever it finds there is its
own work. The workflow runs `anoint`'s tests, not the full suite.

## Goals

- `liturgy anoint hymn.lit` produces one executable that runs on another
  machine of the same OS and architecture with nothing installed, verified on
  macOS, Linux and Windows.
- That executable renders machine curses with the correct `.lit` file, line,
  source and ritual name, across modules, packages, threads and chains.
- The core install, and the whole existing suite, are untouched by Nuitka's
  absence.

## Non-goals

- **Speed.** Not measured, not claimed.
- **Cross-compiling.** Nuitka builds for the machine it runs on. A macOS
  executable runs on macOS. Said plainly in the docs.
- **Code signing and notarization.** A downloaded macOS executable is
  quarantined by Gatekeeper; the docs say how to clear it, and signing stays
  the user's business.
- **Data files.** Litanies that read files relative to `__file__` will look
  inside the unpacked temporary directory. Bundling data is not offered.
- **Litanies outside the entry directory, and dynamically imported ones.**
  Not gathered; see stage 1 and 2. Documented.
- **Keeping the source private.** The baked tables carry every litany's
  source lines in the executable, in plain text. That is what lets a curse
  quote the line; the docs say so.
- **Carets in the executable.** See above.
- **The audible Binharic Chant.** Step two, its own spec.
- **A standalone-folder mode** or any other Nuitka mode. One file only.

## Anti-goals

These would make the feature a failure even if it technically worked:

- Anything imported from Liturgy when the executable runs.
- A curse from the executable whose line numbers are the generated Python's
  rather than the litany's.
- Nuitka becoming a core dependency, or any existing test needing it.
- Build debris left beside the user's litany.
- A second, hand-maintained copy of the curse renderer.

## Testing

- **Without Nuitka** (always run): gathering, rendering, the line map, the
  hook insertion point (docstring, `from __future__`, neither), and the baked
  module. The baked module is exercised by `exec`ing the staged Python under
  plain CPython with the hook installed and comparing its curse to `chant`'s.
  The refusal message when Nuitka is missing.
- **The corpus backstop:** the stdlib sweep in `tests/test_roundtrip.py` gains
  one assertion per swept file: the rewritten tree unparses and re-parses to
  an identical tree. The sweep's floor is not lowered.
- **With Nuitka** (skipped when it is not installed, marked slow): one end to
  end build of a small multi-module litany (sibling litany, litany package,
  plain `.py`, a thread failure and a chained curse), run from a different
  directory with the sources moved away, and its curse compared with
  `chant`'s.
- Suite green on Python 3.12 and 3.14, as the project requires.
- `anoint`'s tests, end-to-end included, green in the new workflow on all
  three platforms (see *Platforms*). The end-to-end test is the one that must
  not be skipped there: the workflow installs `liturgy[anoint]`.

## Documentation

Five surfaces, as for every behaviour change (`docs/LIBER-LITURGIAE.md`
first, then `docs/liber-liturgiae.html`, `README.md`, `docs/index.html`,
`docs/liturgy-data-slate.html`):

- **Chapter IX:** the section *The one verb still unwritten* goes. Its
  history of how each reserved name was spent stays, with `anoint` added to
  it.
- **Chapter XI:** `anoint` joins the built verbs; the chapter's opening count
  changes. It documents the curse table above, the platform limit and the
  Gatekeeper note.
- **Chapter II** (the paragraph *There is deliberately no verb for anointing
  an environment*): reworded. There is still no verb for anointing an
  environment; `anoint` anoints a litany, and the paragraph says so.
- **README:** the "seven verbs into eight" incompleteness note and the
  reserved-name list are updated; `liturgy[anoint]` joins the extras.
- Every command and output the docs show is run before it ships, per
  CLAUDE.md.

## Evidence

A throwaway spike (2026-11-07, macOS arm64, Python 3.14.10, Nuitka 4.3.4):

- A three-rite litany, rendered with `ast.unparse` and the hook imported as
  its first statement, built in single-file mode in 35 s (7.4 MB). Run from
  another directory with no source present, the hook fired; frames carried
  line numbers and `colno=None`.
- A multi-module project (entry litany, sibling litany, `pkg/__init__.lit`,
  `pkg/cog.lit`, a plain `helper.py`, `threading`) staged as above built in
  13 s. Its curses for a thread failure and a chained
  `proclaim ... within omen` matched `liturgy chant`'s frame for frame,
  carets aside. The only difference: the spike's renderer did not drop the
  two `threading.py` launcher frames that `curse.py` already drops.
- The line map on `examples/constructs.lit` mapped every generated statement,
  including all of `litany`'s and `augur:`'s desugared statements, back to
  the construct's line.
- All 1,754 stdlib files (Python 3.14) that compile as litanies after
  `to_liturgy` unparse and re-parse to an identical tree. 120 others do not
  compile as litanies at all, mostly from Liturgy words used as identifiers,
  the caveat the round-trip sweep already skips.

Not exercised: Linux and Windows builds (the workflow covers them); Python
3.12; litanies reading files via `__file__`.

## Left to the builder

- The shape of the pure renderer module and how `curse.py` calls it.
- The workflow's details (caching, timeouts, how the slow test is selected).
- Status-line wording.
- Where the gather, render, map and bake code lives (`tooling.py` or a new
  module placed correctly in the dependency order in CLAUDE.md).
- The Nuitka version floor in `pyproject.toml`.
