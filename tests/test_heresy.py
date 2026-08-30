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
