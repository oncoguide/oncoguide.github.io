"""Tests for cross-verification module -- compare discovery claims vs real findings."""

import json
from unittest.mock import patch, MagicMock

import pytest

from modules.cross_verify import cross_verify, format_report
from modules.cost_tracker import CostTracker


def _mock_message(text):
    return MagicMock(
        content=[MagicMock(text=text)],
        usage=MagicMock(input_tokens=1000, output_tokens=500),
    )


@patch("modules.cross_verify.anthropic.Anthropic")
def test_cross_verify_returns_report(mock_cls):
    """Cross-verify should return a structured report."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    report = {
        "verified": [
            {"claim": "ORR 84%", "finding_id": 3, "finding_value": "ORR 84%", "status": "VERIFIED"}
        ],
        "contradicted": [
            {"claim": "PFS 24.8 months", "finding_id": 7, "finding_value": "PFS 22.0 months",
             "status": "CONTRADICTED", "use_finding": True}
        ],
        "unverified": [
            {"claim": "Brain ORR 91%", "status": "UNVERIFIED", "reason": "No findings with authority >= 3"}
        ],
    }
    mock_client.messages.create.return_value = _mock_message(json.dumps(report))

    ct = CostTracker()
    knowledge_map = {"approved_drugs": [{"name": "selpercatinib", "ORR": "84%", "PFS": "24.8mo"}]}
    findings = [
        {"id": 3, "title_english": "LIBRETTO-431", "summary_english": "ORR 84%",
         "relevance_score": 9, "authority_score": 5, "source_url": "https://nejm.org/1"},
        {"id": 7, "title_english": "Updated PFS", "summary_english": "median PFS 22.0 months",
         "relevance_score": 8, "authority_score": 4, "source_url": "https://jco.org/1"},
    ]

    result = cross_verify(
        knowledge_map=knowledge_map,
        findings=findings,
        diagnosis="RET fusion NSCLC",
        api_key="fake-key",
        cost=ct,
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
        findings=[],
        diagnosis="Test",
        api_key="fake-key",
        cost=ct,
    )
    assert result["verified"] == []
    assert result["contradicted"] == []
    assert result["unverified"] == []


def test_cross_verify_no_api_key():
    """Without API key, return empty report."""
    ct = CostTracker()
    result = cross_verify(
        knowledge_map={"approved_drugs": []},
        findings=[{"id": 1}],
        diagnosis="Test",
        api_key="",
        cost=ct,
    )
    assert result["verified"] == []


def test_format_report_readable():
    """Format report should produce human-readable text."""
    report = {
        "verified": [
            {"claim": "ORR 84%", "finding_id": 3, "finding_value": "ORR 84%", "status": "VERIFIED"}
        ],
        "contradicted": [
            {"claim": "PFS 24.8mo", "finding_id": 7, "finding_value": "PFS 22.0mo",
             "status": "CONTRADICTED", "use_finding": True}
        ],
        "unverified": [
            {"claim": "Brain ORR 91%", "status": "UNVERIFIED", "reason": "No high-authority finding"}
        ],
    }
    text = format_report(report)
    assert "VERIFIED" in text
    assert "CONTRADICTED" in text
    assert "UNVERIFIED" in text
    assert "ORR 84%" in text
    assert "PFS 22.0mo" in text


def test_format_report_empty():
    """Empty report should produce a short summary."""
    report = {"verified": [], "contradicted": [], "unverified": []}
    text = format_report(report)
    assert "No claims" in text or text == ""
