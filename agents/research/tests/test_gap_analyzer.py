import pytest
from unittest.mock import patch, MagicMock, Mock

from modules.gap_analyzer import analyze_gaps, LIFECYCLE_THRESHOLDS


def _mock_tool_use(input_dict):
    mock_tool = Mock()
    mock_tool.type = "tool_use"
    mock_tool.input = input_dict
    mock_msg = Mock()
    mock_msg.content = [mock_tool]
    mock_msg.usage = Mock(input_tokens=50, output_tokens=20)
    return mock_msg


SAMPLE_SECTIONS = [
    {"id": "best-treatment", "title": "Treatment", "description": "Drug response rates"},
    {"id": "side-effects", "title": "Side Effects", "description": "Adverse events with frequencies"},
    {"id": "resistance", "title": "Resistance", "description": "Resistance mechanisms"},
]


def _make_findings(stage_counts: dict) -> list[dict]:
    """Create findings with lifecycle_stage tags."""
    findings = []
    for stage, count in stage_counts.items():
        for i in range(count):
            findings.append({
                "title_english": f"Finding {stage}-{i}",
                "relevance_score": 8,  # above threshold (7)
                "lifecycle_stage": stage,
            })
    return findings


@patch("modules.gap_analyzer.anthropic.Anthropic")
def test_gap_analysis_detects_weak_stages(mock_cls):
    """Gap analysis should detect stages below threshold and generate queries."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    # Only one API call now (gap query generation) -- no section mapping needed
    mock_client.messages.create.return_value = _mock_tool_use({
        "queries": [
            {"query_text": "RET resistance G810R", "search_engine": "pubmed", "lifecycle_stage": "Q5"},
            {"query_text": "RET fusion mistakes interactions", "search_engine": "serper", "lifecycle_stage": "Q7"},
        ]
    })

    # Q2 has plenty, but Q5 and Q7 are below threshold
    findings = _make_findings({"Q2": 20, "Q3": 25, "Q5": 3, "Q7": 1})
    result = analyze_gaps("RET fusion NSCLC", findings, SAMPLE_SECTIONS, "fake-key")

    assert len(result) == 2
    stages = {q["lifecycle_stage"] for q in result}
    assert "Q5" in stages
    assert "Q7" in stages


@patch("modules.gap_analyzer.anthropic.Anthropic")
def test_gap_analysis_empty_when_all_covered(mock_cls):
    """analyze_gaps returns empty when all lifecycle stages are covered."""
    # Create findings that satisfy ALL thresholds
    findings = _make_findings({
        "Q1": 10, "Q2": 20, "Q3": 25, "Q4": 10,
        "Q5": 15, "Q6": 12, "Q7": 8, "Q8": 5,
    })
    result = analyze_gaps("RET fusion NSCLC", findings, SAMPLE_SECTIONS, "fake-key")
    assert result == []


def test_analyze_gaps_no_api_key():
    result = analyze_gaps("topic", _make_findings({"Q2": 5}), SAMPLE_SECTIONS, api_key="")
    assert result == []


def test_analyze_gaps_no_findings():
    result = analyze_gaps("topic", [], SAMPLE_SECTIONS, api_key="fake-key")
    assert result == []


def test_lifecycle_thresholds_defined():
    """All Q1-Q8 must have thresholds."""
    for q in ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]:
        assert q in LIFECYCLE_THRESHOLDS
