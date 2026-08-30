"""Import hook and __main__ execution for .lit files."""

from __future__ import annotations

import importlib
import importlib.machinery
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

from .transform import transform

SUFFIX = ".lit"


class LiturgyLoader(SourceFileLoader):
    """Compiles Liturgy on import.

    `get_source` is deliberately NOT overridden: the inherited one returns
    the original .lit text, which is what makes linecache and tracebacks
    display Liturgy rather than generated Python.
    """

    def source_to_code(self, data, path, *, _optimize=-1):  # noqa: D102
        src = importlib.util.decode_source(data)
        py, _smap = transform(src)
        return compile(
            py, path, "exec", dont_inherit=True, optimize=_optimize
        )


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
    with open(path, encoding="utf-8") as fh:
        src = fh.read()

    py, _smap = transform(src)

    # No loader is involved here, so seed linecache by hand or the traceback
    # will have no source lines to show.
    linecache.cache[path] = (
        len(src),
        None,
        src.splitlines(keepends=True),
        path,
    )

    module = types.ModuleType("__main__")
    module.__file__ = path
    module.__loader__ = None
    module.__package__ = None
    sys.modules["__main__"] = module

    old_argv = sys.argv
    sys.argv = [path, *argv]
    try:
        exec(compile(py, path, "exec", dont_inherit=True), module.__dict__)
    finally:
        sys.argv = old_argv
    return 0
