import pytest
from unittest.mock import patch, MagicMock

from modules.enrichment import enrich_finding, enrich_batch


@patch("modules.enrichment.anthropic.Anthropic")
def test_enrich_relevant_finding(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"relevant": true, "relevance_score": 8, "title_english": "Test Title EN", "summary_english": "Summary text"}')],
        usage=MagicMock(input_tokens=100, output_tokens=50),
    )
    result = enrich_finding(
        finding={"title": "Test", "url": "https://example.com", "snippet": "content", "language": "en", "date": "2026-01-01"},
        topic_title="Cancer Diagnosis",
        api_key="fake-key",
    )
    assert result["relevant"] is True
    assert result["relevance_score"] == 8


@patch("modules.enrichment.anthropic.Anthropic")
def test_enrich_irrelevant_finding(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"relevant": false, "relevance_score": 2, "title_english": "", "summary_english": ""}')],
        usage=MagicMock(input_tokens=100, output_tokens=30),
    )
    result = enrich_finding(
        finding={"title": "Unrelated", "url": "https://example.com/x", "snippet": "cats", "language": "en", "date": None},
        topic_title="Cancer Diagnosis",
        api_key="fake-key",
    )
    assert result["relevant"] is False


# --- Authority score tests ---


@patch("modules.enrichment.anthropic.Anthropic")
def test_enrich_returns_authority_score(mock_anthropic_cls):
    """Authority score (1-5) should be returned by enrichment."""
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"relevant": true, "relevance_score": 9, "authority_score": 5, "title_english": "LIBRETTO-431", "summary_english": "Phase III results"}')],
        usage=MagicMock(input_tokens=100, output_tokens=60),
    )
    result = enrich_finding(
        finding={"title": "LIBRETTO-431", "url": "https://nejm.org/1", "snippet": "phase III", "language": "en", "date": "2025-03"},
        topic_title="RET fusion NSCLC",
        api_key="fake-key",
    )
    assert result["authority_score"] == 5


@patch("modules.enrichment.anthropic.Anthropic")
def test_enrich_authority_score_default_zero(mock_anthropic_cls):
    """If model doesn't return authority_score, default to 0."""
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    # Old-style response without authority_score
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"relevant": true, "relevance_score": 7, "title_english": "Test", "summary_english": "data"}')],
        usage=MagicMock(input_tokens=100, output_tokens=50),
    )
    result = enrich_finding(
        finding={"title": "Test", "url": "https://example.com", "snippet": "x", "language": "en", "date": "2025"},
        topic_title="Cancer",
        api_key="fake-key",
    )
    # Should have authority_score key, defaulting to 0 if not in response
    assert result.get("authority_score", 0) == 0
