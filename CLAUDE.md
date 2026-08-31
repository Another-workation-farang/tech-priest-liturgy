# Liturgy

A superset of Python whose surface syntax is Warhammer 40,000 tech-priest
ritual language. `.lit` files tokenize, have their ritual words substituted
back to Python spellings, and compile as ordinary Python.

## Where things go

- **`design/specs/`** and **`design/plans/`** — design documents and
  implementation plans. **Not** `docs/superpowers/`, which is where the
  superpowers skills write by default: `docs/` is published as a GitHub Pages
  site, and internal design notes do not belong in it. Move anything that
  lands there.
- **`docs/`** — the published site, and nothing else. `LIBER-LITURGIAE.md` is
  the canonical language reference; the HTML pages render the same text and
  follow `docs/STYLE-COGITATOR.md`.
- **`src/liturgy/`** — the implementation. Module dependency order is
  `lexicon` -> `sourcemap` -> `transform` -> `constructs` -> `rewrite` ->
  `compiler` -> `loader`/`curse` -> `cli`. Nothing imports later than itself.

## Rules this project has learned the hard way

- **The transform never adds or removes a line.** Line N of the generated
  Python is line N of the Liturgy. Traceback line numbers depend on it, and a
  `Substitution` spanning two rows breaks it.
- **`ast.walk` flattens the tree and destroys scope distinctions.** It has
  caused six separate defects here. `rewrite.py` has one traversal,
  `_in_scope`, and no `ast.walk` anywhere in `src/` -- except
  `collisions.py`, which is a deliberate exception, not an oversight: the
  substitution it mirrors is itself scope-blind (Rule 1/2 rewrite a
  reserved word's every occurrence in the file, textually, regardless of
  which scope it is bound in), so "is this name bound anywhere as a
  reserved word" is genuinely a whole-file question with no scope
  boundary to respect. Flattening is correct there for the same reason it
  is wrong everywhere else in `src/`: it matches what the code it mirrors
  actually does. A new scope-blind question may reuse `ast.walk` on that
  same reasoning; anything that must distinguish one scope from another
  belongs on `_in_scope` instead.
- **`ast` and `traceback` count UTF-8 bytes; everything else counts
  characters.** Any offset from either must go through
  `sourcemap.char_offset` before a `SourceMap` sees it.
- **No runtime.** Constructs desugar into self-contained generated Python.
  Nothing is imported from Liturgy at runtime. A feature that cannot be built
  within that gets cut, not accommodated — `noospheric` was.
- **Every documented command and output is run before it ships.** That check
  has caught a real error every time it has been applied.

## Testing

`.venv/bin/pytest`. The suite is expected green on Python 3.12 and later.
The stdlib corpus sweep in `tests/test_roundtrip.py` is the backstop that has
caught what hand-written tests missed; do not weaken its floor.
