"""Command line interface."""

from __future__ import annotations

import argparse
import os
import sys

from . import curse, heresy
from .loader import chant as _chant

HERETICAL: dict[str, str] = {"run": "chant", "repl": "commune"}

# Owned by Spec III. Declared here so Core never reuses the names.
RESERVED_VERBS = frozenset(
    {
        "augur",
        "prove",
        "sanctify",
        "forge",
        "consecrate",
        "purge",
        "anoint",
        "transcribe",
    }
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liturgy")
    parser.add_argument(
        "--absolved",
        action="store_true",
        help="suppress rebukes for mundane verb names",
    )
    parser.add_argument(
        "--profane",
        action="store_true",
        help="render plain Python tracebacks instead of machine curses",
    )
    verbs = parser.add_subparsers(dest="verb", required=True)

    p_chant = verbs.add_parser("chant", help="execute a litany")
    p_chant.add_argument("file")
    p_chant.add_argument("args", nargs=argparse.REMAINDER)

    verbs.add_parser("commune", help="open an interactive session")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Resolve heretical aliases before parsing, remembering the transgression.
    transgression: tuple[str, str] | None = None
    for i, arg in enumerate(argv):
        if arg.startswith("-"):
            continue
        if arg in HERETICAL:
            transgression = (arg, HERETICAL[arg])
            argv[i] = HERETICAL[arg]
        break

    args = _build_parser().parse_args(argv)

    if transgression and not args.absolved:
        heresy.rebuke(*transgression)

    profane = args.profane or os.environ.get("LITURGY_PROFANE") == "1"
    if not profane:
        curse.install()

    if args.verb == "chant":
        return _chant(args.file, args.args)
    if args.verb == "commune":
        from .commune import commune

        return commune()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
