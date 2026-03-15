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
