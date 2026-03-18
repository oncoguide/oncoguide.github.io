import pytest
from unittest.mock import patch, MagicMock, Mock

from modules.gap_analyzer import analyze_gaps, _map_findings_to_sections


def _mock_tool_use(input_dict):
    mock_tool = Mock()
    mock_tool.type = "tool_use"
    mock_tool.input = input_dict
    mock_msg = Mock()
    mock_msg.content = [mock_tool]
    mock_msg.usage = Mock(input_tokens=50, output_tokens=20)
    return mock_msg


SAMPLE_FINDINGS = [
    {"title_english": "Selpercatinib Phase III results", "relevance_score": 9},
    {"title_english": "RET inhibitor side effects", "relevance_score": 7},
    {"title_english": "LIBRETTO-431 OS data", "relevance_score": 8},
    {"title_english": "Pralsetinib approval", "relevance_score": 8},
    {"title_english": "RET resistance mechanisms", "relevance_score": 7},
]

SAMPLE_SECTIONS = [
    {"id": "best-treatment", "title": "Treatment Efficacy", "description": "Drug response rates"},
    {"id": "side-effects", "title": "Side Effects", "description": "Adverse events with frequencies"},
    {"id": "resistance", "title": "Resistance", "description": "Resistance mechanisms"},
]


def test_map_findings_uses_tool_call():
    """_map_findings_to_sections uses tool_choice."""
    mock_client = Mock()
    mock_client.messages.create.return_value = _mock_tool_use({
        "section_map": {"best-treatment": [0, 1, 2], "side-effects": [3, 4]}
    })

    result = _map_findings_to_sections(SAMPLE_FINDINGS, SAMPLE_SECTIONS, mock_client, "claude-haiku-4-5-20251001")

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["tool_choice"]["name"] == "submit_section_map"
    assert result == {"best-treatment": [0, 1, 2], "side-effects": [3, 4]}


@patch("modules.gap_analyzer.anthropic.Anthropic")
def test_gap_queries_uses_tool_call(mock_cls):
    """analyze_gaps uses tool_choice for gap query generation."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    mock_client.messages.create.side_effect = [
        # First call: _map_findings_to_sections
        _mock_tool_use({"section_map": {"best-treatment": [1, 2], "side-effects": [], "resistance": [5]}}),
        # Second call: gap query generation
        _mock_tool_use({
            "queries": [{"query_text": "selpercatinib resistance", "search_engine": "pubmed", "section_id": "resistance"}]
        }),
    ]

    result = analyze_gaps("RET fusion NSCLC", SAMPLE_FINDINGS, SAMPLE_SECTIONS, "fake-key")

    # Verify the gap queries call used tool_choice
    second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
    assert second_call_kwargs["tool_choice"] == {"type": "tool", "name": "submit_gap_queries"}
    assert len(result) == 1
    # section_id should be normalized to target_section
    assert result[0].get("target_section") == "resistance"


@patch("modules.gap_analyzer.anthropic.Anthropic")
def test_gap_queries_empty_when_all_covered(mock_cls):
    """analyze_gaps returns empty list when all sections are well-covered."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    mock_client.messages.create.side_effect = [
        _mock_tool_use({"section_map": {"best-treatment": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}}),
        _mock_tool_use({"queries": []}),
    ]

    result = analyze_gaps("RET fusion NSCLC", SAMPLE_FINDINGS, SAMPLE_SECTIONS, "fake-key")
    assert result == []


def test_analyze_gaps_no_api_key():
    result = analyze_gaps("topic", SAMPLE_FINDINGS, SAMPLE_SECTIONS, api_key="")
    assert result == []


def test_analyze_gaps_no_findings():
    result = analyze_gaps("topic", [], SAMPLE_SECTIONS, api_key="fake-key")
    assert result == []
