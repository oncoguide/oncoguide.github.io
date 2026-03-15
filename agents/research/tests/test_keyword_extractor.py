import json
import pytest
from unittest.mock import patch, MagicMock

from modules.keyword_extractor import extract_queries


def _mock_message(text):
    return MagicMock(
        content=[MagicMock(text=text)],
        usage=MagicMock(input_tokens=5000, output_tokens=3000),
    )


@patch("modules.keyword_extractor.anthropic.Anthropic")
def test_extracts_queries_from_conversation(mock_cls):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    queries = [
        {"query_text": "selpercatinib ORR phase III", "search_engine": "pubmed",
         "language": "en", "target_section": "treatment-efficacy", "rationale": "confirm ORR"},
        {"query_text": "LOXO-260 RET inhibitor phase I", "search_engine": "serper",
         "language": "en", "target_section": "pipeline", "rationale": "pipeline drug"},
    ]
    mock_client.messages.create.return_value = _mock_message(json.dumps(queries))

    from modules.cost_tracker import CostTracker
    ct = CostTracker()
    result = extract_queries(
        diagnosis="RET fusion NSCLC",
        conversation=["ONCOLOGIST: ...", "ADVOCATE: ..."],
        knowledge_map={"approved_drugs": [{"name": "selpercatinib"}]},
        api_key="fake-key",
        model="claude-sonnet-4-6",
        cost=ct,
    )
    assert len(result) == 2
    assert result[0]["search_engine"] == "pubmed"
    assert result[1]["target_section"] == "pipeline"


def test_no_api_key_returns_empty():
    from modules.cost_tracker import CostTracker
    ct = CostTracker()
    result = extract_queries(
        diagnosis="test", conversation=[], knowledge_map={},
        api_key="", model="claude-sonnet-4-6", cost=ct,
    )
    assert result == []
