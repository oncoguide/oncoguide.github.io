"""Tests for cross-verification module -- compare discovery claims vs real findings."""

import json
from unittest.mock import patch, MagicMock, Mock

import pytest

from modules.cross_verify import cross_verify, format_report
from modules.cost_tracker import CostTracker


def _mock_tool_use(input_dict):
    mock_tool = Mock()
    mock_tool.type = "tool_use"
    mock_tool.input = input_dict
    mock_msg = Mock()
    mock_msg.content = [mock_tool]
    mock_msg.usage = Mock(input_tokens=1000, output_tokens=500)
    return mock_msg


SAMPLE_KNOWLEDGE = {"approved_drugs": [{"name": "selpercatinib", "ORR": "84%", "PFS": "24.8mo"}]}
SAMPLE_FINDINGS = [
    {"id": 3, "title_english": "LIBRETTO-431", "summary_english": "ORR 84%",
     "relevance_score": 9, "authority_score": 5, "source_url": "https://nejm.org/1"},
    {"id": 7, "title_english": "Updated PFS", "summary_english": "median PFS 22.0 months",
     "relevance_score": 8, "authority_score": 4, "source_url": "https://jco.org/1"},
]


@patch("modules.cross_verify.anthropic.Anthropic")
def test_cross_verify_uses_tool_call(mock_cls):
    """cross_verify uses tool_choice, guaranteeing structured output."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_tool_use({
        "verified": [{"claim": "ORR 84%", "finding_id": 3, "finding_value": "ORR 84%"}],
        "contradicted": [],
        "unverified": [],
    })

    ct = CostTracker()
    result = cross_verify(
        knowledge_map=SAMPLE_KNOWLEDGE, findings=SAMPLE_FINDINGS,
        diagnosis="RET fusion NSCLC", api_key="fake-key", cost=ct,
    )

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "submit_verification"}
    assert len(result["verified"]) == 1


@patch("modules.cross_verify.anthropic.Anthropic")
def test_cross_verify_returns_report(mock_cls):
    """Cross-verify should return a structured report."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    mock_client.messages.create.return_value = _mock_tool_use({
        "verified": [{"claim": "ORR 84%", "finding_id": 3, "finding_value": "ORR 84%"}],
        "contradicted": [{"claim": "PFS 24.8 months", "discovery_value": "24.8mo",
                          "finding_id": 7, "finding_value": "PFS 22.0 months", "authority_score": 4}],
        "unverified": [{"claim": "Brain ORR 91%", "reason": "No findings with authority >= 3"}],
    })

    ct = CostTracker()
    result = cross_verify(
        knowledge_map=SAMPLE_KNOWLEDGE, findings=SAMPLE_FINDINGS,
        diagnosis="RET fusion NSCLC", api_key="fake-key", cost=ct,
    )
    assert "verified" in result
    assert "contradicted" in result
    assert "unverified" in result
    assert len(result["verified"]) == 1
    assert len(result["contradicted"]) == 1


@patch("modules.cross_verify.anthropic.Anthropic")
def test_cross_verify_no_findings_returns_empty(mock_cls):
    """With no findings, cross-verify should return an empty report."""
    ct = CostTracker()
    result = cross_verify(
        knowledge_map={"approved_drugs": [{"name": "drug"}]},
        findings=[], diagnosis="Test", api_key="fake-key", cost=ct,
    )
    assert result["verified"] == []
    assert result["contradicted"] == []
    assert result["unverified"] == []


def test_cross_verify_no_api_key():
    """Without API key, return empty report."""
    ct = CostTracker()
    result = cross_verify(
        knowledge_map={"approved_drugs": []},
        findings=[{"id": 1, "authority_score": 4}],
        diagnosis="Test", api_key="", cost=ct,
    )
    assert result["verified"] == []


def test_format_report_readable():
    """Format report should produce human-readable text."""
    report = {
        "verified": [{"claim": "ORR 84%", "finding_id": 3, "finding_value": "ORR 84%"}],
        "contradicted": [{"claim": "PFS 24.8mo", "discovery_value": "24.8mo",
                          "finding_id": 7, "finding_value": "PFS 22.0mo", "authority_score": 4, "use_finding": True}],
        "unverified": [{"claim": "Brain ORR 91%", "reason": "No high-authority finding"}],
    }
    text = format_report(report)
    assert "VERIFIED" in text
    assert "CONTRADICTED" in text
    assert "UNVERIFIED" in text
    assert "ORR 84%" in text


def test_format_report_empty():
    """Empty report should produce a short summary."""
    report = {"verified": [], "contradicted": [], "unverified": []}
    text = format_report(report)
    assert "No claims" in text or text == ""
