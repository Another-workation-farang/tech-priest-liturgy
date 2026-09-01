"""Cross-file enforcement of `consecrated`.

The construct enforces per compilation unit. These are the rebindings that
reach a consecrated name from outside the file that sealed it, which the
compiler by construction cannot see.
"""

from __future__ import annotations

import pytest

from liturgy.seals import find_breaches, find_seals


def seals_of(src, filename="config.lit", *, liturgy=True):
    return find_seals(src, filename, liturgy=liturgy)


def breaches_of(src, sealed, filename="server.lit", *, liturgy=True):
    return find_breaches(src, filename, sealed, liturgy=liturgy)


# --- what counts as a seal -------------------------------------------------


def test_a_module_level_consecrated_is_a_seal():
    seals = seals_of("consecrated PORT = 8080\n")
    assert [(s.name, s.module, s.line) for s in seals] == [("PORT", "config", 1)]


def test_the_column_points_at_the_name_not_the_keyword():
    # `consecrated PORT` -- the caret must land on PORT, at column 12.
    (seal,) = seals_of("consecrated PORT = 8080\n")
    assert seal.col == 12


def test_several_seals_in_one_file_are_all_found():
    src = "consecrated PORT = 8080\nconsecrated HOST = 'forge'\n"
    assert {s.name for s in seals_of(src)} == {"PORT", "HOST"}


def test_a_consecrated_inside_a_rite_is_not_a_seal():
    # Only module-level names are reachable as `module.NAME`, so only they
    # can be breached from another file.
    src = "rite f():\n    consecrated LOCAL = 1\n    render LOCAL\n"
    assert seals_of(src) == []


def test_an_ordinary_binding_is_not_a_seal():
    assert seals_of("PORT = 8080\n") == []


def test_a_python_file_has_no_seals():
    # consecrated is Liturgy-only; a .py file cannot declare one.
    assert seals_of("PORT = 8080\n", "plain.py", liturgy=False) == []


# --- what counts as a breach -----------------------------------------------


SEALED = {"config": {"PORT"}}


def test_assignment_through_the_module_object_is_a_breach():
    src = "invoke config\nconfig.PORT = 9\n"
    (b,) = breaches_of(src, SEALED)
    assert (b.name, b.module, b.line, b.how) == ("PORT", "config", 2, "assigned")


def test_the_breach_column_points_at_the_name():
    src = "invoke config\nconfig.PORT = 9\n"
    (b,) = breaches_of(src, SEALED)
    # `config.PORT` -- PORT begins at column 7.
    assert b.col == 7


def test_an_aliased_import_is_followed():
    src = "invoke config styled cfg\ncfg.PORT = 9\n"
    (b,) = breaches_of(src, SEALED)
    assert b.name == "PORT"


def test_a_from_import_of_the_module_is_followed():
    src = "within pkg invoke config\nconfig.PORT = 9\n"
    (b,) = breaches_of(src, SEALED)
    assert b.name == "PORT"


def test_augmented_assignment_is_a_breach():
    src = "invoke config\nconfig.PORT += 1\n"
    (b,) = breaches_of(src, SEALED)
    assert b.how == "assigned"


def test_setattr_on_the_module_is_a_breach():
    # The docs name setattr as something the construct cannot stop. Here it
    # is stoppable, because the name is a literal the walk can read.
    src = 'invoke config\nsetattr(config, "PORT", 9)\n'
    (b,) = breaches_of(src, SEALED)
    assert b.how == "setattr"


def test_deleting_through_the_module_object_is_a_breach():
    src = "invoke config\npurge config.PORT\n"
    (b,) = breaches_of(src, SEALED)
    assert b.how == "deleted"


def test_a_python_file_may_breach_a_liturgy_seal():
    # .py imports .lit through the hook like anything else.
    src = "import config\nconfig.PORT = 9\n"
    (b,) = breaches_of(src, SEALED, "plain.py", liturgy=False)
    assert b.name == "PORT"


# --- what must NOT count ---------------------------------------------------


def test_reading_the_name_is_not_a_breach():
    src = "invoke config\nintone(config.PORT)\n"
    assert breaches_of(src, SEALED) == []


def test_an_unconsecrated_attribute_is_not_a_breach():
    src = "invoke config\nconfig.TIMEOUT = 5\n"
    assert breaches_of(src, SEALED) == []


def test_a_different_module_with_the_same_attribute_is_not_a_breach():
    src = "invoke other\nother.PORT = 9\n"
    assert breaches_of(src, SEALED) == []


def test_an_unimported_name_is_not_a_breach():
    # `config` here is a local dict, not the module.
    src = 'config = {}\nconfig.PORT = 9\n'
    assert breaches_of(src, SEALED) == []


def test_a_local_binding_of_the_imported_name_is_not_a_breach():
    # `within config invoke PORT` binds a local PORT; rebinding that local
    # does not touch config's own attribute.
    src = "within config invoke PORT\nPORT = 9\n"
    assert breaches_of(src, SEALED) == []


def test_setattr_with_a_computed_name_is_not_reported():
    # The walk reads literal names only. A computed one is genuinely
    # invisible and must not be guessed at.
    src = "invoke config\nsetattr(config, name, 9)\n"
    assert breaches_of(src, SEALED) == []


def test_the_sealing_file_rebinding_its_own_name_is_left_to_the_compiler():
    # `consecrated PORT = 8080` then `PORT = 9` in one file is already a
    # compile-time heresy. Reporting it here too would double up.
    src = "invoke config\nPORT = 9\n"
    assert breaches_of(src, SEALED) == []


# --- errors ----------------------------------------------------------------


def test_a_file_that_does_not_parse_raises():
    with pytest.raises(SyntaxError):
        seals_of("rite (:\n")
