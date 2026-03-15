import pytest
from modules.cost_tracker import CostTracker


def test_initial_state():
    ct = CostTracker(max_cost_usd=5.0)
    assert ct.total_cost_usd == 0.0
    assert ct.total_input_tokens == 0
    assert ct.total_output_tokens == 0


def test_track_sonnet_call():
    ct = CostTracker(max_cost_usd=5.0)
    ct.track("claude-sonnet-4-6", input_tokens=2000, output_tokens=4000)
    assert ct.total_input_tokens == 2000
    assert ct.total_output_tokens == 4000
    assert ct.total_cost_usd > 0


def test_track_haiku_call():
    ct = CostTracker(max_cost_usd=5.0)
    ct.track("claude-haiku-4-5-20251001", input_tokens=10000, output_tokens=5000)
    assert ct.total_cost_usd > 0
    # Haiku should be much cheaper than Sonnet
    cost_haiku = ct.total_cost_usd
    ct2 = CostTracker(max_cost_usd=5.0)
    ct2.track("claude-sonnet-4-6", input_tokens=10000, output_tokens=5000)
    assert cost_haiku < ct2.total_cost_usd


def test_budget_exceeded_raises():
    ct = CostTracker(max_cost_usd=0.001)  # tiny budget
    with pytest.raises(RuntimeError, match="Budget exceeded"):
        ct.track("claude-sonnet-4-6", input_tokens=100000, output_tokens=50000)


def test_budget_check():
    ct = CostTracker(max_cost_usd=5.0)
    assert ct.has_budget()
    ct.track("claude-sonnet-4-6", input_tokens=1000, output_tokens=500)
    assert ct.has_budget()


def test_report():
    ct = CostTracker(max_cost_usd=5.0)
    ct.track("claude-sonnet-4-6", input_tokens=2000, output_tokens=1000)
    ct.track("claude-haiku-4-5-20251001", input_tokens=5000, output_tokens=2000)
    report = ct.report()
    assert "sonnet" in report.lower() and "haiku" in report.lower()
    assert "$" in report
