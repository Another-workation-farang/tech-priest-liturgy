"""Setting a litany's form in order, without changing what it says.

Chapter IX declined a formatter twice over, and the second reason was the
real one: doing it improperly means a tool that eats your source. So this one
is deliberately small, and everything it does is checked before it is
returned.

What it will not do is as important as what it will. `ast.unparse` would
give a full reformatting in three lines and drop every comment and blank
line on the way -- so it is not used. Nothing here re-flows an expression,
re-quotes a string, or moves a token. Only whitespace between tokens
changes, and only where the whitespace is not itself somebody's data.

Three shapes are left alone on purpose, each of which a naive formatter
gets wrong:

- The interior of a multi-line string. Its trailing spaces and its
  indentation are its value.
- A bracket continuation. `tokenize` emits no INDENT for one, and the
  author's alignment is a choice.
- A standalone comment before a block's first statement. `tokenize` reports
  it *before* the INDENT token, so a running depth counter indents it to
  the enclosing level and silently walks it out of the block it belongs to.
  Such a comment takes the depth of the statement it introduces.
"""

from __future__ import annotations

import ast
import io
import tokenize

from .compiler import _PASSES
from .transform import UnfinishedLitany, split_lines, transform

INDENT_WIDTH = 4
MAX_BLANK_RUN = 2

_LAYOUT = frozenset({tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE, tokenize.NL})


class UnsanctifiableLitany(Exception):
    """The litany could not be set in order, and was left exactly as it was."""


def _shape(src: str) -> tuple[dict[int, int], set[int]]:
    """`(depth_of_row, protected_rows)` for the rows this may re-indent.

    `depth_of_row` holds only rows that begin a logical statement, plus the
    standalone comments attached to one. Every other row -- continuations
    especially -- is absent, and absent means untouched.
    """
    depth = 0
    brackets = 0
    depth_of: dict[int, int] = {}
    protected: set[int] = set()
    pending_comments: list[int] = []

    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.INDENT:
            depth += 1
            continue
        if tok.type == tokenize.DEDENT:
            depth = max(0, depth - 1)
            continue

        if tok.type == tokenize.COMMENT and tok.start[1] == _first_col(src, tok):
            # Standalone: decide its depth once the next statement names one.
            pending_comments.append(tok.start[0])
            continue

        if tok.type in _LAYOUT or tok.type == tokenize.ENDMARKER:
            continue

        if tok.end[0] > tok.start[0]:
            # A multi-line token: everything after its opening row is data.
            protected.update(range(tok.start[0] + 1, tok.end[0] + 1))

        if brackets == 0 and tok.start[0] not in depth_of:
            row = tok.start[0]
            if row not in protected:
                depth_of[row] = depth
                for c in pending_comments:
                    depth_of.setdefault(c, depth)
            pending_comments.clear()

        if tok.type == tokenize.OP:
            if tok.string in "([{":
                brackets += 1
            elif tok.string in ")]}":
                brackets = max(0, brackets - 1)

    # Comments with no statement after them keep the last depth seen.
    for c in pending_comments:
        depth_of.setdefault(c, depth)
    return depth_of, protected


def _first_col(src: str, tok) -> int:
    """The column of the first non-space character on the token's row."""
    line = tok.line
    return len(line) - len(line.lstrip())


def _significant(src: str) -> list[tuple[int, str]]:
    """Every token that carries meaning, for the before/after comparison.

    Layout tokens are excluded because reshaping them is the whole job.
    Comments are emphatically included: losing one is the failure this
    check exists to catch.
    """
    out = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type in _LAYOUT or tok.type == tokenize.ENDMARKER:
            continue
        out.append((tok.type, tok.string))
    return out


def _tree(src: str) -> str:
    """A dump of what the litany compiles to, for the before/after check."""
    py, _ = transform(src, _PASSES, filename="<sanctify>")
    return ast.dump(ast.parse(py))


def sanctify_text(src: str) -> str:
    """Return `src` with its form set in order.

    Raises:
        UnsanctifiableLitany: the litany does not tokenise or does not
            parse, or the result would not have said the same thing. In
            every case the caller has the original, unharmed.
    """
    try:
        before_tokens = _significant(src)
        before_tree = _tree(src)
        depth_of, protected = _shape(src)
    except (tokenize.TokenError, UnfinishedLitany, IndentationError) as err:
        raise UnsanctifiableLitany(f"the litany does not tokenise: {err}") from err
    except SyntaxError as err:
        raise UnsanctifiableLitany(f"the litany does not parse: {err.msg}") from err

    lines = split_lines(src)
    out: list[str] = []
    kept_verbatim: list[bool] = []
    blank_run = 0

    for n, raw in enumerate(lines, start=1):
        # `split_lines` keeps the line terminator; the join below puts one
        # back, so it comes off here -- for protected rows too, or every
        # string interior gains a blank line.
        stripped_eol = raw.rstrip("\r\n")

        if n in protected:
            out.append(stripped_eol)
            kept_verbatim.append(True)
            blank_run = 0
            continue

        body = stripped_eol.rstrip()
        if not body:
            blank_run += 1
            if blank_run > MAX_BLANK_RUN:
                continue
            out.append("")
            kept_verbatim.append(False)
            continue

        blank_run = 0
        if n in depth_of:
            body = " " * (INDENT_WIDTH * depth_of[n]) + body.lstrip()
        out.append(body)
        kept_verbatim.append(False)

    # Trailing blank lines go -- but a blank line inside a string is data,
    # not trailing whitespace, and stays.
    while out and not out[-1] and not kept_verbatim[-1]:
        out.pop()
        kept_verbatim.pop()
    result = "\n".join(out) + "\n" if out else ""

    # The guarantee, checked rather than asserted. A formatter that cannot
    # prove it kept every token and the same tree is the tool Chapter IX
    # refused to ship.
    try:
        if _significant(result) != before_tokens:
            raise UnsanctifiableLitany("the tokens would have changed")
        if _tree(result) != before_tree:
            raise UnsanctifiableLitany("the meaning would have changed")
    except (tokenize.TokenError, UnfinishedLitany, SyntaxError) as err:
        raise UnsanctifiableLitany(f"the result would not read back: {err}") from err

    return result
