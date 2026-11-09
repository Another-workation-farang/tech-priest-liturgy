import os
import pathlib
import re
import subprocess
import sys

import pytest

# The last three fault on a line `ast.stmt` alone would miss: decorator, `curse`, `wherein`.
OMENS = ("thread", "chain", "twin", "mantle", "oath", "verdict")

_HYMN = '''"""The entry litany: every shape an anointing must carry."""
within __future__ invoke annotations

invoke sys
invoke threading
invoke helper
within rites invoke divide
within pkg.cog invoke Cogitator
within reliquary.tally invoke tally
within sanctum.orison invoke orison
within helpers.util invoke whisper
within other.util invoke shout


rite fraught(fn: object) -> object:
    proclaim LostPattern("the mantle is refused")


rite main(omen: str) -> Void:
    intone(divide(6, 2), Cogitator("alpha").speak(), helper.double(4))
    intone(tally(), orison(), shout())
    should omen == "thread":
        t = threading.Thread(target=Cogitator("omega").fail)
        t.start()
        t.join()
    lest omen == "chain":
        attempt:
            divide(1, 0)
        curse DivisionByTheVoid styled e:
            proclaim MotiveFailure("the spirit is silent") within e
    lest omen == "sprawl":
        total = max(
            1,
            2 / 0,
        )
    lest omen == "twin":
        whisper()
    lest omen == "mantle":
        @fraught
        rite adorned() -> Void:
            intone("unreachable")
    lest omen == "oath":
        attempt:
            divide(1, 0)
        curse NoSuchCurse:
            intone("unreachable")
    lest omen == "verdict":
        discern omen:
            wherein NotAClass():
                intone("unreachable")


introit:
    main(sys.argv[1])
'''

_COG = '''pattern Cogitator:
    rite __init__(self, name: str) -> Void:
        self.name = name

    rite speak(self) -> str:
        render f"++ {self.name} speaks ++"

    rite fail(self) -> Void:
        proclaim ImpureOffering(f"{self.name} is corrupted")
'''

_FILES: dict[str, bytes] = {
    "hymn.lit": _HYMN.encode(),
    "rites.lit": b"\xef\xbb\xbf## \xe2\x9a\x99 the rite of division \xe2\x9a\x99\nrite divide(a: float, b: float) -> float:\n    render a / b  ## \xc3\xb7\n",
    "pkg/__init__.lit": b"VERSION: int = 1\n",
    "pkg/cog.lit": _COG.encode(),
    "reliquary/__init__.lit": b'SEAL: str = "reliquary"\n',
    "reliquary/tally.py": b"def tally():\n    return 3\n",
    "sanctum/__init__.py": b"",
    "sanctum/orison.lit": b'rite orison() -> str:\n    render "spoken in the sanctum"\n',
    "helpers/util.lit": b'rite whisper() -> Void:\n    proclaim LostPattern("the whisper is lost")\n',
    "other/util.lit": b'rite shout() -> str:\n    render "SHOUT"\n',
    "helper.py": b"def double(x):\n    return x * 2\n",
    "venv/pyvenv.cfg": b"",
    "venv/broken.lit": b"rite (:\n",
}


@pytest.fixture
def codex(tmp_path) -> pathlib.Path:
    root = tmp_path / "codex"
    for rel, data in _FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return root


def chant_run(root: pathlib.Path, omen: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "liturgy", "chant", "hymn.lit", omen],
        cwd=root, capture_output=True, text=True,
    )


def normalise(text: str, root: pathlib.Path) -> str:
    text = text.replace(f"{root}{os.sep}", "").replace(os.sep, "/")
    return "".join(
        l for l in text.splitlines(keepends=True) if not re.fullmatch(r"\s*\^+\s*", l.rstrip("\n"))
    )
