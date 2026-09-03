"""Archetypes that are *false*, read by delegating to mypy.

Liturgy does not need a type checker; it needs a translator. The transform
never adds or removes a line, so line N of the generated Python is line N of
the litany and a checker's diagnostics already land on the right row with no
arithmetic at all. Only columns move, and `SourceMap.to_lit` already carries
those -- it is what maps traceback carets today.

mypy is an **optional extra**. Nothing outside this module may reach for it,
and this module does not import it either: it is run in a subprocess, so a
crash or a hang in the checker is something we survive and can report rather
than something that takes the interpreter with it.

**The silent-success mode is the worst outcome available here.** A caller
that reports a clean bill of health having checked nothing is worse than one
that crashes, so every way the oracle can fail to reach a verdict raises
`ArchetypesUnread` and none of them returns an empty list. `check` returning
`[]` means mypy ran, was understood, and found nothing.

mypy also speaks Python, and a litany's author has never written `def` or
`return`. `translate` renders the diagnostics this module recognises into the
language the author actually writes, and **passes every other one through
verbatim, marked `Finding.translated = False`**. A half-translated diagnostic
-- Liturgy words in a Python sentence, or a type name mangled by an
over-eager substitution -- is worse than an honest untranslated one, which is
the same discipline `sanctify` keeps when it refuses rather than guesses.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Callable

from .compiler import _PASSES, parse_named
from .constructs import is_machine_name
from .lexicon import INVERSE
from .sourcemap import char_offset
from .transform import split_lines, transform

__all__ = [
    "ArchetypesUnread",
    "Finding",
    "MypyFailed",
    "MypyNotInstalled",
    "MypyUnintelligible",
    "OracleRun",
    "check",
    "mypy_available",
    "mypy_oracle",
    "parse_diagnostics",
    "translate",
]

# What mypy is told, every run. `--follow-imports=skip` with
# `--ignore-missing-imports` is what makes single-file checking quiet: an
# import mypy cannot resolve would otherwise bury the file's own errors. It
# is also the reason this version checks one litany at a time, which the
# documentation says plainly rather than implying whole-project coverage.
_MYPY_FLAGS = (
    "--show-column-numbers",
    "--show-error-codes",
    "--no-error-summary",
    "--no-pretty",
    "--no-color-output",
    "--follow-imports=skip",
    "--ignore-missing-imports",
    # A user's mypy.ini must not change what a litany is told about itself,
    # and the temp directory this runs in must not accidentally inherit one
    # from /tmp's ancestors either.
    "--config-file=",
)

_DEFAULT_TIMEOUT = 120.0

# `path:line[:col]: severity: message  [code]`. The column is optional
# because mypy omits it for a handful of file-level diagnostics, and the code
# is optional because `note` lines never carry one.
_DIAGNOSTIC = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+)(?::(?P<col>\d+))?: "
    r"(?P<severity>[a-z]+): "
    r"(?P<message>.*?)"
    r"(?:  \[(?P<code>[A-Za-z0-9_-]+)\])?$"
)

_QUOTED = re.compile(r'"([^"]+)"')


class ArchetypesUnread(Exception):
    """The checker reached no verdict.

    Every subclass means "nothing was read", never "nothing was found". A
    caller must not render this as a clean bill of health.
    """


class MypyNotInstalled(ArchetypesUnread):
    """The `archetypes` extra is not installed in the interpreter asked."""


class MypyFailed(ArchetypesUnread):
    """mypy ran but did not finish -- it crashed, timed out, or refused."""


class MypyUnintelligible(ArchetypesUnread):
    """mypy finished and said something this module cannot read.

    Raised rather than skipped: a line we do not understand may be the only
    finding there was, and dropping it silently is the failure this module
    exists to prevent.
    """


@dataclass(frozen=True, slots=True)
class Finding:
    """One archetype diagnostic, in **Liturgy** coordinates.

    `line` is 1-based and needs no mapping: the transform never adds or
    removes a line, so the generated Python's row *is* the litany's row.

    `col` is 0-based -- the convention `Collision`, `Seal` and `Breach` all
    keep -- and has already been through `char_offset` and `to_lit`, because
    mypy counts UTF-8 bytes in generated-Python columns and everything else
    here counts characters in the litany. It is None when mypy gave no
    column; a column is never invented, since a caret under column 0 is a
    claim about where the fault is and a missing one is not.

    `message` is the diagnostic in the language the litany is written in
    where `translate` recognised its shape, and mypy's own untouched text
    where it did not.

    `translated` says which of those two it is, and exists so that a renderer
    can attribute an untranslated message to the checker rather than pass
    Python prose off as Liturgy. It defaults to False because that is the
    honest default: a `Finding` built by hand, or by a caller that predates
    this field, is claiming nothing about whose words it carries. `code` is
    mypy's error code, or None for a `note`. `severity` is mypy's word for it
    -- `error` or `note`.
    """

    line: int
    col: int | None
    message: str
    code: str | None
    severity: str
    translated: bool = False


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One parsed mypy line, still in **generated-Python** coordinates.

    `col` is 1-based here, exactly as mypy printed it, and is a UTF-8 byte
    offset. Kept separate from `Finding` so that "what mypy said" and "where
    that is in the litany" are two steps and the first can be tested without
    mypy installed at all.
    """

    path: str
    line: int
    col: int | None
    severity: str
    message: str
    code: str | None


@dataclass(frozen=True, slots=True)
class OracleRun:
    """What an oracle brought back: mypy's two streams and its exit status."""

    stdout: str
    stderr: str
    status: int


# (generated .py to check, cache directory to use) -> what mypy said.
Oracle = Callable[[pathlib.Path, pathlib.Path], OracleRun]


def mypy_available(python: str | os.PathLike[str] | None = None) -> bool:
    """Whether `python` can run mypy. Never imports it.

    The interpreter defaults to this one, where `importlib.util.find_spec`
    answers without loading the package. A different interpreter is asked
    the same question in a subprocess, which is what lets the trials run a
    real mypy from an environment the core does not have.
    """
    exe = sys.executable if python is None else os.fspath(python)
    if exe == sys.executable:
        try:
            return importlib.util.find_spec("mypy") is not None
        except (ImportError, ValueError):
            return False
    probe = "import importlib.util as u, sys; sys.exit(0 if u.find_spec('mypy') else 1)"
    try:
        done = subprocess.run(
            [exe, "-c", probe], capture_output=True, timeout=_DEFAULT_TIMEOUT
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def mypy_oracle(
    python: str | os.PathLike[str] | None = None,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
) -> Oracle:
    """The real oracle: mypy, in a subprocess, with an isolated cache.

    The cache directory is the one `check` made under its temp directory, so
    mypy never writes into the litany's project and two runs cannot collide
    over the same cache. The subprocess runs *in* that directory and is
    handed a bare filename, so the path mypy prints back carries no temp
    directory to strip.

    Raises:
        MypyNotInstalled: `python` has no mypy.
        MypyFailed: mypy could not be started, or did not finish in time.
    """
    exe = sys.executable if python is None else os.fspath(python)

    def run(path: pathlib.Path, cache_dir: pathlib.Path) -> OracleRun:
        if not mypy_available(exe):
            raise MypyNotInstalled(
                f"{exe} cannot run mypy; install the archetypes extra"
            )
        argv = [exe, "-m", "mypy", *_MYPY_FLAGS, f"--cache-dir={cache_dir}", path.name]
        try:
            done = subprocess.run(
                argv,
                cwd=path.parent,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise MypyFailed(
                f"mypy did not finish within {timeout:g}s"
            ) from None
        except OSError as err:
            raise MypyFailed(f"mypy could not be run: {err}") from None
        return OracleRun(done.stdout, done.stderr, done.returncode)

    return run


def parse_diagnostics(stdout: str) -> list[Diagnostic]:
    """Every diagnostic in mypy's output, in generated-Python coordinates.

    Raises:
        MypyUnintelligible: a non-blank line that is not a diagnostic.
    """
    found: list[Diagnostic] = []
    for raw in stdout.splitlines():
        if not raw.strip():
            continue
        m = _DIAGNOSTIC.match(raw)
        if m is None:
            raise MypyUnintelligible(f"cannot read mypy's output: {raw!r}")
        col = m["col"]
        found.append(
            Diagnostic(
                path=m["path"],
                line=int(m["line"]),
                col=int(col) if col is not None else None,
                severity=m["severity"],
                message=m["message"],
                code=m["code"],
            )
        )
    return found


def _is_carrier_noise(diag: Diagnostic) -> bool:
    """Is this mypy complaining about a construct carrier?

    `litany(...)` and `augur:` desugar through `__litany__` and `__augur__`,
    which exist only to be restructured by a later AST pass -- mypy sees the
    intermediate source and reports them undefined. The names are read from
    `constructs.is_machine_name`, never written down here: a carrier added
    later must not leak because nobody remembered to type its name into this
    module.
    """
    if diag.code != "name-defined":
        return False
    return any(is_machine_name(name) for name in _QUOTED.findall(diag.message))


def _drop_carrier_noise(diags: list[Diagnostic]) -> list[Diagnostic]:
    """`diags` without the carrier errors, and without their notes.

    mypy attaches explanatory `note` lines to the error above them at the
    same position. Dropping an error and keeping its notes would leave the
    explanation of a fault the reader is never shown.
    """
    kept: list[Diagnostic] = []
    dropped_at: tuple[int, int | None] | None = None
    for diag in diags:
        if diag.severity == "note" and dropped_at == (diag.line, diag.col):
            continue
        if _is_carrier_noise(diag):
            dropped_at = (diag.line, diag.col)
            continue
        dropped_at = None
        kept.append(diag)
    return kept


# --- translation -----------------------------------------------------------
#
# The Liturgy words below are read out of `lexicon.INVERSE`, never written
# down here, for the same reason `_is_carrier_noise` asks
# `constructs.is_machine_name` rather than a list of strings: renaming a word
# in the lexicon must rename it in these messages too.


def _word(python: str) -> str:
    """The Liturgy spelling of a Python word.

    Looked up as the message is built, not as this module is imported, so
    that the lexicon is demonstrably the only place these words live: change
    `render` there and these diagnostics change with it.
    """
    return INVERSE[python]


# Operators mypy spells with symbols. It also spells one with a word --
# `Unsupported operand types for in ("str" and "Generator[int, None, None]")`
# -- and `in` is `among` in Liturgy, but a Liturgy operator inside a Python
# sentence is the half-translation this module refuses, and translating the
# sentence would then need every word operator's Liturgy spelling to be
# certain. Those messages pass through whole instead.
_SYMBOLIC_OPERATOR = re.compile(r"^[^\w\s]{1,3}$")


def _a(archetype: str) -> str:
    """`a` or `an`, for a type name that is printed verbatim after it.

    Crude on purpose: it looks at the letter, not the sound, because the
    alternative is a pronunciation table for every type name a user can
    write. It is only ever an article.
    """
    return "an" if archetype[:1].lower() in "aeiou" else "a"


def _incompatible_return(m: re.Match[str]) -> str:
    return (
        f"this {_word('def')} {_word('return')}s {_a(m['got'])} {m['got']} "
        f"where it declared {_a(m['want'])} {m['want']}"
    )


def _no_return_expected(m: re.Match[str]) -> str:
    del m
    return (
        f"this {_word('def')} {_word('return')}s a value "
        f"where it declared {_word('None')}"
    )


def _missing_return(m: re.Match[str]) -> str:
    del m
    return (
        f"this {_word('def')} declares an {_word('type')} "
        f"it never {_word('return')}s"
    )


def _bad_argument(m: re.Match[str]) -> str:
    which = m["which"].strip('"')
    owner = f" of {m['owner']}" if m["owner"] else ""
    return (
        f"argument {which} to {m['callee']}{owner} is {_a(m['got'])} {m['got']} "
        f"where {m['callee']} declares {_a(m['want'])} {m['want']}"
    )


def _bad_assignment(m: re.Match[str]) -> str:
    return (
        f"this binds {_a(m['got'])} {m['got']} to a name "
        f"declared {_a(m['want'])} {m['want']}"
    )


def _bad_inherited_assignment(m: re.Match[str]) -> str:
    return (
        f"this binds {_a(m['got'])} {m['got']} where the {_word('class')} "
        f"{m['base']} declared {_a(m['want'])} {m['want']}"
    )


def _bad_operands(m: re.Match[str]) -> str | None:
    if not _SYMBOLIC_OPERATOR.match(m["op"]):
        return None
    return (
        f"{_a(m['left'])} {m['left']} and {_a(m['right'])} {m['right']} "
        f"cannot be joined by {m['op']}"
    )


def _undefined_name(m: re.Match[str]) -> str:
    return f"nothing named {m['name']} is known here"


def _missing_attribute(m: re.Match[str]) -> str:
    return f"{_a(m['owner'])} {m['owner']} bears no attribute {m['attr']}"


def _too_many_arguments(m: re.Match[str]) -> str:
    return f"{m['callee']} is given more arguments than it declares"


def _missing_arguments(m: re.Match[str]) -> str:
    names = _QUOTED.findall(m["names"])
    noun = "argument" if len(names) == 1 else "arguments"
    return f"{m['callee']} is called without its {noun} {', '.join(names)}"


def _unexpected_keyword(m: re.Match[str]) -> str:
    return f"{m['callee']} declares no parameter {m['name']}"


# code -> the message shapes translated under it, in order. A shape that
# does not match, or a builder that returns None, means this module does not
# recognise the diagnostic and it passes through as mypy wrote it. The
# patterns are anchored end to end deliberately: mypy appends hints to some
# of these ("; maybe \"__int__\"? (not iterable)"), and a suffix nobody
# accounted for must fail to match rather than be silently dropped.
_Shape = tuple[re.Pattern[str], Callable[[re.Match[str]], str | None]]

_TRANSLATORS: dict[str, tuple[_Shape, ...]] = {
    "return-value": (
        (
            re.compile(
                r'^Incompatible return value type '
                r'\(got "(?P<got>.+)", expected "(?P<want>.+)"\)$'
            ),
            _incompatible_return,
        ),
        (re.compile(r"^No return value expected$"), _no_return_expected),
    ),
    "return": ((re.compile(r"^Missing return statement$"), _missing_return),),
    "arg-type": (
        (
            re.compile(
                r'^Argument (?P<which>\d+|"[^"]+") to "(?P<callee>[^"]+)"'
                r'(?: of "(?P<owner>[^"]+)")? has incompatible type '
                r'"(?P<got>.+)"; expected "(?P<want>.+)"$'
            ),
            _bad_argument,
        ),
    ),
    "assignment": (
        (
            re.compile(
                r'^Incompatible types in assignment \(expression has type '
                r'"(?P<got>.+)", variable has type "(?P<want>.+)"\)$'
            ),
            _bad_assignment,
        ),
        (
            re.compile(
                r'^Incompatible types in assignment \(expression has type '
                r'"(?P<got>.+)", base class "(?P<base>[^"]+)" defined the '
                r'type as "(?P<want>.+)"\)$'
            ),
            _bad_inherited_assignment,
        ),
    ),
    "operator": (
        (
            re.compile(
                r'^Unsupported operand types for (?P<op>\S+) '
                r'\("(?P<left>.+)" and "(?P<right>.+)"\)$'
            ),
            _bad_operands,
        ),
    ),
    "name-defined": (
        (re.compile(r'^Name "(?P<name>[^"]+)" is not defined$'), _undefined_name),
    ),
    "attr-defined": (
        (
            re.compile(r'^"(?P<owner>.+)" has no attribute "(?P<attr>[^"]+)"$'),
            _missing_attribute,
        ),
    ),
    "call-arg": (
        (
            re.compile(r'^Too many arguments for "(?P<callee>[^"]+)"$'),
            _too_many_arguments,
        ),
        (
            re.compile(
                r'^Missing positional arguments? (?P<names>"[^"]+"(?:, "[^"]+")*) '
                r'in call to "(?P<callee>[^"]+)"$'
            ),
            _missing_arguments,
        ),
        (
            re.compile(
                r'^Unexpected keyword argument "(?P<name>[^"]+)" '
                r'for "(?P<callee>[^"]+)"$'
            ),
            _unexpected_keyword,
        ),
    ),
}


def translate(
    message: str, code: str | None, severity: str = "error"
) -> tuple[str, bool]:
    """`message` in Liturgy, and whether it could be said in Liturgy at all.

    Returns `(text, translated)`. When `translated` is False the text is
    mypy's own, character for character, and a renderer must attribute it to
    the checker: a half-translated diagnostic is worse than an honest
    untranslated one, and that judgement is what this return value carries.

    Translated: `return-value`, `return`, `arg-type`, `assignment`,
    `operator`, `name-defined`, `attr-defined` and `call-arg` -- and only the
    message shapes recorded in `_TRANSLATORS`, since mypy's prose moves
    between versions and a shape that has shifted must miss rather than half
    match. **Every other code passes through**, as does every `note`: a note
    continues the error above it, reads as a fragment on its own, and is the
    checker's commentary on its own reasoning rather than a statement about
    the litany.

    Names and type names are copied out of the match and printed verbatim,
    never substituted. `archetype` is Liturgy's word for `type`, but `int` is
    still `int`, and a type name is arbitrary Python type syntax rather than
    a word: rewriting `ValueError` inside `dict[str, ValueError]` needs a
    parser for that syntax, and `ImpureOffering` is not certainly what the
    author wrote there in any case, since a litany may spell either. The
    keyword positions -- what a `rite` does, what a `pattern` declares -- are
    this module's to translate; the names in them are the author's, and mypy
    quoted them for the same reason.
    """
    if severity != "error" or code is None:
        return message, False
    for pattern, build in _TRANSLATORS.get(code, ()):
        m = pattern.match(message)
        if m is None:
            continue
        text = build(m)
        if text is not None:
            return text, True
    return message, False


def to_finding(diag: Diagnostic, py_lines: list[str], smap) -> Finding:
    """`diag` in Liturgy coordinates.

    The message goes through `translate` on the way, so a `Finding` carries
    Liturgy where Liturgy could be spoken confidently and mypy's own words,
    marked as such, where it could not.

    The line passes through untouched -- that is the whole feasibility
    argument. The column takes the two steps every offset in this project
    takes: mypy's 1-based UTF-8 *byte* offset into the generated Python line
    becomes a 0-based character offset via `char_offset`, and `to_lit` then
    carries it back across the substitutions to the litany.
    """
    message, translated = translate(diag.message, diag.code, diag.severity)
    if diag.col is None:
        return Finding(
            diag.line, None, message, diag.code, diag.severity, translated
        )
    py_line = py_lines[diag.line - 1] if 0 <= diag.line - 1 < len(py_lines) else ""
    col = smap.to_lit(diag.line, char_offset(py_line, diag.col - 1))
    return Finding(diag.line, col, message, diag.code, diag.severity, translated)


def interpret(
    run: OracleRun,
    py_lines: list[str],
    smap,
) -> list[Finding]:
    """What the oracle's answer means, or why it means nothing.

    Split out from `check` so that every way of misreading mypy is testable
    without mypy installed. The three guards below are the whole defence
    against reporting "no type errors" having read nothing:

    * an exit status that is neither 0 (clean) nor 1 (errors found) means
      mypy refused or crashed;
    * status 1 with nothing parsed means mypy found errors this module did
      not see, which is the silent-success hole exactly;
    * an error at status 0 means our understanding of mypy's contract is
      wrong, and a wrong understanding is not a clean bill of health.

    Carrier noise is filtered *after* those guards, so a run whose every
    diagnostic is noise still returns an honest empty list.

    Raises:
        MypyFailed: mypy did not reach a verdict.
        MypyUnintelligible: mypy's output could not be read.
    """
    if run.status not in (0, 1):
        detail = (run.stderr.strip() or run.stdout.strip() or "no output")
        raise MypyFailed(f"mypy exited {run.status}: {detail}")
    diags = parse_diagnostics(run.stdout)
    errors = [d for d in diags if d.severity == "error"]
    if run.status == 1 and not errors:
        raise MypyFailed(
            "mypy reported errors this module could not read: "
            f"{run.stdout.strip()!r}"
        )
    if run.status == 0 and errors:
        raise MypyFailed(
            f"mypy reported {len(errors)} error(s) but exited 0; "
            "its contract is not what this module assumes"
        )
    return [to_finding(d, py_lines, smap) for d in _drop_carrier_noise(diags)]


def _module_stem(filename: str) -> str:
    """A filename for the temp copy that keeps the litany's own name.

    The temp file's name becomes the module name mypy reports, so
    `prayer.lit` should be checked as `prayer.py` and not as `tmp8f3a.py`.
    Anything a filesystem might refuse -- the `<litany>` transform uses when
    there is no file at all, a leading dot, a path separator -- is scrubbed
    rather than trusted.
    """
    stem = re.sub(r"[^A-Za-z0-9_.-]", "_", pathlib.PurePath(filename).stem)
    return stem.strip("._-") or "litany"


def check(
    src: str,
    filename: str,
    *,
    oracle: Oracle | None = None,
) -> list[Finding]:
    """Every false archetype in `src`, in Liturgy coordinates.

    An empty list means mypy ran, its answer was understood, and there was
    nothing to report. It never means the check did not happen -- that is
    always an `ArchetypesUnread`.

    Nothing is printed. Rendering belongs to `augur --archetypes`.

    Raises:
        ArchetypesUnread: mypy is missing, failed, or was unintelligible.
        SyntaxError: `src` does not transform or parse. Not a finding, and
            deliberately the same exception `find_collisions` and
            `find_seals` raise for the same litany.
        UnfinishedLitany: `src` ends mid-bracket or mid-string.
        TechHeresy: a construct header is malformed.
    """
    out = transform(src, _PASSES, filename=filename)
    # Parse before spending a mypy run on it, so a litany that is not Python
    # at all fails as a syntax error naming the substitution -- which is a
    # better report than mypy's `Invalid syntax`, and is not a type finding.
    parse_named(out.python, filename, src, out.source_map)

    run_oracle = mypy_oracle() if oracle is None else oracle
    with tempfile.TemporaryDirectory(prefix="liturgy-archetypes-") as tmp:
        root = pathlib.Path(tmp)
        cache = root / "cache"
        path = root / f"{_module_stem(filename)}.py"
        path.write_text(out.python, encoding="utf-8")
        run = run_oracle(path, cache)

    return interpret(run, split_lines(out.python), out.source_map)
