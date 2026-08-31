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


# --- C1: blocks whose statement list is not a direct field of a statement ---
#
# `_collect_consecrated` used to recurse only into fields that were a list
# whose first element was an `ast.stmt`. `Try.handlers` holds `ExceptHandler`
# and `Match.cases` holds `match_case` -- neither is a statement -- so both
# subtrees were skipped entirely: the carrier survived into the compiled
# tree, enforcement was silently off, and on Python 3.12/3.13 the eagerly
# evaluated module-scope annotation killed the module with
# `NameError: __consecrated__`.

NESTED_BLOCKS = {
    "curse": "attempt:\n    abide\ncurse MachineCurse:\n{body}",
    "curse-styled": (
        "attempt:\n    abide\ncurse MachineCurse styled e:\n{body}"
    ),
    "regardless": "attempt:\n    abide\nregardless:\n{body}",
    "otherwise-of-attempt": (
        "attempt:\n    abide\ncurse MachineCurse:\n    abide\notherwise:\n{body}"
    ),
    "wherein": "discern 1:\n    wherein 1:\n{body}",
    "should": "should Sanctioned:\n{body}",
    "anointed": "anointed unseal('/dev/null') styled fh:\n{body}",
}


@pytest.mark.parametrize("name", sorted(NESTED_BLOCKS))
def test_consecrated_is_desugared_inside_every_kind_of_block(name):
    indent = "        " if name == "wherein" else "    "
    src = NESTED_BLOCKS[name].format(body=f"{indent}consecrated PORT = 8080\n")
    # Compiles, and nothing named __consecrated__ is left to evaluate.
    ns = {}
    exec(compile_litany(src, "prayer.lit"), ns)
    assert "__consecrated__" not in ns
    assert ns.get("__annotations__", {}) == {}


@pytest.mark.parametrize("name", sorted(NESTED_BLOCKS))
def test_rebinding_is_rejected_inside_every_kind_of_block(name):
    indent = "        " if name == "wherein" else "    "
    body = f"{indent}consecrated PORT = 8080\n{indent}PORT = 9\n"
    with pytest.raises(TechHeresy, match="may not be rebound"):
        compile_litany(NESTED_BLOCKS[name].format(body=body), "prayer.lit")


# --- I3: `universal` and `adjacent` are not the same reach ------------------
#
# `_check_nested` used `ast.walk`, which harvested every `universal` and
# `adjacent` in every descendant scope and then rejected any store anywhere
# in the outer one. Both cases below are correct programs it refused to
# compile, and neither could be worked around.


def test_a_local_shadow_survives_a_universal_read_in_a_deeper_rite():
    src = (
        "consecrated PORT = 8080\n"
        "rite outer():\n"
        "    PORT = 1\n"          # a legitimate local shadow
        "    rite deeper():\n"
        "        universal PORT\n"  # only READS the module binding
        "        render PORT\n"
        "    render (PORT, deeper())\n"
    )
    ns = run(src)
    assert ns["outer"]() == (1, 8080)


def test_universal_does_not_reach_a_consecrated_in_a_rite():
    # `universal PORT` in `inner` names the MODULE's PORT. `outer`'s
    # consecrated PORT is a different binding entirely and is untouched.
    src = (
        "rite outer():\n"
        "    consecrated PORT = 8080\n"
        "    rite inner():\n"
        "        universal PORT\n"
        "        PORT = 1\n"
        "    inner()\n"
        "    render PORT\n"
    )
    ns = run(src)
    assert ns["outer"]() == 8080 and ns["PORT"] == 1


def test_adjacent_does_reach_a_consecrated_in_a_rite():
    src = (
        "rite outer():\n"
        "    consecrated PORT = 8080\n"
        "    rite inner():\n"
        "        adjacent PORT\n"
        "        PORT = 1\n"
    )
    with pytest.raises(TechHeresy, match="may not be rebound"):
        compile_litany(src, "prayer.lit")


def test_universal_reaches_a_module_consecrated_from_any_depth():
    src = (
        "consecrated PORT = 8080\n"
        "rite outer():\n"
        "    rite deeper():\n"
        "        universal PORT\n"
        "        PORT = 1\n"
    )
    with pytest.raises(TechHeresy, match="may not be rebound"):
        compile_litany(src, "prayer.lit")


def test_a_rite_that_binds_the_name_locally_shields_deeper_adjacents():
    # `adjacent PORT` in `deep` binds to `mid`, the nearest enclosing rite
    # that holds PORT as a local -- not to `outer`'s consecrated one.
    src = (
        "rite outer():\n"
        "    consecrated PORT = 8080\n"
        "    rite mid():\n"
        "        PORT = 0\n"
        "        rite deep():\n"
        "            adjacent PORT\n"
        "            PORT = 1\n"
        "        deep()\n"
        "        render PORT\n"
        "    render (mid(), PORT)\n"
    )
    assert run(src)["outer"]() == (1, 8080)


def test_a_rite_that_only_declares_the_name_shields_nothing():
    # `adjacent PORT` in `mid` makes PORT free there, not local, so `deep`'s
    # own `adjacent PORT` resolves straight past `mid` to `outer`.
    src = (
        "rite outer():\n"
        "    consecrated PORT = 8080\n"
        "    rite mid():\n"
        "        adjacent PORT\n"
        "        rite deep():\n"
        "            adjacent PORT\n"
        "            PORT = 1\n"
    )
    with pytest.raises(TechHeresy, match="may not be rebound"):
        compile_litany(src, "prayer.lit")


def test_a_class_body_may_name_a_consecrated_freely():
    # A class attribute is its own binding; no closure reaches it either.
    ns = run("consecrated PORT = 8080\npattern C:\n    PORT = 1\n")
    assert ns["C"].PORT == 1 and ns["PORT"] == 8080


def test_a_class_body_declaring_universal_does_rebind():
    src = "consecrated PORT = 8080\npattern C:\n    universal PORT\n    PORT = 1\n"
    with pytest.raises(TechHeresy, match="may not be rebound"):
        compile_litany(src, "prayer.lit")


def test_nothing_nested_can_reach_a_consecrated_in_a_class_body():
    src = (
        "pattern C:\n"
        "    consecrated PORT = 8080\n"
        "    rite m(self):\n"
        "        PORT = 1\n"
        "        render PORT\n"
    )
    ns = run(src)
    assert ns["C"].PORT == 8080 and ns["C"].m(None) == 1


# --- M9: three bindings that used to slip through --------------------------


@pytest.mark.parametrize(
    "rebinding,line",
    [
        ("attempt:\n    abide\ncurse MachineCurse styled PORT:\n    abide", 4),
        ("discern 1:\n    wherein PORT:\n        abide", 3),
        ("discern 1:\n    wherein 1 styled PORT:\n        abide", 3),
        ("discern [1]:\n    wherein [head, *PORT]:\n        abide", 3),
        ("discern {}:\n    wherein {**PORT}:\n        abide", 3),
        ("rite PORT():\n    abide", 2),
        ("pattern PORT:\n    abide", 2),
        ("remote rite PORT():\n    abide", 2),
    ],
    ids=[
        "except-as", "match-capture", "match-as", "match-star",
        "match-mapping-rest", "rite-name", "pattern-name", "async-rite-name",
    ],
)
def test_these_bindings_are_rebindings_too(rebinding, line):
    src = f"consecrated PORT = 8080\n{rebinding}\n"
    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    assert "may not be rebound" in str(exc.value)
    assert exc.value.lineno == line


def test_the_same_bindings_are_fine_in_a_nested_scope():
    # Each is a local binding of the nested rite, not a rebinding of ours.
    src = (
        "consecrated PORT = 8080\n"
        "rite f():\n"
        "    attempt:\n"
        "        abide\n"
        "    curse MachineCurse styled PORT:\n"
        "        abide\n"
        "    rite PORT():\n"
        "        abide\n"
        "    pattern PORT:\n"
        "        abide\n"
    )
    ns = run(src)
    ns["f"]()
    assert ns["PORT"] == 8080
