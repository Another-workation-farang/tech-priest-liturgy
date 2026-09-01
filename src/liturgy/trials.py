"""The pytest plugin behind `prove`.

Kept in its own module so nothing imports pytest unless `prove` is the verb
being run. pytest is an optional extra (`liturgy[trials]`), and the rest of
the language must not acquire a test-framework dependency by accident.
"""

from __future__ import annotations

import pathlib


class LitanyTrials:
    """Collects `test_*.lit` the way pytest collects `test_*.py`.

    Passed to `pytest.main(plugins=[...])` rather than written into a
    `conftest.py`, which is the boilerplate this verb exists to remove.
    """

    def pytest_collect_file(self, parent, file_path: pathlib.Path):
        import pytest

        if file_path.suffix == ".lit" and file_path.name.startswith("test_"):
            return pytest.Module.from_parent(parent, path=file_path)
        return None
