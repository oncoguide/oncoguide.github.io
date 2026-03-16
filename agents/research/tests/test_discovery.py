import json
import pytest
from unittest.mock import patch, MagicMock

from modules.discovery import (
    run_discovery,
    _oncologist_initial,
    _advocate_evaluate,
    _oncologist_respond,
    _haiku_structurer,
    _merge_knowledge,
    _parse_json,
    SECTION_SCORE_THRESHOLD,
)


def _mock_message(text):
    return MagicMock(
        content=[MagicMock(text=text)],
        usage=MagicMock(input_tokens=1000, output_tokens=500),
    )


def test_section_score_threshold():
    assert SECTION_SCORE_THRESHOLD == 8.5


def test_oncologist_initial_returns_knowledge():
    mock_client = MagicMock()
    knowledge = {
        "approved_drugs": [{"name": "selpercatinib", "brand": "Retevmo"}],
        "pipeline_drugs": [],
        "landmark_trials": [],
        "side_effects": [],
        "resistance": [],
        "guidelines": [],
        "testing": [],
    }
    mock_client.messages.create.return_value = _mock_message(json.dumps(knowledge))

    from modules.cost_tracker import CostTracker
    ct = CostTracker()
    result = _oncologist_initial(mock_client, "RET fusion NSCLC", "claude-sonnet-4-6", ct)
    assert "approved_drugs" in result
    assert result["approved_drugs"][0]["name"] == "selpercatinib"


def test_advocate_evaluate_returns_scores():
    mock_client = MagicMock()
    evaluation = {
        "section_scores": {
            "big-picture": {"score": 9.0, "assessment": "Good"},
            "treatment-efficacy": {"score": 7.0, "assessment": "Missing PFS data"},
        },
        "questions": ["What about brain metastases ORR?"],
        "all_satisfied": False,
    }
    mock_client.messages.create.return_value = _mock_message(json.dumps(evaluation))

    from modules.cost_tracker import CostTracker
    ct = CostTracker()
    result = _advocate_evaluate(
        mock_client, "RET fusion NSCLC", "knowledge text", [], "claude-sonnet-4-6", ct
    )
    assert "section_scores" in result
    assert result["all_satisfied"] is False


@patch("modules.discovery.anthropic.Anthropic")
def test_discovery_loop_converges(mock_cls):
    """Test that loop exits when advocate is satisfied."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    # Round 1: oncologist initial
    knowledge = {"approved_drugs": [{"name": "selpercatinib"}], "pipeline_drugs": [], "landmark_trials": [], "side_effects": [], "resistance": [], "guidelines": [], "testing": []}
    # Round 1: advocate not satisfied
    eval_round1 = {"section_scores": {"big-picture": {"score": 9.0, "assessment": "OK"}, "pipeline": {"score": 6.0, "assessment": "Missing drugs"}}, "questions": ["What about LOXO-260?"], "all_satisfied": False}
    # Round 2: oncologist responds
    response = {"answers": [{"question": "What about LOXO-260?", "answer": "LOXO-260 is in Phase I by Lilly"}], "additional_knowledge": {"pipeline_drugs": [{"name": "LOXO-260", "phase": "I"}]}}
    # Round 2: advocate satisfied
    eval_round2 = {"section_scores": {"big-picture": {"score": 9.0, "assessment": "OK"}, "pipeline": {"score": 9.0, "assessment": "Complete now"}}, "questions": [], "all_satisfied": True}

    mock_client.messages.create.side_effect = [
        _mock_message(json.dumps(knowledge)),
        _mock_message(json.dumps(eval_round1)),
        _mock_message(json.dumps(response)),
        _mock_message(json.dumps(eval_round2)),
    ]

    from modules.cost_tracker import CostTracker
    ct = CostTracker()
    result = run_discovery("RET fusion NSCLC", "claude-sonnet-4-6", ct, api_key="fake-key")

    assert result["converged"] is True
    assert result["rounds"] == 2
    assert len(result["conversation"]) > 0
    assert "knowledge_map" in result


@patch("modules.discovery.anthropic.Anthropic")
def test_discovery_loop_respects_max_rounds(mock_cls):
    """Test that loop exits after max rounds even if not satisfied."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    knowledge = {"approved_drugs": [], "pipeline_drugs": [], "landmark_trials": [], "side_effects": [], "resistance": [], "guidelines": [], "testing": []}
    never_satisfied = {"section_scores": {"big-picture": {"score": 5.0, "assessment": "Weak"}}, "questions": ["More info needed"], "all_satisfied": False}
    response = {"answers": [{"question": "More info needed", "answer": "Some info"}], "additional_knowledge": {}}

    # Will be called repeatedly: oncologist_initial, then (advocate + oncologist) * max_rounds
    responses = [_mock_message(json.dumps(knowledge))]
    for _ in range(5):  # max rounds
        responses.append(_mock_message(json.dumps(never_satisfied)))
        responses.append(_mock_message(json.dumps(response)))
    mock_client.messages.create.side_effect = responses

    from modules.cost_tracker import CostTracker
    ct = CostTracker()
    result = run_discovery("RET fusion NSCLC", "claude-sonnet-4-6", ct, api_key="fake-key", max_rounds=5)

    assert result["converged"] is False
    assert result["rounds"] == 5


def test_merge_knowledge_deduplicates():
    base = {"approved_drugs": [{"name": "selpercatinib", "brand": "Retevmo"}], "pipeline_drugs": []}
    additional = {
        "approved_drugs": [
            {"name": "selpercatinib", "brand": "Retevmo"},  # duplicate
            {"name": "pralsetinib", "brand": "Gavreto"},  # new
        ],
        "pipeline_drugs": [{"name": "LOXO-260", "phase": "I"}],
    }
    result = _merge_knowledge(base, additional)
    assert len(result["approved_drugs"]) == 2  # selpercatinib + pralsetinib (no dupe)
    assert len(result["pipeline_drugs"]) == 1
    drug_names = [d["name"] for d in result["approved_drugs"]]
    assert "selpercatinib" in drug_names
    assert "pralsetinib" in drug_names


def test_discovery_no_api_key():
    """Test graceful fallback with no API key."""
    from modules.cost_tracker import CostTracker
    ct = CostTracker()
    result = run_discovery("RET fusion NSCLC", "claude-sonnet-4-6", ct, api_key="")
    assert result["converged"] is False
    assert result["conversation"] == []


# --- Pre-search context injection ---


def test_discovery_with_pre_search_context():
    """Test that pre-search context is injected into oncologist prompt."""
    from modules.discovery import _oncologist_system

    context = '[PubMed] "LOXO-260 Phase I" (2025)\n  Next-gen RET inhibitor'
    prompt = _oncologist_system("Test oncologist persona", pre_search_context=context)
    assert "LOXO-260" in prompt
    assert "REAL-WORLD RESEARCH DATA" in prompt


def test_discovery_without_pre_search_context():
    """Test backward compatibility -- empty context does not break prompt."""
    from modules.discovery import _oncologist_system

    prompt = _oncologist_system("Test persona", pre_search_context="")
    assert "REAL-WORLD RESEARCH DATA" not in prompt
    # Core prompt still present
    assert "DISCOVERY CONVERSATION" in prompt


# --- Haiku structurer fallback ---


def test_haiku_structurer_extracts_json_from_narrative():
    """Test that Haiku structurer converts narrative text to JSON."""
    mock_client = MagicMock()
    structured = {
        "answers": [{"question": "What about brain mets?", "answer": "Selpercatinib shows 82% intracranial ORR"}],
        "additional_knowledge": {"approved_drugs": [], "pipeline_drugs": [], "landmark_trials": [],
                                  "side_effects": [], "resistance": [], "guidelines": [], "testing": []},
    }
    mock_client.messages.create.return_value = _mock_message(json.dumps(structured))

    from modules.cost_tracker import CostTracker
    ct = CostTracker()
    result = _haiku_structurer(
        mock_client,
        "Selpercatinib shows 82% intracranial ORR in brain metastases...",
        ["What about brain mets?"],
        ct,
    )
    assert result["answers"][0]["answer"] == "Selpercatinib shows 82% intracranial ORR"


def test_oncologist_respond_falls_back_to_haiku():
    """Test that _oncologist_respond uses Haiku fallback when Sonnet returns narrative."""
    mock_client = MagicMock()

    # First call (Sonnet): returns narrative prose, not JSON
    narrative_response = _mock_message(
        "Selpercatinib (Retevmo) is a first-line treatment for RET fusion NSCLC. "
        "The LIBRETTO-001 trial showed 64% ORR in previously treated patients."
    )
    # Second call (Haiku structurer): returns proper JSON
    structured = {
        "answers": [{"question": "What about treatment?", "answer": "Selpercatinib 64% ORR"}],
        "additional_knowledge": {"approved_drugs": [{"name": "selpercatinib"}], "pipeline_drugs": [],
                                  "landmark_trials": [], "side_effects": [], "resistance": [],
                                  "guidelines": [], "testing": []},
    }
    haiku_response = _mock_message(json.dumps(structured))

    mock_client.messages.create.side_effect = [narrative_response, haiku_response]

    from modules.cost_tracker import CostTracker
    ct = CostTracker()
    result = _oncologist_respond(
        mock_client, "RET fusion NSCLC", ["What about treatment?"],
        '{"approved_drugs": []}', "claude-sonnet-4-6", ct,
    )
    assert "answers" in result
    assert result["additional_knowledge"]["approved_drugs"][0]["name"] == "selpercatinib"
    # Verify both Sonnet and Haiku were called
    assert mock_client.messages.create.call_count == 2


def test_oncologist_respond_no_fallback_when_json_valid():
    """Test that Haiku fallback is NOT called when Sonnet returns valid JSON."""
    mock_client = MagicMock()
    valid_json = {
        "answers": [{"question": "Q1", "answer": "A1"}],
        "additional_knowledge": {},
    }
    mock_client.messages.create.return_value = _mock_message(json.dumps(valid_json))

    from modules.cost_tracker import CostTracker
    ct = CostTracker()
    result = _oncologist_respond(
        mock_client, "RET fusion NSCLC", ["Q1"],
        '{"approved_drugs": []}', "claude-sonnet-4-6", ct,
    )
    assert result["answers"][0]["answer"] == "A1"
    # Only Sonnet called, no Haiku fallback
    assert mock_client.messages.create.call_count == 1


def test_parse_json_handles_mixed_text_and_json():
    """Test _parse_json extracts JSON from text with surrounding narrative."""
    raw = 'Here is the data you requested:\n\n{"answers": [{"q": "test"}]}\n\nLet me know if you need more.'
    result = _parse_json(raw, "test")
    assert result["answers"][0]["q"] == "test"


def test_parse_json_returns_empty_on_pure_narrative():
    """Test _parse_json returns {} when no valid JSON exists."""
    raw = "Selpercatinib is a kinase inhibitor approved for RET fusion NSCLC. It shows good efficacy."
    result = _parse_json(raw, "test")
    assert result == {}
