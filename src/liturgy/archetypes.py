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

    `message` is mypy's own text, untranslated (Task 3's work). `code` is
    mypy's error code, or None for a `note`. `severity` is mypy's word for
    it -- `error` or `note`.
    """

    line: int
    col: int | None
    message: str
    code: str | None
    severity: str


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


def to_finding(diag: Diagnostic, py_lines: list[str], smap) -> Finding:
    """`diag` in Liturgy coordinates.

    The line passes through untouched -- that is the whole feasibility
    argument. The column takes the two steps every offset in this project
    takes: mypy's 1-based UTF-8 *byte* offset into the generated Python line
    becomes a 0-based character offset via `char_offset`, and `to_lit` then
    carries it back across the substitutions to the litany.
    """
    if diag.col is None:
        return Finding(diag.line, None, diag.message, diag.code, diag.severity)
    py_line = py_lines[diag.line - 1] if 0 <= diag.line - 1 < len(py_lines) else ""
    col = smap.to_lit(diag.line, char_offset(py_line, diag.col - 1))
    return Finding(diag.line, col, diag.message, diag.code, diag.severity)


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
