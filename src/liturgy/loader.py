"""Import hook and __main__ execution for .lit files."""

from __future__ import annotations

import importlib
import importlib.util
import linecache
import os
import sys
import types

from importlib.machinery import (
    BYTECODE_SUFFIXES,
    EXTENSION_SUFFIXES,
    SOURCE_SUFFIXES,
    ExtensionFileLoader,
    FileFinder,
    SourceFileLoader,
    SourcelessFileLoader,
)

from .compiler import compile_litany
from .curse import record_source
from .transform import split_lines

SUFFIX = ".lit"


class LiturgyLoader(SourceFileLoader):
    """Compiles Liturgy on import.

    `get_source` is deliberately NOT overridden: the inherited one returns
    the original .lit text, which is what makes linecache and tracebacks
    display Liturgy rather than generated Python.
    """

    def source_to_code(self, data, path, *, _optimize=-1):  # noqa: D102
        src = importlib.util.decode_source(data)
        # The moment of compilation is the only point the exact executed
        # source is known for certain -- record it so a later curse render
        # is correct even if the .lit file is edited on disk afterwards.
        record_source(path, src)
        return compile_litany(src, path, optimize=_optimize)

    def exec_module(self, module):  # noqa: D102
        # Recording in source_to_code alone is not enough: the import system
        # skips compilation entirely when a valid .pyc exists, so from the
        # second run of any program onwards nothing would be recorded and the
        # stale-source guarantee would be silently inert. Executing, unlike
        # compiling, always happens.
        #
        # A cache hit means the .pyc was validated against the file's current
        # mtime and size, so what get_source reads here *is* what was
        # compiled. On a cache miss source_to_code records again, from the
        # bytes it actually compiled, which correctly wins.
        try:
            src = self.get_source(module.__name__)
        except (OSError, ImportError, ValueError):
            src = None  # unreadable or undecodable: skip, never break import
        if src is not None:
            record_source(self.path, src)
        super().exec_module(module)


_installed = False


def install() -> None:
    """Register the .lit path hook. Idempotent."""
    global _installed
    if _installed:
        return

    # The default loader details MUST be included. A hook carrying only our
    # details still matches every directory, shadowing the stdlib FileFinder
    # and breaking all .py imports.
    hook = FileFinder.path_hook(
        (LiturgyLoader, [SUFFIX]),
        (ExtensionFileLoader, EXTENSION_SUFFIXES),
        (SourceFileLoader, SOURCE_SUFFIXES),
        (SourcelessFileLoader, BYTECODE_SUFFIXES),
    )
    sys.path_hooks.insert(0, hook)
    sys.path_importer_cache.clear()
    importlib.invalidate_caches()
    _installed = True


def chant(path: str, argv: list[str]) -> int:
    """Execute a .lit file with __main__ semantics."""
    install()
    path = os.path.abspath(path)
    # decode_source, not open(encoding="utf-8"): it honours a UTF-8 BOM and a
    # PEP 263 `coding:` cookie, which is what the import path does. Reading
    # the same file two different ways gave two different answers -- a BOM'd
    # or latin-1 .lit imported fine and refused to chant.
    with open(path, "rb") as fh:
        src = importlib.util.decode_source(fh.read())

    record_source(path, src)

    # No loader is involved here, so seed linecache by hand or the traceback
    # will have no source lines to show.
    linecache.cache[path] = (
        len(src),
        None,
        split_lines(src),
        path,
    )

    module = types.ModuleType("__main__")
    module.__file__ = path
    module.__loader__ = None
    module.__package__ = None

    # `python file.py` prepends the script's directory to sys.path, and the
    # README promises chant executes a litany the same way. Without this a
    # multi-file Liturgy program is unrunnable via the console script; it only
    # appeared to work when the containing directory happened to be the cwd.
    script_dir = os.path.dirname(path)

    old_main = sys.modules.get("__main__")
    old_argv = sys.argv
    sys.modules["__main__"] = module
    sys.argv = [path, *argv]
    sys.path.insert(0, script_dir)
    try:
        exec(compile_litany(src, path), module.__dict__)
    finally:
        # Remove one occurrence, not every one: the directory may legitimately
        # have been on sys.path already, or the litany may have added it.
        try:
            sys.path.remove(script_dir)
        except ValueError:
            pass
        sys.argv = old_argv
        if old_main is None:
            del sys.modules["__main__"]
        else:
            sys.modules["__main__"] = old_main
    return 0
