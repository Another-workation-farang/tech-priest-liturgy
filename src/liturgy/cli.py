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

    p_forge = verbs.add_parser("forge", help="compile litanies to bytecode")
    _add_global_flags(p_forge, default=argparse.SUPPRESS)
    p_forge.add_argument("paths", nargs="*")
    p_forge.add_argument(
        "--anew", action="store_true",
        help="forge even litanies whose bytecode is already current",
    )

    p_cons = verbs.add_parser(
        "consecrate", help="check consecrated names across the tree"
    )
    _add_global_flags(p_cons, default=argparse.SUPPRESS)
    p_cons.add_argument("paths", nargs="*")
    p_cons.add_argument(
        "--plain", action="store_true",
        help="emit file:line:col: messages for editors and CI",
    )

    p_prove = verbs.add_parser(
        "prove",
        help="run a litany's trials",
        description="Run pytest with the .lit hook installed and test_*.lit "
                    "collected. Every argument is passed straight to pytest.",
    )
    _add_global_flags(p_prove, default=argparse.SUPPRESS)
    p_prove.add_argument(
        "args", nargs=argparse.REMAINDER,
        help="paths and pytest options, passed through unchanged",
    )

    p_sanct = verbs.add_parser("sanctify", help="set a litany's form in order")
    _add_global_flags(p_sanct, default=argparse.SUPPRESS)
    p_sanct.add_argument("paths", nargs="*")
    p_sanct.add_argument(
        "--check", action="store_true",
        help="report what is unclean without writing anything",
    )

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

    # `prove` hands everything after it to pytest, flags included. argparse
    # would claim a leading `-k` for itself before REMAINDER ever saw it --
    # `chant` escapes that only because a required positional comes first --
    # so prove's tail is lifted out before parsing and put back after.
    passthrough: list[str] = []
    verb_at = next((i for i, a in enumerate(argv) if not a.startswith("-")), None)
    if verb_at is not None and argv[verb_at] == "prove":
        tail = argv[verb_at + 1 :]
        # -h/--help stays with argparse: every other verb answers it, and a
        # wrapper that suddenly shows pytest's help instead is a surprise.
        if not {"-h", "--help"} & set(tail):
            argv, passthrough = argv[: verb_at + 1], tail

    args = _build_parser().parse_args(argv)
    if getattr(args, "verb", None) == "prove" and passthrough:
        args.args = passthrough

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

    if args.verb == "forge":
        from .tooling import forge

        return forge(args.paths, anew=args.anew)

    if args.verb == "consecrate":
        from .tooling import consecrate

        return consecrate(args.paths, plain=args.plain)

    if args.verb == "prove":
        from .tooling import prove

        return prove(args.args)

    if args.verb == "sanctify":
        from .tooling import sanctify

        return sanctify(args.paths, check=args.check)

    if args.verb == "purge":
        from .tooling import purge

        return purge(heresies=args.heresies)

    # The only other verb: the subparser is required, so argparse has already
    # rejected anything else.
    from .commune import commune

    return commune()


if __name__ == "__main__":
    raise SystemExit(main())
