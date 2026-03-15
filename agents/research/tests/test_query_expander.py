import pytest
from unittest.mock import patch, MagicMock

from modules.query_expander import expand_queries


@patch("modules.query_expander.anthropic.Anthropic")
def test_expands_base_queries(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='[{"query_text": "expanded query", "search_engine": "serper", "language": "en"}]')]
    )
    result = expand_queries(
        topic_title="Cancer Diagnosis",
        base_queries=["cancer diagnosis protocol"],
        api_key="fake-key",
        model="claude-haiku-4-5-20251001",
    )
    assert isinstance(result, list)
    assert len(result) >= 1
    # Base query should be included
    base_texts = [q["query_text"] for q in result]
    assert "cancer diagnosis protocol" in base_texts


def test_base_queries_included_in_output():
    """Base queries should always be in the output even if expansion fails."""
    result = expand_queries(
        topic_title="Cancer Diagnosis",
        base_queries=["query1", "query2"],
        api_key="",
        model="claude-haiku-4-5-20251001",
    )
    assert len(result) >= 2
    texts = [q["query_text"] for q in result]
    assert "query1" in texts
    assert "query2" in texts
