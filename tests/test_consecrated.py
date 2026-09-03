import pytest

from liturgy.compiler import compile_litany
from liturgy.constructs import TechHeresy


def run(src):
    ns = {}
    exec(compile_litany(src, "prayer.lit"), ns)
    return ns


def annotations_of(ns):
    """A module namespace's annotations, on both sides of PEP 649.

    From 3.14 a module's annotations are lazy: the namespace carries
    `__annotate__` and materialises `__annotations__` only when something
    asks, which an `exec` into a plain dict never does. Calling the
    annotate function with format 1 (VALUE) is that asking.
    """
    if "__annotations__" in ns:
        return ns["__annotations__"]
    annotate = ns.get("__annotate__")
    return annotate(1) if annotate is not None else {}


def test_a_consecrated_binding_holds_its_value():
    assert run("consecrated PORT: int = 8080\n")["PORT"] == 8080


def test_the_annotation_carrier_does_not_survive_into_the_module():
    ns = run("consecrated PORT: int = 8080\n")
    assert "__consecrated__" not in ns
    # The slot holds what the author declared and nothing of the machine's.
    # Asserting no annotation at all would pass on 3.14 for the wrong reason:
    # PEP 649 makes a module's annotations lazy, so a plain `exec` namespace
    # never materialises them and `{}` is what you see whatever is there.
    assert annotations_of(ns) == {"PORT": int}


def test_indentation_is_preserved():
    ns = run("rite f() -> int:\n    consecrated INNER: int = 1\n    render INNER\n")
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
    src = f"consecrated PORT: int = 8080\n{rebinding}\n"
    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    assert "PORT" in str(exc.value)
    assert exc.value.filename == "prayer.lit"
    assert exc.value.lineno == 2


def test_consecrating_inside_a_loop_is_rejected():
    # Rebinds on every iteration while looking like a single declaration.
    src = "foreach i among span(3):\n    consecrated X: int = i\n"
    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    assert "loop" in str(exc.value)


def test_a_different_name_is_unaffected():
    ns = run("consecrated PORT: int = 8080\nOTHER = 1\nOTHER = 2\n")
    assert ns["OTHER"] == 2


def test_a_nested_scope_may_use_the_name_freely():
    # Shadowing in a function is a different binding, not a rebinding.
    src = "consecrated PORT: int = 8080\nrite f() -> int:\n    PORT = 1\n    render PORT\n"
    ns = run(src)
    assert ns["f"]() == 1 and ns["PORT"] == 8080


def test_rebinding_through_universal_is_rejected():
    src = (
        "consecrated PORT: int = 8080\n"
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
    src = NESTED_BLOCKS[name].format(body=f"{indent}consecrated PORT: int = 8080\n")
    # Compiles, and nothing named __consecrated__ is left to evaluate.
    ns = {}
    exec(compile_litany(src, "prayer.lit"), ns)
    assert "__consecrated__" not in ns
    # Every block here is module-level, so whether the module carries the
    # annotation depends on whether the body ran -- `should Sanctioned:` runs
    # and a `curse` with nothing raised does not. Either is right; what must
    # never appear is anything of the machine's own.
    assert annotations_of(ns) in ({}, {"PORT": int})


@pytest.mark.parametrize("name", sorted(NESTED_BLOCKS))
def test_rebinding_is_rejected_inside_every_kind_of_block(name):
    indent = "        " if name == "wherein" else "    "
    body = f"{indent}consecrated PORT: int = 8080\n{indent}PORT = 9\n"
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
        "consecrated PORT: int = 8080\n"
        "rite outer() -> tuple:\n"
        "    PORT = 1\n"          # a legitimate local shadow
        "    rite deeper() -> int:\n"
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
        "rite outer() -> int:\n"
        "    consecrated PORT: int = 8080\n"
        "    rite inner() -> Void:\n"
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
        "    consecrated PORT: int = 8080\n"
        "    rite inner():\n"
        "        adjacent PORT\n"
        "        PORT = 1\n"
    )
    with pytest.raises(TechHeresy, match="may not be rebound"):
        compile_litany(src, "prayer.lit")


def test_universal_reaches_a_module_consecrated_from_any_depth():
    src = (
        "consecrated PORT: int = 8080\n"
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
        "rite outer() -> tuple:\n"
        "    consecrated PORT: int = 8080\n"
        "    rite mid() -> int:\n"
        "        PORT = 0\n"
        "        rite deep() -> Void:\n"
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
        "    consecrated PORT: int = 8080\n"
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
    ns = run("consecrated PORT: int = 8080\npattern C:\n    PORT = 1\n")
    assert ns["C"].PORT == 1 and ns["PORT"] == 8080


def test_a_class_body_declaring_universal_does_rebind():
    src = "consecrated PORT: int = 8080\npattern C:\n    universal PORT\n    PORT = 1\n"
    with pytest.raises(TechHeresy, match="may not be rebound"):
        compile_litany(src, "prayer.lit")


def test_nothing_nested_can_reach_a_consecrated_in_a_class_body():
    src = (
        "pattern C:\n"
        "    consecrated PORT: int = 8080\n"
        "    rite m(self) -> int:\n"
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
    src = f"consecrated PORT: int = 8080\n{rebinding}\n"
    with pytest.raises(TechHeresy) as exc:
        compile_litany(src, "prayer.lit")
    assert "may not be rebound" in str(exc.value)
    assert exc.value.lineno == line


def test_the_same_bindings_are_fine_in_a_nested_scope():
    # Each is a local binding of the nested rite, not a rebinding of ours.
    src = (
        "consecrated PORT: int = 8080\n"
        "rite f() -> Void:\n"
        "    attempt:\n"
        "        abide\n"
        "    curse MachineCurse styled PORT:\n"
        "        abide\n"
        "    rite PORT() -> Void:\n"
        "        abide\n"
        "    pattern PORT:\n"
        "        abide\n"
    )
    ns = run(src)
    ns["f"]()
    assert ns["PORT"] == 8080


# --- a versicle is a scope too ---------------------------------------------
#
# The sixth scope-flattening defect on this branch, and the same shape as I3:
# `_in_scope` stopped at `rite` and `pattern` but not at `versicle`, so a
# walrus inside a lambda -- which binds the lambda's own local -- was read as
# a rebinding of ours and a correct program was refused.


def test_a_walrus_inside_a_versicle_binds_there_not_here():
    src = (
        "consecrated PORT: int = 8080\n"
        "f = versicle: (PORT := 1)\n"
        "inner = f()\n"
    )
    ns = run(src)
    assert ns["inner"] == 1 and ns["PORT"] == 8080


def test_a_walrus_in_a_comprehension_still_binds_here():
    # PEP 572: a comprehension assigns a walrus to the CONTAINING scope, so
    # this one really is a rebinding and the versicle fix must not excuse it.
    src = "consecrated PORT: int = 8080\nxs = [(PORT := i) foreach i among span(3)]\n"
    with pytest.raises(TechHeresy, match="may not be rebound"):
        compile_litany(src, "prayer.lit")


def test_a_comprehension_target_is_its_own_binding():
    ns = run("consecrated PORT: int = 8080\nxs = [PORT foreach PORT among span(3)]\n")
    assert ns["xs"] == [0, 1, 2] and ns["PORT"] == 8080


def test_a_walrus_at_our_own_scope_is_still_a_rebinding():
    with pytest.raises(TechHeresy, match="may not be rebound"):
        compile_litany("consecrated PORT: int = 8080\n(PORT := 1)\n", "prayer.lit")


# --- Spec IV: a consecrated name may declare its archetype ------------------
#
# The construct used to reach the AST through the annotation slot, so the
# slot was never the author's to spend: `consecrated PORT: int = 8080` was
# `SyntaxError: invalid syntax (PORT is Liturgy for PORT: __consecrated__)`.
# Consecration travels beside the source now, in `ConstructFacts`, and the
# annotation means what it means in Python.


def test_a_consecrated_name_may_declare_its_archetype():
    assert run("consecrated PORT: int = 8080\n")["PORT"] == 8080


def test_the_declared_archetype_reaches_the_module():
    assert annotations_of(run("consecrated PORT: int = 8080\n")) == {"PORT": int}


def test_a_subscripted_archetype_is_carried_whole():
    ns = run("consecrated TABLE: dict[str, int] = {'a': 1}\n")
    assert ns["TABLE"] == {"a": 1}
    assert annotations_of(ns) == {"TABLE": dict[str, int]}


def test_an_archetype_may_be_declared_inside_a_rite():
    ns = run("rite f() -> int:\n    consecrated INNER: int = 1\n    render INNER\n")
    assert ns["f"]() == 1


def test_an_annotated_consecrated_name_still_refuses_a_rebinding():
    with pytest.raises(TechHeresy, match="may not be rebound"):
        compile_litany("consecrated PORT: int = 8080\nPORT = 9\n", "prayer.lit")


def test_an_annotated_name_may_not_be_consecrated_twice():
    src = "consecrated P: int = 1\nconsecrated P: int = 2\n"
    with pytest.raises(TechHeresy, match="already consecrated"):
        compile_litany(src, "prayer.lit")


def test_an_annotated_consecration_inside_a_loop_is_still_rejected():
    src = "foreach i among span(3):\n    consecrated X: int = i\n"
    with pytest.raises(TechHeresy, match="loop"):
        compile_litany(src, "prayer.lit")


# --- one row, two meanings --------------------------------------------------
#
# A consecration is recorded by row, column and name. The column is the part
# that earns its keep: these two rows are indistinguishable by row and name.


def test_a_declaration_and_a_rebinding_on_one_row_are_told_apart():
    with pytest.raises(TechHeresy, match="may not be rebound"):
        compile_litany("consecrated PORT: int = 8080; PORT = 9\n", "prayer.lit")


def test_two_declarations_on_one_row_both_hold():
    ns = run("consecrated A: int = 1; consecrated B: int = 2\nA_ = A; B_ = B\n")
    assert (ns["A_"], ns["B_"]) == (1, 2)


def test_two_declarations_of_one_name_on_one_row_are_still_a_repeat():
    with pytest.raises(TechHeresy, match="already consecrated"):
        compile_litany("consecrated A = 1; consecrated A = 2\n", "prayer.lit")


# --- headers that bind no single name ---------------------------------------
#
# While consecration travelled through the annotation slot, every shape below
# generated Python that would not parse -- `A: __consecrated__, B = 1, 2` and
# the like -- so the parser refused them for free. The generated Python is now
# the author's own minus one word, and all of these are perfectly valid
# Python: without an explicit check the author would be left holding a name
# they believe is sealed and is not.


@pytest.mark.parametrize(
    "header",
    [
        "consecrated PORT",
        "consecrated PORT: int",
        "consecrated PORT += 1",
        "consecrated PORT, OTHER = 1, 2",
        "consecrated PORT = OTHER = 1",
        "consecrated cfg.PORT = 1",
        "consecrated cfg[0] = 1",
    ],
)
def test_a_header_that_binds_no_single_name_is_rejected(header):
    with pytest.raises(TechHeresy, match="not bound to a single value") as exc:
        compile_litany(header + "\n", "prayer.lit")
    assert exc.value.lineno == 1
    # Where the caret lands is asserted end-to-end in `test_curse.py`: the
    # offset here is a generated-Python column and only the renderer, which
    # maps it back through the SourceMap, can be held to the Liturgy one.
