import pytest
from unittest.mock import patch, MagicMock, Mock

from modules.enrichment import enrich_finding, enrich_batch


def _mock_tool_use(input_dict):
    mock_tool = Mock()
    mock_tool.type = "tool_use"
    mock_tool.input = input_dict
    mock_msg = Mock()
    mock_msg.content = [mock_tool]
    mock_msg.usage = Mock(input_tokens=100, output_tokens=50)
    return mock_msg


@patch("modules.enrichment.anthropic.Anthropic")
def test_enrich_uses_tool_call(mock_anthropic_cls):
    """enrich_finding uses tool_choice, guaranteeing structured output."""
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_tool_use({
        "relevant": True, "relevance_score": 8, "authority_score": 4,
        "lifecycle_stage": "Q2",
        "title_english": "Test Title EN", "summary_english": "Summary text",
    })

    result = enrich_finding(
        finding={"title": "Test", "url": "https://example.com", "snippet": "content",
                 "language": "en", "date": "2026-01-01"},
        topic_title="Cancer Diagnosis",
        api_key="fake-key",
    )

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "submit_enrichment"}
    assert result["relevant"] is True
    assert result["relevance_score"] == 8
    assert result["authority_score"] == 4
    assert result["lifecycle_stage"] == "Q2"


@patch("modules.enrichment.anthropic.Anthropic")
def test_enrich_relevant_finding(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_tool_use({
        "relevant": True, "relevance_score": 8, "authority_score": 3,
        "lifecycle_stage": "Q3",
        "title_english": "Test Title EN", "summary_english": "Summary text",
    })

    result = enrich_finding(
        finding={"title": "Test", "url": "https://example.com", "snippet": "content",
                 "language": "en", "date": "2026-01-01"},
        topic_title="Cancer Diagnosis",
        api_key="fake-key",
    )
    assert result["relevant"] is True
    assert result["relevance_score"] == 8
    assert result["lifecycle_stage"] == "Q3"


@patch("modules.enrichment.anthropic.Anthropic")
def test_enrich_irrelevant_finding(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_tool_use({
        "relevant": False, "relevance_score": 2, "authority_score": 1,
        "lifecycle_stage": "Q3",
        "title_english": "", "summary_english": "",
    })

    result = enrich_finding(
        finding={"title": "Unrelated", "url": "https://example.com/x", "snippet": "cats",
                 "language": "en", "date": None},
        topic_title="Cancer Diagnosis",
        api_key="fake-key",
    )
    assert result["relevant"] is False


@patch("modules.enrichment.anthropic.Anthropic")
def test_enrich_returns_authority_score(mock_anthropic_cls):
    """Authority score (1-5) should be returned by enrichment."""
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_tool_use({
        "relevant": True, "relevance_score": 9, "authority_score": 5,
        "lifecycle_stage": "Q2",
        "title_english": "LIBRETTO-431", "summary_english": "Phase III results",
    })

    result = enrich_finding(
        finding={"title": "LIBRETTO-431", "url": "https://nejm.org/1", "snippet": "phase III",
                 "language": "en", "date": "2025-03"},
        topic_title="RET fusion NSCLC",
        api_key="fake-key",
    )
    assert result["authority_score"] == 5


@patch("modules.enrichment.anthropic.Anthropic")
def test_enrich_error_fallback(mock_anthropic_cls):
    """Network/API error returns safe fallback dict."""
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.side_effect = Exception("Network error")

    result = enrich_finding(
        finding={"title": "Test", "url": "https://example.com", "snippet": "x",
                 "language": "en", "date": "2025"},
        topic_title="Cancer",
        api_key="fake-key",
    )
    assert result["relevant"] is False
    assert result["relevance_score"] == 0
    assert result["authority_score"] == 0
