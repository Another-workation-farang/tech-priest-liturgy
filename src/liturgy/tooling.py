"""The tooling verbs: augur, transcribe, forge, consecrate, prove,
sanctify and purge."""

from __future__ import annotations

import importlib.util
import io
import os
import pathlib
import shutil
import sys
import tokenize

from .archetypes import ArchetypesUnread, check, mypy_available
from .collisions import find_collisions
from .compiler import _PASSES, compile_litany
from .constructs import TechHeresy
from .heresy import state_path
from .reverse import to_liturgy
from .form import UnsanctifiableLitany, sanctify_text
from .seals import find_breaches, find_seals
from .transform import UnfinishedLitany, split_lines, transform

_SOURCES = (".lit", ".py")


def _readable(f: pathlib.Path) -> bool:
    """Whether `f` is a candidate for the scan -- a file, or a broken link.

    A dangling `.lit` symlink is not a file, but dropping it silently is the
    same lie as walking past a symlinked directory: something named `.lit`
    was met and never read. Keeping it means `augur` opens it, fails, and
    says so. A symlink to a *directory* is excluded here because
    `unscanned_dirs` already names it.
    """
    return f.is_file() or (f.is_symlink() and not f.is_dir())


def _skipped_quietly(d: pathlib.Path) -> bool:
    """Is `d` a directory the walk prunes without a word?

    Three kinds, all of them noise no adept means to lint: hidden
    directories (`.venv`, `.git`, editor droppings), `__pycache__`, and any
    directory holding a `pyvenv.cfg` -- the marker every virtual
    environment carries, hidden or not. Without this, `augur .` on a
    project with a vendored environment drowned real findings under every
    third-party `.py` that binds `render` or `span`. A directory the
    caller names *directly* is always walked -- naming it is asking.
    """
    return (
        d.name.startswith(".")
        or d.name == "__pycache__"
        or (d / "pyvenv.cfg").is_file()
    )


def _gather(
    paths: list[str],
) -> tuple[list[pathlib.Path], list[tuple[pathlib.Path, str]]]:
    """Files to read, expanding directories to the sources we understand.

    Returns `(files, notes)`. `notes` names, with a reason each, every
    directory that was met and not read: a symlinked directory (never
    entered -- a `.lit` file behind one is invisible to the walk, and
    reporting the tree clean without a word about it would be the one
    thing a linter must not do) and a directory the walk could not open.
    Directories pruned as noise (see `_skipped_quietly`) are not noted;
    hidden files are skipped the same way. The path the caller names
    directly is never skipped by any of these rules -- naming it is asking
    for it, symlink, hidden or not.

    Files are deduplicated across arguments, so overlapping paths --
    `augur quiet.lit .` -- report each finding once.
    """
    files: list[pathlib.Path] = []
    notes: list[tuple[pathlib.Path, str]] = []
    seen: set[str] = set()

    def claim(f: pathlib.Path) -> None:
        key = os.path.abspath(f)
        if key not in seen:
            seen.add(key)
            files.append(f)

    def walk(d: pathlib.Path, collected, skipped) -> None:
        try:
            entries = sorted(d.iterdir())
        except OSError as err:
            skipped.append((d, f"cannot be read: {err.strerror}"))
            return
        for entry in entries:
            if entry.is_dir() and not entry.is_symlink():
                if not _skipped_quietly(entry):
                    walk(entry, collected, skipped)
            elif entry.is_dir():
                # A symlinked directory is never entered. One that is noise
                # anyway -- a symlinked `.venv`, say -- is pruned as
                # quietly as its real counterpart would be; any other is
                # named, not passed over in silence.
                if not _skipped_quietly(entry):
                    skipped.append((
                        entry,
                        "symlinked directory: not descended into, not scanned",
                    ))
            elif entry.suffix in _SOURCES and _readable(entry):
                if entry.name.startswith("."):
                    # A hidden source file is skipped -- but a reader that
                    # quietly does not read a file is worse than no
                    # reader, so it is named; name it directly to read it.
                    skipped.append((entry, "hidden: not read"))
                else:
                    collected.append(entry)

    for raw in paths:
        p = pathlib.Path(raw)
        if p.is_dir():
            collected: list[pathlib.Path] = []
            skipped: list[tuple[pathlib.Path, str]] = []
            walk(p, collected, skipped)
            for f in sorted(collected):
                claim(f)
            for note in sorted(skipped):
                if note not in notes:
                    notes.append(note)
        else:
            claim(p)
    return files, notes


def _report(path, line, src_line, col, width, message, *, out) -> None:
    print("++ THE OMENS ARE TROUBLED ++", file=out)
    print(f"   {path}, line {line}", file=out)
    if src_line:
        print(f"       {src_line}", file=out)
        print(f"       {' ' * col}{'^' * max(width, 1)}", file=out)
    print(f"   {message}", file=out)


def augur(
    paths: list[str],
    *,
    plain: bool = False,
    archetypes: bool = False,
    oracle=None,
    out=None,
) -> int:
    """Read litanies for faults without chanting them. 0 clean, 1 findings.

    Two checks always, and a third only when it is asked for. Collisions
    and the compile are cheap enough to run on every keystroke; reading
    archetypes spawns mypy and is not, so `archetypes` is a flag and the
    two standing checks behave identically whether or not it is passed.

    **Only litanies are read for archetypes.** A `.py` file is still
    scanned by the two standing checks, but it has no substitutions and so
    no `SourceMap`, which means nothing this verb could say about it would
    be in Liturgy coordinates -- it would be mypy's own report, wearing
    Liturgy's banner. Running mypy on Python is mypy's job, and the user
    can run it directly and get better output than this could relay. A
    `.py` beside litanies is simply skipped; a run whose files held **no**
    litany at all says so and exits 1, because a check that was asked for
    and never happened must not read as a check that found nothing.

    `oracle` is the seam `archetypes.check` documents, passed straight
    through: the trials use it to run a real mypy from an environment the
    core does not have. When it is given, the "is mypy installed here"
    gate below is skipped, because the caller has supplied the oracle that
    gate exists to find.
    """
    out = out if out is not None else sys.stdout
    troubled = False

    if archetypes and oracle is None and not mypy_available():
        # Refused before the walk, as `prove` refuses without pytest. Doing
        # two thirds of what was asked and exiting 1 anyway would leave the
        # reader to work out which third was missing.
        print("++ CANNOT READ ARCHETYPES: mypy is not installed ++", file=out)
        print(
            "   reading them needs it:  pip install 'liturgy[archetypes]'",
            file=out,
        )
        return 1

    files, notes = _gather(paths)
    # Whether the third check had anything it could be run on. Asked for and
    # never run is the silent success this module's docstring calls the worst
    # outcome available, and it has to be said out loud rather than left to
    # an empty report the reader will read as "clean".
    saw_litany = False

    for d, message in notes:
        troubled = True
        _emit_bare(d, message, plain=plain, out=out)

    for path in files:
        # decode_source, not read_text(encoding="utf-8"): a BOM or a PEP 263
        # `coding:` cookie must be honoured exactly as `chant`, `transcribe`
        # and the import path honour it, or augur invents faults of its own
        # reading -- a stripped BOM reported as an invalid character, a
        # latin-1 cookie as a crash -- and stops agreeing with chant.
        # UnicodeDecodeError is a ValueError, not an OSError: caught here
        # rather than left to escape an `-> int` contract and end the walk.
        try:
            src = importlib.util.decode_source(path.read_bytes())
        except OSError as err:
            troubled = True
            _emit_bare(path, f"cannot be read: {err.strerror}", plain=plain, out=out)
            continue
        except (SyntaxError, UnicodeDecodeError, LookupError) as err:
            troubled = True
            _emit_bare(path, f"cannot be decoded: {err}", plain=plain, out=out)
            continue

        liturgy = path.suffix == ".lit"
        saw_litany = saw_litany or liturgy
        try:
            collisions = find_collisions(src, str(path), liturgy=liturgy)
        except UnfinishedLitany:
            troubled = True
            _emit_bare(
                path, "omens unread: the litany does not tokenise",
                plain=plain, out=out,
            )
            continue
        except SyntaxError as err:
            troubled = True
            _emit_bare(
                path, f"{type(err).__name__}: {err.msg}",
                line=err.lineno or 1, plain=plain, out=out,
            )
            continue
        except ValueError as err:
            # e.g. a null byte in a .py file: compile() raises ValueError,
            # not SyntaxError, and an -> int contract does not traceback.
            troubled = True
            _emit_bare(path, f"cannot be compiled: {err}", plain=plain, out=out)
            continue

        compiles = True
        if liturgy:
            # Compiling is what makes augur agree with chant. Collisions are
            # already in hand, so a failure here is something else entirely.
            try:
                compile_litany(src, str(path))
            except SyntaxError as err:
                troubled = True
                compiles = False
                _emit_bare(
                    path, f"{type(err).__name__}: {err.msg}",
                    line=err.lineno or 1, plain=plain, out=out,
                )

        lines = split_lines(src)
        for c in collisions:
            troubled = True
            if c.target is None:
                note = (
                    f"{c.word} is the machine's own name; "
                    "a litany may not speak it"
                )
            else:
                note = f"{c.word} is reserved; it becomes {c.target}"
                if c.quiet:
                    note += " -- silently"
            if plain:
                print(f"{path}:{c.line}:{c.col + 1}: {note}", file=out)
            else:
                text = lines[c.line - 1].rstrip("\n") if c.line <= len(lines) else ""
                _report(path, c.line, text, c.col, len(c.word), note, out=out)

        # Last, and only for a litany that got as far as compiling: `check`
        # transforms and parses again, and would raise the same SyntaxError
        # the compile above has already reported in better words.
        if archetypes and liturgy and compiles:
            if _read_archetypes(
                path, src, lines, plain=plain, oracle=oracle, out=out
            ):
                troubled = True

    if archetypes and not saw_litany:
        # The same shape as the missing-mypy refusal above, and for the same
        # reason: the reader asked for archetypes and got none, and an empty
        # report plus exit 0 would let them believe a check happened. Only
        # when *no* litany was read at all -- a .py beside litanies is the
        # documented, harmless case and says nothing.
        print("++ NO ARCHETYPES WERE READ: no litany was given ++", file=out)
        print(
            "   only .lit files carry the substitutions this check maps back",
            file=out,
        )
        troubled = True

    return 1 if troubled else 0


def _read_archetypes(path, src, lines, *, plain, oracle, out) -> bool:
    """Report one litany's false archetypes. True if there was anything.

    The distinction this function exists to keep is the one
    `archetypes.check` is built around: an empty list of findings means
    mypy ran and found nothing, and *every* other outcome is an
    `ArchetypesUnread` that must read as "unread" and never as "clean".
    Hence "archetypes unread", the same words `augur` and `consecrate`
    already use for omens and seals they could not read, and never
    silence.

    An unread litany does not end the walk either -- the next file is still
    read -- so the exception is caught here rather than allowed past
    `augur`'s `-> int`.
    """
    try:
        findings = check(src, str(path), oracle=oracle)
    except ArchetypesUnread as err:
        _emit_bare(path, f"archetypes unread: {err}", plain=plain, out=out)
        return True
    except SyntaxError as err:
        # Not reachable through `augur`, which has already compiled this
        # litany, but `check` is documented to let these through and a
        # reader that dies on the third file of forty is no reader.
        _emit_bare(
            path, f"archetypes unread: {type(err).__name__}: {err.msg}",
            line=err.lineno or 1, plain=plain, out=out,
        )
        return True

    after_error = False
    for f in findings:
        # mypy's own convention: the code in brackets at the end, which is
        # what a reader greps for and what `# type: ignore[...]` names.
        note = f.message if f.code is None else f"{f.message}  [{f.code}]"
        if f.severity == "note" and after_error:
            # A note explains the error above it. Giving it its own banner
            # would announce a second fault that does not exist.
            if plain:
                col = 1 if f.col is None else f.col + 1
                print(f"{path}:{f.line}:{col}: note: {note}", file=out)
            else:
                print(f"   note: {note}", file=out)
            continue
        after_error = f.severity == "error"
        if f.severity == "note":
            note = f"note: {note}"
        elif not f.translated:
            # `Finding.translated` exists for exactly this: a diagnostic
            # the checker's words could not be confidently rendered into
            # Liturgy is attributed to the checker, not passed off as
            # Liturgy's own. It is why the litany's author is suddenly
            # being told about `def` and `return`.
            note = f"mypy's own words: {note}"
        if f.col is None:
            # No caret, and no column invented for one. A caret under
            # column 0 is a claim about where the fault is.
            _emit_bare(path, note, line=f.line, plain=plain, out=out)
        elif plain:
            print(f"{path}:{f.line}:{f.col + 1}: {note}", file=out)
        else:
            text = lines[f.line - 1].rstrip("\n") if f.line <= len(lines) else ""
            _report(path, f.line, text, f.col, 1, note, out=out)
    return bool(findings)


def _emit_bare(path, message, *, line: int = 1, plain: bool, out) -> None:
    if plain:
        print(f"{path}:{line}:1: {message}", file=out)
    else:
        _report(path, line, "", 0, 0, message, out=out)


def _newline_style(raw: bytes) -> str:
    """The line ending `raw` was written with, so the output can keep it.

    `decode_source` (like `read_text`) performs universal-newline
    translation on the way in, so by the time `src` exists as `str` the
    original bytes' line endings are gone and the round-trip self-check --
    which compares that already-normalised text against `back` -- cannot
    see a CRLF-to-LF change happen underneath it. Detecting the style here,
    from the untranslated bytes, and re-applying it to the output at the
    very end is what keeps the written file's *bytes*, not just its text,
    faithful to the source -- rewriting a user's line endings without a
    word about it is exactly the kind of silent lie `transcribe` exists to
    refuse elsewhere.
    """
    return "\r\n" if b"\r\n" in raw else "\n"


def _source_encoding(raw: bytes) -> str:
    """The encoding named by `raw`'s BOM or PEP 263 `coding:` cookie.

    `decode_source` already runs `tokenize.detect_encoding` internally to
    decide how to decode `raw`; calling it again here is cheap (it only
    reads the first two lines) and returns the same name, so the
    destination can be written back in the encoding the source actually
    declared -- 'utf-8-sig' for a BOM, the cookie's name otherwise --
    instead of always UTF-8. Same rule as `_newline_style`: transcribe
    preserves the file's physical properties and changes only the words.
    """
    encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
    return encoding


def _collision_row(label: str, c) -> str:
    what = "the machine's own" if c.target is None else f"reserved ({c.target})"
    return f"  {label}:{c.line}  {c.word:<12} -> {what}"


def _output_omens(litany: str, label: str) -> list[str]:
    """Everything the reader must know about the Liturgy about to be written.

    Two omens, in the order a reader needs them: what `augur` will say
    about the output's names, and whether the output chants at all.
    """
    return _collision_omens(litany, label) + _archetype_omens(litany, label)


def _collision_omens(litany: str, label: str) -> list[str]:
    """What `augur` will say about the Liturgy `transcribe` is about to emit.

    `transcribe` refuses on collisions in its *input*, but `to_liturgy` can
    bind a reserved word the Python never did: `def encode(self, input)`
    becomes `rite encode(self, hearken)`, and `hearken` is reserved. Over a
    stdlib sample that is about one file in five. The output is not wrong --
    it round-trips, compiles and runs identically -- so this warns rather
    than refuses; refusing to write correct code would be the worse
    failure. Warning here is what stops the transcribe-then-augur workflow
    surprising people, and it costs one call to machinery already imported.
    """
    try:
        collisions = find_collisions(litany, label, liturgy=True)
    except SyntaxError:
        # The output has already round-tripped through `transform`, so this
        # is not reachable by a fault the user can act on. Say nothing
        # rather than turn a warning path into a second failure path.
        return []
    if not collisions:
        return []
    plural = "S" if len(collisions) != 1 else ""
    lines = [f"++ THE OUTPUT CARRIES {len(collisions)} COLLISION{plural} ++"]
    lines += [_collision_row(label, c) for c in collisions]
    # No longer "and chants as written": since Spec IV a faithful
    # transcription may still need archetypes before it will chant, and
    # `_archetype_omens` says so on its own line. Claiming both would have
    # the two warnings contradict each other in the same breath.
    lines.append("augur will flag these; the words are faithful and run the same")
    return lines


def _archetype_omens(litany: str, label: str) -> list[str]:
    """Whether the Liturgy `transcribe` is about to emit will chant.

    Since Spec IV a rite must declare an archetype for each parameter and
    for what it renders, and a consecrated name must declare one too.
    Python requires none of that, so a transcription is unannotated by
    definition and will not chant as written.

    The backstop above therefore compiles with the rule suppressed, and
    this is the other half of that bargain: it is the same rule, run on
    purpose, to warn instead of refuse. Nothing is prepended to the output
    -- an `unsanctioned` line ahead of the litany breaks transcribe's own
    round-trip self-check (`transform("unsanctioned\n" + lit) != src`),
    which is the guarantee that makes the verb trustworthy at all. The one
    word the user must type is cheaper than that guarantee.

    Compiling a second time is the cost of telling the truth here. It buys
    the exact fault and its line, and it stays silent on a source that was
    annotated in Python -- where a blanket warning would be a lie.
    """
    try:
        compile_litany(litany, label)
    except TechHeresy as err:
        first = f"  {label}:{err.lineno}  {err.msg}"
    except SyntaxError:
        # Already compiled once without the rule, so anything else here is
        # not a fault the user can act on. Say nothing rather than turn a
        # warning path into a second failure path.
        return []
    else:
        return []
    return [
        "++ THE OUTPUT WILL NOT CHANT AS WRITTEN ++",
        first,
        "Python does not require archetypes and Liturgy does. declare one for "
        "every",
        "parameter and return and every consecrated name, or write "
        "`unsanctioned`",
        "before a rite to exempt it -- or alone at the margin to exempt the "
        "file.",
    ]


def transcribe(source: str, dest: str | None = None, *, out=None) -> int:
    """Render a Python file into Liturgy. 0 written, 1 refused."""
    out = out if out is not None else sys.stdout
    path = pathlib.Path(source)

    try:
        raw = path.read_bytes()
    except OSError as err:
        print(f"++ CANNOT TRANSCRIBE: {path} {err.strerror} ++", file=out)
        return 1

    # decode_source, not read_text(encoding="utf-8"): it honours a UTF-8 BOM
    # and a PEP 263 `coding:` cookie, so a latin-1 or BOM'd source decodes
    # the same way the import path decodes it, instead of being reported as
    # a bogus SyntaxError or crashing outright.
    try:
        src = importlib.util.decode_source(raw)
        encoding = _source_encoding(raw)
    except (SyntaxError, UnicodeDecodeError, LookupError) as err:
        print(f"++ CANNOT TRANSCRIBE: {path} cannot be decoded: {err} ++", file=out)
        return 1

    newline = _newline_style(raw)

    try:
        collisions = find_collisions(src, str(path), liturgy=False)
    except SyntaxError as err:
        print(
            f"++ CANNOT TRANSCRIBE: {type(err).__name__} at line {err.lineno} ++",
            file=out,
        )
        return 1
    except ValueError as err:
        # e.g. a null byte: compile() raises ValueError, not SyntaxError,
        # and an -> int contract does not traceback.
        print(f"++ CANNOT TRANSCRIBE: {path} cannot be compiled: {err} ++", file=out)
        return 1

    if collisions:
        print(
            f"++ CANNOT TRANSCRIBE: {len(collisions)} "
            f"COLLISION{'S' if len(collisions) != 1 else ''} ++",
            file=out,
        )
        for c in collisions:
            print(_collision_row(str(path), c), file=out)
        print("rename these, then chant again", file=out)
        return 1

    litany = to_liturgy(src)

    # Verify before writing. This is the round-trip property test applied to
    # one real file: if the output does not transform back to the input, the
    # output is wrong and must not reach disk claiming otherwise.
    heretical = False
    try:
        # `_PASSES`, not the default: the reverse pass emits `introit:` for
        # a main guard, and `introit` is a construct word the alias pass
        # alone does not expand. Checked against DEFAULT_PASSES this would
        # declare every transcription of a file with a main guard broken.
        back = transform(litany, _PASSES, filename=str(path)).python
    except TechHeresy:
        # Running the carrier pass here means this now sees the construct
        # heresies too -- `consecrated = 5` is valid Python that no litany
        # may spell. That is not a round-trip fault and must not be reported
        # as one: the backstop below says which construct and which line,
        # and "a fault in Liturgy, not in your source" would be a lie about
        # a fault that is squarely in the source.
        back, heretical = None, True
    except SyntaxError:
        back = None
    if back != src and not heretical:
        print("++ CANNOT TRANSCRIBE: the output does not round-trip ++", file=out)
        print("   this is a fault in Liturgy, not in your source", file=out)
        return 1

    # Round-tripping proves the words are faithful; it does not prove they
    # chant. A Python source can spell what a litany may not -- a bare
    # `consecrated = 5`, a call to its own `__litany__` -- and the collision
    # check catches only bindings. Compiling the output is the backstop
    # that catches every such shape at once, before anything claims the
    # transcription succeeded.
    #
    # `sanction=False`, and only here. Those shapes are *structural*: text
    # that is not Liturgy at all, which no edit short of a rewrite will
    # save. Spec IV's archetype rule is a different kind of thing -- a
    # policy about litanies an author writes, not a property of well-formed
    # Liturgy. Python does not require annotations, so transcribed Python
    # has none by definition, and refusing on that ground refused every
    # real Python file with a function in it, which is the whole purpose of
    # the verb. The backstop asks "is this a program?"; whether it meets
    # the policy is the omens' business, three lines below.
    label = dest if dest is not None else str(path)
    try:
        compile_litany(litany, label, sanction=False)
    except SyntaxError as err:
        print("++ CANNOT TRANSCRIBE: the output would not chant ++", file=out)
        print(f"   line {err.lineno}: {err.msg}", file=out)
        print("rewrite or rename what it names, then transcribe again", file=out)
        return 1
    except ValueError as err:
        print("++ CANNOT TRANSCRIBE: the output would not chant ++", file=out)
        print(f"   {err}", file=out)
        return 1

    output = litany if newline == "\n" else litany.replace("\n", newline)
    omens = _output_omens(litany, label)

    if dest is None:
        print(output, end="", file=out)
        # stdout is the payload in this mode, not a report. A diagnostic
        # spliced into it would be exactly the silent corruption transcribe
        # exists to refuse, so the warning goes to stderr instead.
        for line in omens:
            print(line, file=sys.stderr)
        return 0

    # Encode in the source's own declared encoding, not always UTF-8: a
    # destination that carries the source's `coding:` cookie forward
    # verbatim (we never touch it -- it lives in a comment) but is written
    # in a different encoding is corrupt for every reader that honours that
    # cookie, this project's own loader included. This is not a case the
    # substitutions can trigger -- every reserved word is ASCII -- but
    # refuse rather than raise if it ever did.
    try:
        payload = output.encode(encoding)
    except (LookupError, UnicodeEncodeError) as err:
        print(
            f"++ CANNOT TRANSCRIBE: cannot encode the output as {encoding}: "
            f"{err} ++",
            file=out,
        )
        return 1

    # A second, byte-level round-trip: decode the exact bytes about to be
    # written the way a consumer honouring the destination's own cookie
    # would -- our loader, or CPython itself -- and confirm they still say
    # what we mean to write, i.e. `litany` (compared, not `output`, since
    # `decode_source` normalises newlines the same way it did for `src`).
    # The text-level check above compares `back` against `src`, neither of
    # which ever touches an encoding, so it cannot see bytes that are wrong
    # for the encoding their own cookie declares; this can.
    try:
        byte_roundtrip = importlib.util.decode_source(payload)
    except (SyntaxError, UnicodeDecodeError, LookupError):
        byte_roundtrip = None
    if byte_roundtrip != litany:
        print("++ CANNOT TRANSCRIBE: the output does not round-trip ++", file=out)
        print("   this is a fault in Liturgy, not in your source", file=out)
        return 1

    try:
        pathlib.Path(dest).write_bytes(payload)
    except OSError as err:
        print(
            f"++ CANNOT TRANSCRIBE: cannot write {dest}: {err.strerror} ++",
            file=out,
        )
        return 1
    print(f"++ {len(split_lines(litany))} lines transcribed ++", file=out)
    for line in omens:
        print(line, file=out)
    return 0


def purge(*, heresies: bool = False, root: str | None = None, out=None) -> int:
    """Clear generated caches. 0 done, 1 refused.

    The only destructive verb, so it is guarded: it refuses unless the tree
    holds at least one .lit file, because a recursive delete in the wrong
    directory is a bad afternoon. Symlinked directories are never entered --
    `rglob` does not follow them, and each candidate is checked anyway.

    A candidate that cannot be removed (permissions, or the directory
    vanishing between `rglob` and the delete) is reported and skipped
    rather than left to raise -- one unreadable directory must not strand
    the rest, and this is an `-> int` contract, not a traceback. Each
    `purged` line is printed only once the delete underneath it has
    actually succeeded, so the report never claims a deletion that didn't
    happen.
    """
    out = out if out is not None else sys.stdout
    base = pathlib.Path(root) if root is not None else pathlib.Path.cwd()

    if not any(base.rglob("*.lit")):
        print(f"++ {base} does not look like a Liturgy forge ++", file=out)
        print("   no .lit file found; refusing to delete anything", file=out)
        return 1

    removed = 0
    failed = False
    for cache in sorted(base.rglob("__pycache__")):
        if cache.is_symlink() or not cache.is_dir():
            continue
        try:
            shutil.rmtree(cache)
        except OSError as err:
            failed = True
            print(f"++ CANNOT PURGE: {cache} {err.strerror} ++", file=out)
            continue
        print(f"   purged {cache}", file=out)
        removed += 1

    if heresies:
        state = state_path()
        if state.exists():
            try:
                state.unlink()
            except OSError as err:
                failed = True
                print(f"++ CANNOT PURGE: {state} {err.strerror} ++", file=out)
            else:
                print(f"   purged {state}", file=out)
                removed += 1

    print(f"++ {removed} relic{'' if removed == 1 else 's'} purged ++", file=out)
    return 1 if failed else 0


def _cache_stamp(path: pathlib.Path) -> tuple[bool, float]:
    """Whether bytecode exists for `path`, and its mtime.

    Comparing this either side of the compile is how forging tells a litany
    it wrote from one the import system judged already current -- exact,
    where comparing source and cache mtimes would only be a guess, and
    without reading the `.pyc` header this module has no business parsing.
    """
    try:
        cache = pathlib.Path(importlib.util.cache_from_source(str(path)))
    except (NotImplementedError, ValueError):
        return False, 0.0
    try:
        return True, cache.stat().st_mtime
    except OSError:
        return False, 0.0


def forge(paths: list[str], *, anew: bool = False, out=None) -> int:
    """Compile litanies to bytecode before their first import. 0 done, 1 refused.

    Only `.lit` files are forged. Turning `.py` into `.pyc` is `compileall`'s
    work and Liturgy adds nothing to it.

    The compiling is done by the import system's own `get_code`, not by hand:
    it runs this project's loader, so the bytecode is byte-for-byte what an
    import would have produced, and CPython -- not this function -- decides
    whether an existing cache is still valid. It compiles without executing,
    which is the whole difference between forging a litany and importing one.
    """
    out = out if out is not None else sys.stdout
    from .loader import LiturgyLoader

    if sys.dont_write_bytecode:
        # Every write would be a silent no-op, so forging would report
        # success and leave nothing behind.
        print("++ CANNOT FORGE: this interpreter will not write bytecode ++", file=out)
        print("   -B or PYTHONDONTWRITEBYTECODE is in force", file=out)
        return 1

    files, notes = _gather(paths or ["."])
    failed = False

    for d, message in notes:
        failed = True
        print(f"++ CANNOT FORGE: {d} {message} ++", file=out)

    litanies = [f for f in files if f.suffix == ".lit"]
    forged = current = 0

    for path in litanies:
        existed, before = _cache_stamp(path)
        if anew and existed:
            try:
                pathlib.Path(importlib.util.cache_from_source(str(path))).unlink()
            except OSError:
                pass  # get_code overwrites it anyway; the unlink is only a hint
            existed = False

        try:
            LiturgyLoader(path.stem, str(path)).get_code(path.stem)
        except OSError as err:
            failed = True
            print(f"++ CANNOT FORGE: {path} {err.strerror or err} ++", file=out)
            continue
        except SyntaxError as err:
            # err.msg, not str(err): the latter re-appends "(file, line N)",
            # which this line has already said.
            failed = True
            where = f" line {err.lineno}" if err.lineno else ""
            print(
                f"++ CANNOT FORGE: {path}{where} "
                f"{type(err).__name__}: {err.msg} ++",
                file=out,
            )
            continue
        except (ValueError, UnicodeDecodeError, LookupError) as err:
            failed = True
            print(f"++ CANNOT FORGE: {path} {type(err).__name__}: {err} ++", file=out)
            continue

        exists_now, after = _cache_stamp(path)
        if exists_now and (not existed or after != before):
            print(f"   forged {path}", file=out)
            forged += 1
        else:
            current += 1

    if not litanies:
        print("++ no litanies to forge ++", file=out)
        return 1 if failed else 0

    tail = f", {current} already current" if current else ""
    print(
        f"++ {forged} litan{'y' if forged == 1 else 'ies'} forged{tail} ++",
        file=out,
    )
    return 1 if failed else 0


def _decoded(path, *, plain, out, verb):
    """Source text, or None having reported why not. See `augur` for the why."""
    try:
        return importlib.util.decode_source(path.read_bytes())
    except OSError as err:
        print(f"++ CANNOT {verb}: {path} cannot be read: {err.strerror} ++", file=out)
    except (SyntaxError, UnicodeDecodeError, LookupError) as err:
        print(f"++ CANNOT {verb}: {path} cannot be decoded: {err} ++", file=out)
    return None


def consecrate(paths: list[str], *, plain: bool = False, out=None) -> int:
    """Check consecrated names against the whole tree. 0 held, 1 broken.

    `consecrated` enforces per compilation unit, so the compiler cannot see a
    rebinding that arrives from another file. This walks the tree twice --
    once to learn what is sealed, once to find what breaks a seal -- and
    reports the pairs.

    It is a report, not an enforcement: nothing here stops the rebinding at
    run time, and `globals()` and a computed `setattr` name stay invisible
    to it. Chapter VII's boundary moves; it does not disappear.
    """
    out = out if out is not None else sys.stdout
    files, notes = _gather(paths or ["."])
    broken = False

    for d, message in notes:
        broken = True
        print(f"++ CANNOT CONSECRATE: {d} {message} ++", file=out)

    # Pass one: what is sealed, and where.
    sealed: dict[str, set[str]] = {}
    where: dict[tuple[str, str], tuple[pathlib.Path, object, str]] = {}
    ambiguous: dict[str, set[str]] = {}
    sources: dict[pathlib.Path, str] = {}

    for path in files:
        src = _decoded(path, plain=plain, out=out, verb="CONSECRATE")
        if src is None:
            broken = True
            continue
        sources[path] = src
        if path.suffix != ".lit":
            continue
        try:
            found = find_seals(src, str(path), liturgy=True)
        except UnfinishedLitany:
            broken = True
            _emit_bare(path, "seals unread: the litany does not tokenise",
                       plain=plain, out=out)
            continue
        except SyntaxError as err:
            broken = True
            _emit_bare(path, f"{type(err).__name__}: {err.msg}",
                       line=err.lineno or 1, plain=plain, out=out)
            continue
        for seal in found:
            ambiguous.setdefault(seal.module, set()).add(str(path))
            sealed.setdefault(seal.module, set()).add(seal.name)
            where[(seal.module, seal.name)] = (path, seal, src)

    total = sum(len(v) for v in sealed.values())
    if not sealed:
        if not plain:
            print("++ no consecrated names found ++", file=out)
        return 1 if broken else 0

    # Two modules sharing a basename make `module.NAME` ambiguous, and the
    # walk resolves by basename. Say so rather than reporting confidently.
    for module, homes in sorted(ambiguous.items()):
        if len(homes) > 1:
            print(
                f"++ {module} is the name of {len(homes)} litanies; "
                "seals for it are matched by basename ++",
                file=out,
            )
            for h in sorted(homes):
                print(f"   {h}", file=out)

    # Pass two: who breaks one.
    breaches = []
    for path in files:
        src = sources.get(path)
        if src is None:
            continue
        try:
            breaches.extend(
                (path, b)
                for b in find_breaches(
                    src, str(path), sealed, liturgy=path.suffix == ".lit"
                )
            )
        except (UnfinishedLitany, SyntaxError):
            continue  # already reported in pass one for .lit; a .py is not ours

    by_seal: dict[tuple[str, str], list] = {}
    for path, b in breaches:
        by_seal.setdefault((b.module, b.name), []).append((path, b))

    for key in sorted(by_seal, key=lambda k: (k[0], k[1])):
        broken = True
        seal_path, seal, seal_src = where[key]
        module, name = key
        if plain:
            for path, b in by_seal[key]:
                print(
                    f"{path}:{b.line}:{b.col + 1}: {name} is consecrated in "
                    f"{seal_path} line {seal.line} and {b.how} here",
                    file=out,
                )
            continue
        lines = split_lines(seal_src)
        text = lines[seal.line - 1].rstrip("\n") if seal.line <= len(lines) else ""
        print("++ THE SEAL IS BROKEN ++", file=out)
        print(f"   {seal_path}, line {seal.line}", file=out)
        print(f"       {text}", file=out)
        print(f"       {' ' * seal.col}{'^' * len(name)}", file=out)
        print(f"   {name} is consecrated here, and reached in:", file=out)
        for path, b in sorted(by_seal[key], key=lambda pb: (str(pb[0]), pb[1].line)):
            print(f"     {b.how:9} {path}:{b.line}", file=out)
        print("", file=out)

    if not plain:
        # --plain is for editors and CI, like augur's: machine-readable
        # lines and nothing else to parse around.
        held = total - len(by_seal)
        print(
            f"++ {len(by_seal)} seal{'' if len(by_seal) == 1 else 's'} broken, "
            f"{held} held ++",
            file=out,
        )
    return 1 if broken else 0


def prove(args: list[str], *, out=None) -> int:
    """Run a litany's trials. Returns pytest's own exit code.

    Convenience, and openly nothing more: pytest already imports a `.lit`
    module through the hook, and a seven-line `conftest.py` already collects
    `test_*.lit`. This installs the hook and supplies that collector as a
    plugin, so a project needs neither.

    Everything in `args` goes straight to pytest -- paths, `-k`, `-v`, any
    of it. The exit code is pytest's, passed through rather than flattened
    to 0/1: 0 all passed, 1 failures, 5 nothing collected, and so on. A test
    runner that lies about which of those happened is worse than none.
    """
    out = out if out is not None else sys.stdout
    try:
        import pytest
    except ImportError:
        print("++ CANNOT PROVE: pytest is not installed ++", file=out)
        print("   the trials need it:  pip install 'liturgy[trials]'", file=out)
        return 1

    from .loader import install
    from .trials import LitanyTrials

    # The hook must be live before collection, or importing a `.lit` module
    # from a trial fails and `.lit` files are unimportable even once
    # collected.
    install()
    return int(pytest.main(list(args), plugins=[LitanyTrials()]))


def sanctify(paths: list[str], *, check: bool = False, out=None) -> int:
    """Set litanies' form in order. 0 done, 1 refused or (with check) unclean.

    Only `.lit` files. Formatting Python is `ruff`'s or `black`'s work, and
    neither of them can read a litany -- which is the whole reason this
    exists.

    Encoding, line endings and BOM are preserved exactly as `transcribe`
    preserves them: the verb reshapes whitespace between tokens and changes
    nothing else about the file's physical form. A litany it cannot prove
    it kept intact is left exactly as it was.
    """
    out = out if out is not None else sys.stdout
    files, notes = _gather(paths or ["."])
    failed = False

    for d, message in notes:
        failed = True
        print(f"++ CANNOT SANCTIFY: {d} {message} ++", file=out)

    litanies = [f for f in files if f.suffix == ".lit"]
    changed = clean = 0

    for path in litanies:
        try:
            raw = path.read_bytes()
        except OSError as err:
            failed = True
            print(f"++ CANNOT SANCTIFY: {path} {err.strerror} ++", file=out)
            continue
        try:
            src = importlib.util.decode_source(raw)
        except (SyntaxError, UnicodeDecodeError, LookupError) as err:
            failed = True
            print(f"++ CANNOT SANCTIFY: {path} cannot be decoded: {err} ++", file=out)
            continue

        try:
            formed = sanctify_text(src)
        except UnsanctifiableLitany as err:
            failed = True
            print(f"++ CANNOT SANCTIFY: {path} {err} ++", file=out)
            continue

        if formed == src:
            clean += 1
            continue

        changed += 1
        if check:
            print(f"   unclean {path}", file=out)
            continue

        newline = _newline_style(raw)
        encoding = _source_encoding(raw)
        payload = formed.replace("\n", newline)
        try:
            path.write_bytes(payload.encode(encoding))
        except (OSError, UnicodeEncodeError, LookupError) as err:
            failed = True
            print(f"++ CANNOT SANCTIFY: {path} cannot be written: {err} ++", file=out)
            continue
        print(f"   sanctified {path}", file=out)

    if not litanies:
        print("++ no litanies to sanctify ++", file=out)
        return 1 if failed else 0

    if check:
        print(
            f"++ {changed} unclean, {clean} already in order ++", file=out
        )
        return 1 if (failed or changed) else 0

    print(f"++ {changed} sanctified, {clean} already in order ++", file=out)
    return 1 if failed else 0
