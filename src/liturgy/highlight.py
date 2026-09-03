"""A Pygments lexer for Liturgy, driven by the real transform.

A hand-written keyword regex would repeat Spec I's original sin: firing on a
word without checking its position. This lexer instead asks the same token
passes the compiler runs -- `alias_pass` for the sixty words, `carrier_pass`
for construct headers -- exactly which occurrences *are* Liturgy, so the
three prohibitions hold in the highlighting too: `template.render()` paints
`render` as a plain attribute, `func(intone=True)` paints a plain keyword
argument, and an invocation's targets stay the module's own.

Highlighting is not a linter. `span = 1` paints `span` as the builtin it
becomes -- `augur` is the verb that judges bindings. The one exception is
the machine's own names, painted as errors, because no litany may speak
them at all.

This module is the one place the package touches Pygments, and Pygments is
an optional extra (`pip install liturgy[highlight]`): nothing in the core
imports this, and Pygments discovers the class through the
`pygments.lexers` entry point.
"""

from __future__ import annotations

import io
import token as tokmod
import tokenize

from pygments.lexers.python import PythonLexer
from pygments.token import Error, Keyword, Name, Number, Operator, _TokenType

from .constructs import _INSIGNIFICANT, carrier_pass, is_machine_name
from .lexicon import CURSES, KEYWORDS, NUMERALS, SOFTWORDS
from .transform import Substitution, alias_pass, split_lines

# How each table paints. `Operator.Word` and `Keyword.Constant` mirror what
# the Python lexer gives `and`/`or`/`not`/`is`/`in` and `True`/`False`/`None`,
# so a litany and its generated Python read in the same palette.
_CONSTANTS = frozenset({"Sanctioned", "Heretical", "Void"})
_WORD_OPERATORS = frozenset({"likewise", "elsewise", "nay", "be", "among"})


def _paint(word: str) -> _TokenType:
    if word in _CONSTANTS:
        return Keyword.Constant
    if word in _WORD_OPERATORS:
        return Operator.Word
    if word in SOFTWORDS:
        return Name.Builtin
    if word in CURSES:
        return Name.Exception
    if word in NUMERALS:
        return Number.Integer
    return Keyword  # the remaining KEYWORDS, and the construct headers


def _word_table() -> dict[str, _TokenType]:
    """The context-free fallback: word -> token, position-blind."""
    table = {word: _paint(word) for word in (*KEYWORDS, *SOFTWORDS, *CURSES, *NUMERALS)}
    table.update({word: Keyword for word in ("consecrated", "litany", "augur")})
    return table


_FALLBACK = _word_table()


def _remap(text: str) -> dict[int, _TokenType] | None:
    """Character index -> token type, for every occurrence that is Liturgy.

    Uses the compiler's own passes, so context is exact. Returns None when
    the source will not tokenize -- mid-edit text, usually -- and the caller
    falls back to painting by word alone.
    """
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError, ValueError):
        return None

    lines = split_lines(text)
    line_start = [0]
    for line in lines:
        line_start.append(line_start[-1] + len(line))

    def at(row: int, col: int) -> int:
        return line_start[row - 1] + col

    table: dict[int, _TokenType] = {}

    subs: list[Substitution] = alias_pass(toks)
    for s in subs:
        word = lines[s.row - 1][s.col_start : s.col_end]
        table[at(s.row, s.col_start)] = _paint(word)

    # Construct headers. `carrier_pass` raises the machine-name heresy and
    # the malformed-header heresies; a highlighter reports nothing, so on
    # any heresy the headers simply go unpainted and the machine-name scan
    # below still runs. Only the substitution sitting on the construct word
    # itself is painted; anything else on the header is the author's own.
    try:
        for s in carrier_pass(toks).subs:
            word = lines[s.row - 1][s.col_start : s.col_end]
            if word.split(None, 1)[:1] and word.split(None, 1)[0] in (
                "consecrated", "litany", "augur", "unsanctioned"
            ):
                table.setdefault(at(s.row, s.col_start), Keyword)
    except SyntaxError:
        pass

    # The machine's own names, wherever an author spelled them -- except
    # after a dot, where they are legal (Rule 1's reasoning).
    significant = [t for t in toks if t.type not in _INSIGNIFICANT]
    for i, tok in enumerate(significant):
        if tok.type != tokmod.NAME or not is_machine_name(tok.string):
            continue
        prev = significant[i - 1] if i else None
        if prev is not None and prev.type == tokmod.OP and prev.string == ".":
            continue
        table[at(tok.start[0], tok.start[1])] = Error

    return table


class LiturgyLexer(PythonLexer):
    """Python's lexer underneath, with the ritual words repainted on top."""

    name = "Liturgy"
    aliases = ["liturgy", "lit"]
    filenames = ["*.lit"]
    mimetypes = ["text/x-liturgy"]
    url = "https://github.com/Another-workation-farang/tech-priest-liturgy"

    def get_tokens_unprocessed(self, text):
        table = _remap(text)
        for index, token, value in super().get_tokens_unprocessed(text):
            # Only identifier-ish tokens are repainted: the Python lexer
            # has already settled strings, comments and numbers, and a
            # ritual word inside a string is prose, not Liturgy.
            if token in Name or token in Keyword:
                if table is not None:
                    override = table.get(index)
                else:
                    override = _FALLBACK.get(value)
                    if override is None and is_machine_name(value):
                        override = Error
                if override is not None:
                    token = override
            yield index, token, value
