"""Tests for pre-search module -- ground discovery with real external data."""

import json
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

# Will fail until module is created
from modules.pre_search import (
    generate_template_queries,
    generate_haiku_queries,
    format_findings,
    pre_search,
    MAX_CONTEXT_CHARS,
    _get_available_searchers,
)
from modules.cost_tracker import CostTracker


# --- Template query generation ---


def test_template_queries_generated():
    queries = generate_template_queries("RET fusion NSCLC")
    assert len(queries) == 20
    for q in queries:
        assert "RET fusion NSCLC" in q["query_text"]
        assert q["search_engine"] in ("serper", "pubmed", "clinicaltrials", "openfda", "civic")
        assert q.get("language") == "en"


def test_template_years_dynamic():
    queries = generate_template_queries("RET fusion NSCLC")
    year = str(datetime.now().year)
    year_queries = [q for q in queries if year in q["query_text"]]
    assert len(year_queries) >= 4  # at least 4 templates use {year}


def test_template_no_hardcoded_years():
    queries = generate_template_queries("RET fusion NSCLC")
    all_text = " ".join(q["query_text"] for q in queries)
    # Should not contain hardcoded years from development time
    assert "2024" not in all_text


def test_template_different_diagnosis():
    queries = generate_template_queries("HER2-positive breast cancer")
    for q in queries:
        assert "HER2-positive breast cancer" in q["query_text"]


# --- Haiku complement queries ---


def _mock_tool_use(input_dict):
    from unittest.mock import Mock
    mock_tool = Mock()
    mock_tool.type = "tool_use"
    mock_tool.input = input_dict
    mock_msg = Mock()
    mock_msg.content = [mock_tool]
    mock_msg.usage = Mock(input_tokens=1000, output_tokens=500)
    return mock_msg


@patch("modules.pre_search.anthropic.Anthropic")
def test_haiku_queries_uses_tool_call(mock_cls):
    """generate_haiku_queries uses tool_choice, guaranteeing structured output."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_tool_use({
        "queries": [
            {"query_text": "selpercatinib LIBRETTO-431 PFS", "search_engine": "pubmed"},
        ]
    })

    ct = CostTracker()
    templates = generate_template_queries("RET fusion NSCLC")
    generate_haiku_queries("RET fusion NSCLC", templates, "fake-key", ct)

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "submit_haiku_queries"}


@patch("modules.pre_search.anthropic.Anthropic")
def test_haiku_queries_complement(mock_cls):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_tool_use({
        "queries": [
            {"query_text": "selpercatinib LIBRETTO-431 PFS", "search_engine": "pubmed"},
            {"query_text": "LOXO-260 RET phase I Lilly", "search_engine": "serper"},
        ]
    })

    ct = CostTracker()
    templates = generate_template_queries("RET fusion NSCLC")
    result = generate_haiku_queries("RET fusion NSCLC", templates, "fake-key", ct)
    assert len(result) == 2
    assert result[0]["search_engine"] == "pubmed"
    assert result[0].get("language") == "en"


def test_haiku_queries_no_api_key():
    ct = CostTracker()
    templates = generate_template_queries("RET fusion NSCLC")
    result = generate_haiku_queries("RET fusion NSCLC", templates, "", ct)
    assert result == []


# --- Format findings ---


def test_format_findings_as_context():
    findings = [
        {"title": "Study A", "snippet": "ORR 84%", "source": "pubmed", "url": "http://a.com", "relevance_score": 9.5},
        {"title": "Trial B", "snippet": "Phase I recruiting", "source": "clinicaltrials", "url": "http://b.com", "relevance_score": 8.0},
    ]
    result = format_findings(findings)
    assert "=== RECENT RESEARCH FINDINGS" in result
    assert "[pubmed]" in result
    assert "Study A" in result
    assert "Trial B" in result


def test_empty_results_returns_empty_string():
    result = format_findings([])
    assert result == ""


def test_max_findings_cap():
    findings = [
        {"title": f"Study {i}", "snippet": "data", "source": "pubmed", "url": f"http://{i}.com", "relevance_score": 10 - i * 0.1}
        for i in range(100)
    ]
    result = format_findings(findings, max_findings=5)
    assert "Study 0" in result
    assert "Study 4" in result
    assert "Study 5" not in result


def test_findings_sorted_by_relevance():
    findings = [
        {"title": "Low", "snippet": "x", "source": "pubmed", "url": "http://low.com", "relevance_score": 3.0},
        {"title": "High", "snippet": "x", "source": "pubmed", "url": "http://high.com", "relevance_score": 9.5},
    ]
    result = format_findings(findings, max_findings=1)
    assert "High" in result
    assert "Low" not in result


def test_context_truncated_at_limit():
    findings = [
        {"title": f"Study {i} " + "x" * 500, "snippet": "data " * 100, "source": "pubmed", "url": f"http://{i}.com", "relevance_score": 9.0}
        for i in range(100)
    ]
    result = format_findings(findings, max_findings=100)
    assert len(result) <= MAX_CONTEXT_CHARS + 200  # small buffer for truncation note


# --- Available searchers ---


def test_skips_backend_without_api_key():
    cfg = {"serper_api_key": "x", "pubmed_email": "x@x.com"}  # no openfda key
    searchers = _get_available_searchers(cfg)
    assert "openfda" not in searchers
    assert "serper" in searchers
    assert "pubmed" in searchers
    # clinicaltrials and civic have no key requirement
    assert "clinicaltrials" in searchers
    assert "civic" in searchers


def test_all_backends_available():
    cfg = {
        "serper_api_key": "x",
        "pubmed_email": "x@x.com",
        "openfda_api_key": "x",
    }
    searchers = _get_available_searchers(cfg)
    assert len(searchers) == 5


# --- Pre-search main function ---


@patch("modules.pre_search._execute_searches")
@patch("modules.pre_search.generate_haiku_queries")
def test_pre_search_dry_run(mock_haiku, mock_search):
    mock_haiku.return_value = [{"query_text": "test", "search_engine": "pubmed", "language": "en"}]
    ct = CostTracker()
    cfg = {"anthropic_api_key": "fake"}
    result = pre_search("RET fusion NSCLC", cfg, ct, dry_run=True)
    assert result == ""
    mock_search.assert_not_called()  # searches skipped in dry-run


@patch("modules.pre_search.enrich_batch")
@patch("modules.pre_search._execute_searches")
@patch("modules.pre_search.generate_haiku_queries")
def test_pre_search_returns_formatted_context(mock_haiku, mock_search, mock_enrich):
    mock_haiku.return_value = []
    mock_search.return_value = [
        {"title": "Finding A", "snippet": "Data A", "url": "http://a.com", "source": "serper"},
    ]
    mock_enrich.return_value = [
        {"relevant": True, "relevance_score": 9.0, "title_english": "A", "summary_english": "Data A"},
    ]

    ct = CostTracker()
    cfg = {"anthropic_api_key": "fake", "enrichment_model": "claude-haiku-4-5-20251001"}
    result = pre_search("RET fusion NSCLC", cfg, ct)
    assert "Finding A" in result
    assert "=== RECENT RESEARCH FINDINGS" in result


@patch("modules.pre_search._execute_searches")
@patch("modules.pre_search.generate_haiku_queries")
def test_pre_search_no_results_returns_empty(mock_haiku, mock_search):
    mock_haiku.return_value = []
    mock_search.return_value = []

    ct = CostTracker()
    cfg = {"anthropic_api_key": "fake"}
    result = pre_search("RET fusion NSCLC", cfg, ct)
    assert result == ""


@patch("modules.pre_search.enrich_batch")
@patch("modules.pre_search._execute_searches")
@patch("modules.pre_search.generate_haiku_queries")
def test_pre_search_filters_irrelevant(mock_haiku, mock_search, mock_enrich):
    mock_haiku.return_value = []
    mock_search.return_value = [
        {"title": "Relevant", "snippet": "x", "url": "http://a.com"},
        {"title": "Irrelevant", "snippet": "x", "url": "http://b.com"},
    ]
    mock_enrich.return_value = [
        {"relevant": True, "relevance_score": 9.0},
        {"relevant": False, "relevance_score": 2.0},
    ]

    ct = CostTracker()
    cfg = {"anthropic_api_key": "fake", "enrichment_model": "claude-haiku-4-5-20251001"}
    result = pre_search("RET fusion NSCLC", cfg, ct)
    assert "Relevant" in result
    assert "Irrelevant" not in result
