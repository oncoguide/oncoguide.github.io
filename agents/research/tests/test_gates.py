"""Tests for pipeline gate functions."""

from run_research import _gate_0, _gate_1, _gate_2, _gate_3


def test_gate_0_passes():
    ok, _ = _gate_0(25)
    assert ok is True


def test_gate_0_fails():
    ok, reason = _gate_0(10)
    assert ok is False
    assert "10" in reason


def test_gate_1_passes():
    km = {
        "Q2_treatment": {"approved_drugs": [{"name": "selpercatinib"}]},
        "Q5_resistance": {"mechanisms": [{"name": "G810R"}]},
        "Q6_pipeline": {"drugs": [{"name": "EP0031"}]},
    }
    ok, _ = _gate_1(km)
    assert ok is True


def test_gate_1_no_drugs():
    km = {
        "Q2_treatment": {"approved_drugs": []},
        "Q5_resistance": {"mechanisms": [{"name": "G810R"}]},
        "Q6_pipeline": {"drugs": [{"name": "EP0031"}]},
    }
    ok, reason = _gate_1(km)
    assert ok is False
    assert "Q2" in reason


def test_gate_2_passes():
    queries = [{"lifecycle_stage": "Q2"} for _ in range(100)]
    ok, _ = _gate_2(queries)
    assert ok is True


def test_gate_2_too_few():
    queries = [{"lifecycle_stage": "Q2"} for _ in range(50)]
    ok, reason = _gate_2(queries)
    assert ok is False
    assert "50" in reason


def test_gate_3_passes():
    ok, _ = _gate_3(150)
    assert ok is True


def test_gate_3_hard_stop():
    ok, reason = _gate_3(15)
    assert ok is False
    assert "15" in reason


def test_gate_3_warning():
    """< 100 findings passes with a warning reason."""
    ok, reason = _gate_3(60)
    assert ok is True
    assert "60" in reason  # warning message present
