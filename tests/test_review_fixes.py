"""Regression tests for the 2026-08-31 review findings.

Each test class covers one numbered finding from the review; the docstrings
name the failure the fix exists to prevent.
"""

import os
import subprocess
import sys

import pytest

from liturgy.collisions import find_collisions
from liturgy.compiler import compile_litany
from liturgy.constructs import TechHeresy
from liturgy.tooling import augur, transcribe
from liturgy.transform import transform


def run_cli(args, cwd=None, stdin=None, **env):
    return subprocess.run(
        [sys.executable, "-m", "liturgy", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        input=stdin,
        env={**os.environ, **env},
    )


# -- 1: the machine's own names -----------------------------------------


class TestMachineNames:
    def test_user_written_litany_carrier_is_rejected_loudly(self):
        # Valid Python; silently hijacking it into a retry loop dropped the
        # `styled x` binding and never called the user's context manager.
        with pytest.raises(TechHeresy, match="__litany__"):
            compile_litany(
                "with __litany__(3, curse=ValueError) as x:\n    abide\n",
                "prayer.lit",
            )

    def test_user_written_consecrated_carrier_is_rejected_loudly(self):
        with pytest.raises(TechHeresy, match="__consecrated__"):
            compile_litany("x: __consecrated__ = 5\n", "prayer.lit")

    def test_user_written_augur_carrier_is_rejected_loudly(self):
        with pytest.raises(TechHeresy, match="__augur__"):
            compile_litany("anointed __augur__():\n    abide\n", "prayer.lit")

    def test_bookkeeping_prefix_is_rejected(self):
        with pytest.raises(TechHeresy, match="__liturgy_n_0"):
            compile_litany("__liturgy_n_0 = 1\n", "prayer.lit")

    def test_attribute_access_to_a_machine_name_is_left_alone(self):
        # Rule 1's reasoning: another module's attributes are its own.
        compile_litany("x = spirit.__litany__\n", "prayer.lit")

    def test_python_binding_a_machine_name_is_a_collision(self):
        found = find_collisions(
            "def __litany__(n):\n    return n\n", "mod.py", liturgy=False
        )
        assert [c.word for c in found] == ["__litany__"]
        assert found[0].target is None

    def test_transcribe_refuses_python_binding_a_machine_name(self, tmp_path, capsys):
        src = tmp_path / "mod.py"
        src.write_text("def __litany__(n):\n    return n\n")
        assert transcribe(str(src)) == 1
        assert "__litany__" in capsys.readouterr().out

    def test_transcribe_refuses_python_whose_litany_would_not_chant(
        self, tmp_path, capsys
    ):
        # `consecrated = 5` is valid Python with no Liturgy spelling: the
        # carrier pass rejects it. Writing it anyway would produce a file
        # that chant refuses.
        src = tmp_path / "mod.py"
        src.write_text("consecrated = 5\n")
        assert transcribe(str(src)) == 1
        assert "would not chant" in capsys.readouterr().out


# -- 2: archetype (type alias) is a binding ------------------------------


class TestTypeAliasBindings:
    def test_archetype_cannot_rebind_a_consecrated_name(self):
        with pytest.raises(TechHeresy, match="may not be rebound"):
            compile_litany(
                "consecrated PORT = 8080\narchetype PORT = int\n", "p.lit"
            )

    def test_archetype_binding_a_reserved_word_is_a_collision(self):
        found = find_collisions("archetype span = int\n", "p.lit", liturgy=True)
        assert [c.word for c in found] == ["span"]

    def test_python_type_alias_binding_a_reserved_word_is_a_collision(self):
        found = find_collisions("type span = int\n", "mod.py", liturgy=False)
        assert [c.word for c in found] == ["span"]


# -- 3: an augury holds conditions --------------------------------------


class TestAuguryConditions:
    def test_a_constant_is_not_a_condition(self):
        # A docstring in the block was silently a truthy "condition".
        with pytest.raises(TechHeresy, match="constant"):
            compile_litany(
                'rite f(x):\n    augur:\n        "x is positive"\n'
                "    render x\n",
                "p.lit",
            )

    def test_a_walrus_is_not_a_condition(self):
        with pytest.raises(TechHeresy, match="assignment"):
            compile_litany(
                "rite f(x):\n    augur:\n        (y := x)\n    render x\n",
                "p.lit",
            )

    def test_a_call_is_a_condition_judged_by_its_truth(self):
        code = compile_litany(
            "rite f(x):\n    augur:\n        isinstance(x, int)\n"
            "    render x\n"
            "y = f(3)\n",
            "p.lit",
        )
        ns = {}
        exec(code, ns)
        assert ns["y"] == 3


# -- 5: annotating a variable named litany or augur ----------------------


class TestConstructNamedAnnotations:
    def test_an_annotated_variable_named_litany_is_the_users(self):
        code = compile_litany("litany: int = 5\nx = litany\n", "p.lit")
        ns = {}
        exec(code, ns)
        assert ns["x"] == 5

    def test_a_bare_annotation_named_litany_is_the_users(self):
        compile_litany("litany: int\n", "p.lit")

    def test_an_annotated_variable_named_augur_is_the_users(self):
        code = compile_litany("augur: int = 5\nx = augur\n", "p.lit")
        ns = {}
        exec(code, ns)
        assert ns["x"] == 5

    def test_a_one_line_augury_is_rejected_not_silently_inert(self):
        # `augur: x > 0` parses as an annotation of a variable named augur;
        # it reads as a one-line augury, so it is rejected rather than left
        # to check nothing.
        with pytest.raises(TechHeresy, match="lines beneath"):
            compile_litany(
                "rite f(x):\n    augur: x > 0\n    render x\n", "p.lit"
            )

    def test_a_one_line_augury_mid_rite_is_rejected_too(self):
        with pytest.raises(TechHeresy, match="lines beneath"):
            compile_litany(
                "rite f(x):\n    y = x\n    augur: y > 0\n    render y\n",
                "p.lit",
            )

    def test_a_one_line_augury_after_a_real_augury_is_rejected(self):
        with pytest.raises(TechHeresy, match="lines beneath"):
            compile_litany(
                "rite f(x):\n    augur:\n        x > 0\n"
                "    augur: x < 100\n    render x\n",
                "p.lit",
            )

    def test_a_one_line_augury_at_module_level_is_rejected(self):
        with pytest.raises(TechHeresy, match="lines beneath"):
            compile_litany("x = 1\naugur: x > 0\n", "p.lit")

    def test_litany_without_parens_is_still_a_heresy(self):
        with pytest.raises(TechHeresy, match="parenthesised attempt count"):
            compile_litany("litany 3:\n    abide\n", "p.lit")

    def test_a_bare_litany_colon_keeps_its_targeted_heresy(self):
        with pytest.raises(TechHeresy, match="parenthesised attempt count"):
            compile_litany("litany:\n    abide\n", "p.lit")

    def test_augur_with_arguments_is_still_a_heresy(self):
        with pytest.raises(TechHeresy, match="takes no arguments"):
            compile_litany("augur x:\n    abide\n", "p.lit")


# -- 6: litany rejects ** expansion by name ------------------------------


class TestLitanyStarStar:
    def test_double_star_is_rejected_with_a_named_message(self):
        with pytest.raises(TechHeresy) as err:
            compile_litany(
                'litany(3, **{"curse": ValueError}):\n    abide\n', "p.lit"
            )
        assert "None" not in str(err.value)
        assert "**" in str(err.value)


# -- 7: resting is guarded like the count --------------------------------


class TestResting:
    def test_a_negative_literal_resting_is_rejected_at_compile_time(self):
        with pytest.raises(TechHeresy, match="negative"):
            compile_litany(
                "litany(3, resting=-1, curse=ValueError):\n    abide\n",
                "p.lit",
            )

    def test_a_negative_computed_resting_is_rejected_before_any_attempt(self):
        code = compile_litany(
            "r = -1\n"
            "seen = []\n"
            "attempt:\n"
            "    litany(3, resting=r, curse=MotiveFailure):\n"
            "        seen.append(1)\n"
            "        proclaim MotiveFailure()\n"
            "curse ImpureOffering styled omen:\n"
            "    caught = str(omen)\n",
            "p.lit",
        )
        ns = {}
        exec(code, ns)
        # The guard fires before the first attempt, so the body never ran
        # and the ValueError was not mistaken for the body's own failure.
        assert ns["seen"] == []
        assert "negative" in ns["caught"]

    def test_resting_is_evaluated_exactly_once(self):
        code = compile_litany(
            "calls = []\n"
            "rite pause():\n"
            "    calls.append(1)\n"
            "    render 0\n"
            "attempt:\n"
            "    litany(3, resting=pause(), curse=MotiveFailure):\n"
            "        proclaim MotiveFailure()\n"
            "curse MotiveFailure:\n"
            "    abide\n",
            "p.lit",
        )
        ns = {}
        exec(code, ns)
        assert ns["calls"] == [1]


# -- 8: a nested colon is not a statement boundary -----------------------


class TestNestedColon:
    def test_a_dict_colon_does_not_open_an_import_statement(self):
        # `invoke` after `{1:` used to set in_import, which suppressed the
        # substitution of every later word on the line.
        py = transform("x = {1: invoke, 2: measure}\n").python
        assert "len" in py

    def test_a_one_line_compound_import_still_translates(self):
        py = transform("should Sanctioned: invoke json\n").python
        assert py == "if True: import json\n"


# -- 10: the prompt quotes what was typed --------------------------------


class TestCommuneRendering:
    def test_a_syntax_error_at_the_prompt_quotes_the_liturgy(self):
        out = run_cli(["commune"], stdin="render 5\n")
        assert "render 5" in out.stderr
        assert "render is Liturgy for return" in out.stderr

    def test_a_runtime_error_at_the_prompt_is_a_machine_curse(self):
        out = run_cli(["commune"], stdin="1 / 0\n")
        assert "DivisionByTheVoid" in out.stderr
        assert "1 / 0" in out.stderr
        # The console plumbing above the entry is not the user's code.
        assert "code.py" not in out.stderr


# -- 11: the global flags work after the verb ----------------------------


class TestFlagPlacement:
    def test_profane_after_the_verb(self, tmp_path):
        bad = tmp_path / "bad.lit"
        bad.write_text("1 / 0\n")
        out = run_cli(["chant", "--profane", str(bad)])
        assert out.returncode == 1
        assert "Traceback" in out.stderr
        assert "MACHINE CURSE" not in out.stderr

    def test_absolved_after_the_verb(self, tmp_path):
        prayer = tmp_path / "p.lit"
        prayer.write_text("abide\n")
        out = run_cli(
            ["run", "--absolved", str(prayer)],
            XDG_STATE_HOME=str(tmp_path),
        )
        assert out.returncode == 0
        assert "TECH-HERESY" not in out.stderr

    def test_a_flag_before_the_verb_still_wins(self, tmp_path):
        bad = tmp_path / "bad.lit"
        bad.write_text("1 / 0\n")
        out = run_cli(["--profane", "chant", str(bad)])
        assert "Traceback" in out.stderr

    def test_arguments_after_the_file_still_reach_the_litany(self, tmp_path):
        prayer = tmp_path / "argv.lit"
        prayer.write_text("invoke sys\nintone(sys.argv[1])\n")
        out = run_cli(["chant", str(prayer), "--profane"])
        assert out.stdout.strip() == "--profane"


# -- 12: a substitution names itself in a syntax error -------------------


class TestNamedSubstitutions:
    def test_a_numeral_binding_names_the_numeral(self):
        with pytest.raises(SyntaxError, match="twice is Liturgy for 2"):
            compile_litany("twice = 1\n", "p.lit")

    def test_a_keyword_binding_names_the_keyword(self):
        with pytest.raises(SyntaxError, match="render is Liturgy for return"):
            compile_litany("render = 1\n", "p.lit")

    def test_augur_reports_the_named_message(self, tmp_path, capsys):
        prayer = tmp_path / "p.lit"
        prayer.write_text("twice = 1\n")
        assert augur([str(prayer)]) == 1
        assert "twice is Liturgy for 2" in capsys.readouterr().out


# -- 9 and 13: what augur walks ------------------------------------------


class TestAugurWalk:
    def test_hidden_directories_are_not_descended_into(self, tmp_path, capsys):
        (tmp_path / ".venv" / "lib").mkdir(parents=True)
        (tmp_path / ".venv" / "lib" / "third_party.py").write_text("span = 1\n")
        (tmp_path / "ok.lit").write_text("abide\n")
        assert augur([str(tmp_path)]) == 0
        assert "third_party" not in capsys.readouterr().out

    def test_virtual_environments_are_not_descended_into(self, tmp_path, capsys):
        venv = tmp_path / "venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("home = /usr\n")
        (venv / "third_party.py").write_text("span = 1\n")
        (tmp_path / "ok.lit").write_text("abide\n")
        assert augur([str(tmp_path)]) == 0
        assert "third_party" not in capsys.readouterr().out

    def test_a_directory_named_directly_is_always_read(self, tmp_path, capsys):
        hidden = tmp_path / ".venv"
        hidden.mkdir()
        (hidden / "shadow.py").write_text("span = 1\n")
        assert augur([str(hidden)]) == 1
        assert "span" in capsys.readouterr().out

    def test_a_symlinked_noise_directory_is_pruned_quietly(
        self, tmp_path, capsys
    ):
        real = tmp_path / ".cache" / "venvs" / "proj"
        real.mkdir(parents=True)
        (real / "third_party.py").write_text("span = 1\n")
        scanned = tmp_path / "proj"
        scanned.mkdir()
        (scanned / ".venv").symlink_to(real)
        (scanned / "ok.lit").write_text("abide\n")
        assert augur([str(scanned)]) == 0
        assert "symlinked" not in capsys.readouterr().out

    def test_a_hidden_source_file_is_named_not_silently_dropped(
        self, tmp_path, capsys
    ):
        (tmp_path / ".secret.lit").write_text('span = "x"\n')
        (tmp_path / "ok.lit").write_text("abide\n")
        assert augur([str(tmp_path)]) == 1
        out = capsys.readouterr().out
        assert "hidden: not read" in out
        assert "span is reserved" not in out

    def test_overlapping_arguments_report_each_finding_once(
        self, tmp_path, capsys
    ):
        prayer = tmp_path / "quiet.lit"
        prayer.write_text('span = "text range"\n')
        assert augur([str(prayer), str(prayer), str(tmp_path)], plain=True) == 1
        out = capsys.readouterr().out
        assert out.count("span is reserved") == 1


# -- 14: the heresy record survives a read failure ------------------------


class TestHeresyState:
    def test_an_unreadable_record_is_not_clobbered(self, tmp_path, monkeypatch):
        from pathlib import Path

        from liturgy import heresy

        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        path = heresy.state_path()
        path.parent.mkdir(parents=True)
        path.write_text('{"run": 5}')

        real_read = Path.read_text

        def refuse(self, *a, **kw):
            if self == path:
                raise OSError("transient")
            return real_read(self, *a, **kw)

        monkeypatch.setattr(Path, "read_text", refuse)
        heresy._bump("run")
        monkeypatch.undo()
        assert path.read_text() == '{"run": 5}'
