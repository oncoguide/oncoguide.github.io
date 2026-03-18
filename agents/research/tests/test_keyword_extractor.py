import json
import pytest
from unittest.mock import patch, MagicMock, Mock

from modules.keyword_extractor import extract_queries
from modules.cost_tracker import CostTracker


def _mock_tool_use(input_dict):
    mock_tool = Mock()
    mock_tool.type = "tool_use"
    mock_tool.input = input_dict
    mock_msg = Mock()
    mock_msg.content = [mock_tool]
    mock_msg.usage = Mock(input_tokens=5000, output_tokens=3000)
    return mock_msg


@patch("modules.keyword_extractor.api_call")
def test_extract_queries_uses_tool_call(mock_api_call):
    """extract_queries uses tool_choice, guaranteeing structured output."""
    queries_data = {
        "queries": [
            {
                "query_text": "selpercatinib LIBRETTO-001 ORR",
                "search_engine": "pubmed",
                "lifecycle_stage": "Q2",
                "priority": "high",
                "language": "en",
            }
        ]
    }
    mock_api_call.return_value = _mock_tool_use(queries_data)

    ct = CostTracker()
    result = extract_queries(
        diagnosis="RET fusion NSCLC",
        conversation=["ONCOLOGIST: ...", "ADVOCATE: ..."],
        knowledge_map={"approved_drugs": [{"name": "selpercatinib"}]},
        api_key="fake-key",
        model="claude-sonnet-4-6",
        cost=ct,
    )

    call_kwargs = mock_api_call.call_args[1]
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "submit_queries"}
    assert len(result) == 1
    assert result[0]["query_text"] == "selpercatinib LIBRETTO-001 ORR"


@patch("modules.keyword_extractor.api_call")
def test_extracts_queries_from_conversation(mock_api_call):
    queries_data = {
        "queries": [
            {"query_text": "selpercatinib ORR phase III", "search_engine": "pubmed",
             "lifecycle_stage": "Q2", "language": "en"},
            {"query_text": "LOXO-260 RET inhibitor phase I", "search_engine": "serper",
             "lifecycle_stage": "Q6", "language": "en"},
        ]
    }
    mock_api_call.return_value = _mock_tool_use(queries_data)

    ct = CostTracker()
    result = extract_queries(
        diagnosis="RET fusion NSCLC",
        conversation=["ONCOLOGIST: ...", "ADVOCATE: ..."],
        knowledge_map={"Q2_treatment": {"approved_drugs": [{"name": "selpercatinib"}]}},
        api_key="fake-key",
        model="claude-sonnet-4-6",
        cost=ct,
    )
    assert len(result) == 2
    assert result[0]["search_engine"] == "pubmed"
    assert result[0]["lifecycle_stage"] == "Q2"
    assert result[1]["lifecycle_stage"] == "Q6"


def test_no_api_key_returns_empty():
    ct = CostTracker()
    result = extract_queries(
        diagnosis="test", conversation=[], knowledge_map={},
        api_key="", model="claude-sonnet-4-6", cost=ct,
    )
    assert result == []
