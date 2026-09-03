# Liturgy for VS Code

Syntax highlighting for `.lit` files from [Liturgy](https://github.com/Another-workation-farang/tech-priest-liturgy),
the superset of Python spoken in the ritual tongue of the Adeptus Mechanicus.

## Installing

The extension is not on the marketplace (Liturgy is a toy; the marketplace is
not). Install it from this directory:

```
$ cd editors/vscode-liturgy
$ npx @vscode/vsce package
$ code --install-extension liturgy-syntax-0.1.0.vsix
```

or, without packaging, symlink it into your extensions directory and reload:

```
$ ln -s "$(pwd)" ~/.vscode/extensions/tech-priest-liturgy.liturgy-syntax-0.1.0
```

## What it knows

All sixty-three reserved words, painted to match their Python kin: ritual
keywords as keywords, `Sanctioned`/`Heretical`/`Void` as constants,
`likewise`/`elsewise`/`nay`/`be`/`among` as word operators, the five builtin
aliases as builtins, the fifteen curse names as exceptions, `twice`/`thrice`
as numbers. Plain Python spellings highlight too, because a `.lit` file is still
Python underneath. The machine's own names (`__litany__` and kin) paint as
illegal, because speaking one is a loud heresy.

It also approximates the transform's context rules:

- **Attribute position** (Rule 1): `template.render()` leaves `render` plain.
- **Keyword-argument position** (Rule 2): `func(intone=True)` leaves `intone`
  plain. The approximation is broader than the real rule: any ritual word
  directly before a single `=` goes unpainted, so `span = 1` renders as a
  plain name. That happens to read as a warning: a binding of `span` is the
  quiet collision `liturgy augur` exists to catch.
- **Invocations** (Rule 3): on a `within`/`invoke` line only the statement's
  own keywords paint; the targets stay the module's own.
- **Construct headers**: `consecrated`, `litany(...)`: and a lone `augur:`
  paint as keywords only in header position; `litany = 5` is your own name
  and stays plain.
- **`unsanctioned`**: paints in front of a `rite` (or a `remote rite`) or a
  `consecrated` name, and alone on a line at the margin, where it exempts
  the whole litany. An `unsanctioned` in front of either header does not
  stop the header itself painting. Anywhere else the compiler rejects the
  word outright, and the grammar simply leaves it plain rather than
  guessing at `invalid.illegal`.

A TextMate grammar cannot be exact about any of this. For compiler-exact
highlighting (docs, pipelines), use the Pygments lexer that ships with the
package itself: `pip install "liturgy[highlight]"`, then `pygmentize
prayer.lit`. Known approximations here: a one-line compound statement
(`should x: invoke json`) does not get import-context treatment, and a
backslash-continued invocation loses Rule 3 on its continuation lines.

`tests/test_grammar.py` in the repository holds this grammar's word lists to
the language's lexicon, so a word added there without joining this file fails
the suite.
