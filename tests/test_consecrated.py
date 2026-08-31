import pytest

from liturgy.compiler import compile_litany
from liturgy.constructs import TechHeresy


def run(src):
    ns = {}
    exec(compile_litany(src, "prayer.lit"), ns)
    return ns


def test_a_consecrated_binding_holds_its_value():
    assert run("consecrated PORT = 8080\n")["PORT"] == 8080


def test_the_annotation_carrier_does_not_survive_into_the_module():
    ns = run("consecrated PORT = 8080\n")
    assert "__consecrated__" not in ns
    assert ns.get("__annotations__", {}) == {}


def test_indentation_is_preserved():
    ns = run("rite f():\n    consecrated INNER = 1\n    render INNER\n")
    assert ns["f"]() == 1


@pytest.mark.parametrize(
    "rebinding",
    [
        "PORT = 9090",
        "PORT += 1",
        "PORT: int = 9090",
        "(PORT := 9090)",
        "foreach PORT among span(3):\n    abide",
        "anointed unseal('f') styled PORT:\n    abide",
        "purge PORT",
        "invoke os styled PORT",
        "PORT, other = 1, 2",
        "[PORT] = [1]",
        "consecrated PORT = 1",
    ],
)
def test_rebinding_a_consecrated_name_is_rejected(rebinding):
    src = f"consecrated PORT = 8080\n{rebinding}\n"
    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    assert "PORT" in str(exc.value)
    assert exc.value.filename == "prayer.lit"
    assert exc.value.lineno == 2


def test_consecrating_inside_a_loop_is_rejected():
    # Rebinds on every iteration while looking like a single declaration.
    src = "foreach i among span(3):\n    consecrated X = i\n"
    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    assert "loop" in str(exc.value)


def test_a_different_name_is_unaffected():
    ns = run("consecrated PORT = 8080\nOTHER = 1\nOTHER = 2\n")
    assert ns["OTHER"] == 2


def test_a_nested_scope_may_use_the_name_freely():
    # Shadowing in a function is a different binding, not a rebinding.
    src = "consecrated PORT = 8080\nrite f():\n    PORT = 1\n    render PORT\n"
    ns = run(src)
    assert ns["f"]() == 1 and ns["PORT"] == 8080


def test_rebinding_through_universal_is_rejected():
    src = (
        "consecrated PORT = 8080\n"
        "rite f():\n"
        "    universal PORT\n"
        "    PORT = 1\n"
    )
    with pytest.raises(TechHeresy):
        compile_litany(src, "prayer.lit")


def test_the_error_is_a_syntax_error_so_curses_render_it():
    with pytest.raises(SyntaxError):
        compile_litany("consecrated P = 1\nP = 2\n", "prayer.lit")
