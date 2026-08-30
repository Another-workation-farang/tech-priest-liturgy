import io

import pytest

from liturgy import heresy


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.delenv("LITURGY_PIOUS", raising=False)


def emit():
    buf = io.StringIO()
    heresy.rebuke("run", "chant", stream=buf)
    return buf.getvalue()


def test_first_offence_is_noted():
    out = emit()
    assert "TECH-HERESY DETECTED" in out
    assert "CHANT" in out
    assert "noted" in out


def test_second_offence_escalates():
    emit()
    assert "permanent record" in emit()


def test_third_offence_summons_the_inquisition():
    emit()
    emit()
    assert "Inquisition" in emit()


def test_escalation_saturates_at_the_last_rebuke():
    for _ in range(5):
        out = emit()
    assert "Inquisition" in out


def test_pious_zero_silences_everything(monkeypatch):
    monkeypatch.setenv("LITURGY_PIOUS", "0")
    assert emit() == ""


def test_unwritable_state_file_does_not_raise(monkeypatch):
    monkeypatch.setattr(
        heresy, "state_path", lambda: (_ for _ in ()).throw(OSError())
    )
    assert "TECH-HERESY DETECTED" in emit()


@pytest.mark.parametrize(
    "corrupted_state",
    [
        '{"run": "not-a-number"}',  # value not coercible to int
        '{"run": null}',  # null value
        "[1,2,3]",  # JSON array instead of object
        '"hello"',  # JSON string instead of object
    ],
)
def test_corrupted_state_file_still_rebukes(tmp_path, corrupted_state):
    """Verify that partially-corrupted state (from concurrent writes or manual
    edits) does not crash _bump(); the rebuke still emits and the count resets."""
    state_file = tmp_path / "liturgy" / "heresies.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(corrupted_state)

    out = emit()
    assert "TECH-HERESY DETECTED" in out
    assert "noted" in out
