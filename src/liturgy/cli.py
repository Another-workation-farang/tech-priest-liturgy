"""Command line interface."""

from __future__ import annotations

import argparse
import os
import sys

from . import curse, heresy
from .loader import chant as _chant

HERETICAL: dict[str, str] = {"run": "chant", "repl": "commune"}

# Owned by Spec III. Declared here so Core never reuses the names. This
# reserves nothing mechanically -- nothing consults the set at parse time --
# and nothing needs to: argparse rejects any verb it has no subparser for.
RESERVED_VERBS = frozenset(
    {
        "prove",
        "sanctify",
        "forge",
        "consecrate",
        "purge",
        "anoint",
    }
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liturgy")
    parser.add_argument(
        "--absolved",
        action="store_true",
        help=(
            "suppress rebukes for mundane verb names "
            "(must come before the verb)"
        ),
    )
    parser.add_argument(
        "--profane",
        action="store_true",
        help=(
            "render plain Python tracebacks instead of machine curses "
            "(must come before the verb)"
        ),
    )
    verbs = parser.add_subparsers(dest="verb", required=True)

    p_chant = verbs.add_parser("chant", help="execute a litany")
    p_chant.add_argument("file")
    p_chant.add_argument("args", nargs=argparse.REMAINDER)

    verbs.add_parser("commune", help="open an interactive session")

    p_augur = verbs.add_parser("augur", help="read a litany for faults")
    p_augur.add_argument("paths", nargs="+")
    p_augur.add_argument(
        "--plain", action="store_true",
        help="emit file:line:col: messages for editors and CI",
    )

    p_trans = verbs.add_parser("transcribe", help="render Python into Liturgy")
    p_trans.add_argument("source")
    p_trans.add_argument("-o", "--out", dest="dest", default=None)
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

    if args.verb == "augur":
        from .tooling import augur

        return augur(args.paths, plain=args.plain)

    if args.verb == "transcribe":
        from .tooling import transcribe

        return transcribe(args.source, args.dest)

    # The only other verb: the subparser is required, so argparse has already
    # rejected anything else.
    from .commune import commune

    return commune()


if __name__ == "__main__":
    raise SystemExit(main())
