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
        "anoint",
    }
)


def _add_global_flags(parser: argparse.ArgumentParser, *, default) -> None:
    """`--absolved`/`--profane`, accepted before or after the verb.

    The copies on each verb's subparser pass `default=argparse.SUPPRESS`
    rather than False: argparse applies a subparser's defaults *after* the
    parent has parsed, so an ordinary default would silently overwrite a
    flag given before the verb. With SUPPRESS the subparser writes only
    when the flag is actually present, and either position wins.

    One placement caveat remains, by design: `chant`'s REMAINDER hands
    everything after the file to the litany itself, exactly as `python
    file.py --profane` would, so for chant these flags go before the file.
    """
    parser.add_argument(
        "--absolved",
        action="store_true",
        default=default,
        help="suppress rebukes for mundane verb names",
    )
    parser.add_argument(
        "--profane",
        action="store_true",
        default=default,
        help="render plain Python tracebacks instead of machine curses",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liturgy")
    _add_global_flags(parser, default=False)
    verbs = parser.add_subparsers(dest="verb", required=True)

    p_chant = verbs.add_parser("chant", help="execute a litany")
    _add_global_flags(p_chant, default=argparse.SUPPRESS)
    p_chant.add_argument("file")
    p_chant.add_argument("args", nargs=argparse.REMAINDER)

    p_commune = verbs.add_parser("commune", help="open an interactive session")
    _add_global_flags(p_commune, default=argparse.SUPPRESS)

    p_augur = verbs.add_parser("augur", help="read a litany for faults")
    _add_global_flags(p_augur, default=argparse.SUPPRESS)
    p_augur.add_argument("paths", nargs="+")
    p_augur.add_argument(
        "--plain", action="store_true",
        help="emit file:line:col: messages for editors and CI",
    )

    p_trans = verbs.add_parser("transcribe", help="render Python into Liturgy")
    _add_global_flags(p_trans, default=argparse.SUPPRESS)
    p_trans.add_argument("source")
    p_trans.add_argument("-o", "--out", dest="dest", default=None)

    p_purge = verbs.add_parser("purge", help="clear generated caches")
    _add_global_flags(p_purge, default=argparse.SUPPRESS)
    p_purge.add_argument(
        "--heresies", action="store_true", help="also clear the heresy record"
    )
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

    if args.verb == "purge":
        from .tooling import purge

        return purge(heresies=args.heresies)

    # The only other verb: the subparser is required, so argparse has already
    # rejected anything else.
    from .commune import commune

    return commune()


if __name__ == "__main__":
    raise SystemExit(main())
