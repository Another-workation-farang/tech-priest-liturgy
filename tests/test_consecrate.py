"""The consecrate verb: seals checked across the whole tree."""

from __future__ import annotations

import io

from liturgy.tooling import consecrate


def forge_tree(tmp_path, **files):
    for name, body in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    return tmp_path


def run(root, **kw):
    buf = io.StringIO()
    code = consecrate([str(root)], out=buf, **kw)
    return code, buf.getvalue()


def test_a_held_seal_is_reported_as_held(tmp_path):
    forge_tree(tmp_path, **{
        "config.lit": "consecrated PORT = 8080\n",
        "server.lit": "invoke config\nintone(config.PORT)\n",
    })
    code, out = run(tmp_path)
    assert code == 0
    assert "0 seals broken, 1 held" in out


def test_a_rebinding_from_another_litany_breaks_the_seal(tmp_path):
    forge_tree(tmp_path, **{
        "config.lit": "consecrated PORT = 8080\n",
        "server.lit": "invoke config\nconfig.PORT = 9\n",
    })
    code, out = run(tmp_path)
    assert code == 1
    assert "THE SEAL IS BROKEN" in out
    assert "config.lit, line 1" in out
    assert "assigned" in out and "server.lit:2" in out
    assert "1 seal broken, 0 held" in out


def test_the_caret_points_at_the_consecrated_name(tmp_path):
    forge_tree(tmp_path, **{
        "config.lit": "consecrated PORT = 8080\n",
        "server.lit": "invoke config\nconfig.PORT = 9\n",
    })
    _, out = run(tmp_path)
    # `consecrated PORT` -- four carets under PORT, at column 12.
    assert "\n       consecrated PORT = 8080\n" in out
    assert "\n                   ^^^^\n" in out


def test_a_python_file_can_break_a_seal(tmp_path):
    forge_tree(tmp_path, **{
        "config.lit": 'consecrated HOST = "mars"\n',
        "tamper.py": 'import config\nsetattr(config, "HOST", "terra")\n',
    })
    code, out = run(tmp_path)
    assert code == 1
    assert "setattr" in out and "tamper.py:2" in out


def test_several_breaches_of_one_seal_are_grouped(tmp_path):
    forge_tree(tmp_path, **{
        "config.lit": "consecrated PORT = 8080\n",
        "a.lit": "invoke config\nconfig.PORT = 1\n",
        "b.lit": "invoke config\nconfig.PORT = 2\n",
    })
    code, out = run(tmp_path)
    assert code == 1
    assert out.count("THE SEAL IS BROKEN") == 1, "one seal, one heading"
    assert "a.lit:2" in out and "b.lit:2" in out
    assert "1 seal broken" in out


def test_a_tree_with_no_consecrated_names_says_so(tmp_path):
    forge_tree(tmp_path, **{"x.lit": "intone(1)\n"})
    code, out = run(tmp_path)
    assert code == 0
    assert "no consecrated names found" in out


def test_plain_emits_machine_lines_and_no_summary(tmp_path):
    forge_tree(tmp_path, **{
        "config.lit": "consecrated PORT = 8080\n",
        "server.lit": "invoke config\nconfig.PORT = 9\n",
    })
    code, out = run(tmp_path, plain=True)
    assert code == 1
    assert "server.lit:2:8:" in out
    assert "++" not in out, "--plain is for editors; nothing to parse around"


def test_a_broken_litany_is_reported_and_does_not_stop_the_walk(tmp_path):
    forge_tree(tmp_path, **{
        # A genuine parse failure. Note `render 1` at module level would
        # NOT do: ast.parse accepts it and only compile() rejects it, and
        # compiling is augur's job, not this verb's.
        "aaa.lit": "rite (:\n",
        "config.lit": "consecrated PORT = 8080\n",
        "server.lit": "invoke config\nconfig.PORT = 9\n",
    })
    code, out = run(tmp_path)
    assert code == 1
    assert "aaa.lit" in out
    assert "THE SEAL IS BROKEN" in out, "one bad file ended the walk"


def test_two_litanies_sharing_a_basename_are_called_out(tmp_path):
    # The walk resolves `module.NAME` by basename, so two `config.lit` make
    # the answer ambiguous. Saying so beats reporting confidently.
    forge_tree(tmp_path, **{
        "one/config.lit": "consecrated PORT = 8080\n",
        "two/config.lit": "consecrated PORT = 9090\n",
    })
    code, out = run(tmp_path)
    assert "matched by basename" in out
    assert "one/config.lit" in out and "two/config.lit" in out


def test_a_consecrated_inside_a_rite_is_not_counted(tmp_path):
    forge_tree(tmp_path, **{
        "config.lit": "rite f():\n    consecrated LOCAL = 1\n    render LOCAL\n",
    })
    code, out = run(tmp_path)
    assert code == 0
    assert "no consecrated names found" in out


def test_an_unreadable_file_is_reported_not_raised(tmp_path):
    (tmp_path / "gone.lit").symlink_to(tmp_path / "nowhere.lit")
    code, out = run(tmp_path)
    assert code == 1
    assert "CANNOT CONSECRATE" in out


def test_a_seal_on_an_annotated_name_is_still_checked(tmp_path):
    # Spec IV: `consecrated PORT: int = 8080` is a seal like any other, and
    # the caret still lands on the name.
    forge_tree(tmp_path, **{
        "config.lit": "consecrated PORT: int = 8080\n",
        "server.lit": "invoke config\nconfig.PORT = 9\n",
    })
    code, out = run(tmp_path)
    assert code == 1
    assert "THE SEAL IS BROKEN" in out
    assert "\n       consecrated PORT: int = 8080\n" in out
    assert "\n                   ^^^^\n" in out
