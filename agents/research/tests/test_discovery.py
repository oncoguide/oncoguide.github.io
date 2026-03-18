import json
import pytest
from unittest.mock import patch, MagicMock, Mock

from modules.discovery import (
    run_discovery,
    _oncologist_initial,
    _advocate_evaluate,
    _oncologist_respond,
    _merge_knowledge,
    SECTION_SCORE_THRESHOLD,
    ONCOLOGIST_LIFECYCLE_TOOL,
)
from modules.cost_tracker import CostTracker


def _mock_tool_use(input_dict):
    """Create a mock message with tool_use content block."""
    mock_tool = Mock()
    mock_tool.type = "tool_use"
    mock_tool.input = input_dict
    mock_msg = Mock()
    mock_msg.content = [mock_tool]
    mock_msg.usage = Mock(input_tokens=1000, output_tokens=500)
    return mock_msg


@pytest.fixture
def cost_tracker():
    return CostTracker()


@pytest.fixture
def mock_client():
    return Mock()


def test_section_score_threshold():
    assert SECTION_SCORE_THRESHOLD == 8.5


# --- Tool use assertion tests ---


def _q1q8_knowledge():
    """Standard Q1-Q8 knowledge map for tests."""
    return {
        "Q1_diagnostic": {"molecular_tests": [{"test": "NGS"}], "staging": "TNM", "subtypes": []},
        "Q2_treatment": {"approved_drugs": [{"name": "selpercatinib", "brand": "Retevmo"}], "guidelines": {}, "immunotherapy_role": "none"},
        "Q3_living": {"per_drug": [], "emergency_signs": [], "nutrition": "", "access": {}},
        "Q4_metastases": {"sites": []},
        "Q5_resistance": {"mechanisms": [], "median_time_months": 24, "next_line": []},
        "Q6_pipeline": {"drugs": [], "novel_modalities": []},
        "Q7_mistakes": {"items": []},
        "Q8_community": {"resources": []},
    }


def _q1q8_scores(all_satisfied=True, low_q=None, low_score=5.0):
    """Standard Q1-Q8 evaluation scores for tests."""
    scores = {f"Q{i}": {"score": 9.0, "assessment": "OK"} for i in range(1, 9)}
    if low_q:
        scores[low_q] = {"score": low_score, "assessment": "Incomplete"}
    return scores


@patch("modules.discovery.api_call")
def test_oncologist_initial_uses_tool_call(mock_api_call, mock_client, cost_tracker):
    """_oncologist_initial uses tool_choice, guaranteeing structured Q1-Q8 output."""
    knowledge = _q1q8_knowledge()
    mock_api_call.return_value = _mock_tool_use(knowledge)

    result = _oncologist_initial(mock_client, "RET fusion NSCLC", "claude-sonnet-4-6", cost_tracker)

    call_kwargs = mock_api_call.call_args[1]
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "submit_lifecycle_knowledge"}
    assert result["Q2_treatment"]["approved_drugs"][0]["name"] == "selpercatinib"


def test_lifecycle_tool_has_q1_q8():
    """The oncologist tool schema must have Q1-Q8 keys."""
    props = ONCOLOGIST_LIFECYCLE_TOOL["input_schema"]["properties"]
    for q in ["Q1_diagnostic", "Q2_treatment", "Q3_living", "Q4_metastases",
              "Q5_resistance", "Q6_pipeline", "Q7_mistakes", "Q8_community"]:
        assert q in props, f"Missing {q} in tool schema"


@patch("modules.discovery.api_call")
def test_advocate_evaluate_uses_tool_call(mock_api_call, mock_client, cost_tracker):
    """_advocate_evaluate uses tool_choice, guaranteeing Q1-Q8 structured output."""
    evaluation = {
        "scores": _q1q8_scores(all_satisfied=False, low_q="Q2", low_score=7.0),
        "questions": ["What about brain metastases ORR?"],
        "all_satisfied": False,
    }
    mock_api_call.return_value = _mock_tool_use(evaluation)

    result = _advocate_evaluate(
        mock_client, "RET fusion NSCLC", "knowledge text", [], "claude-sonnet-4-6", cost_tracker
    )

    call_kwargs = mock_api_call.call_args[1]
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "submit_lifecycle_evaluation"}
    assert result["all_satisfied"] is False
    assert "scores" in result


@patch("modules.discovery.api_call")
def test_oncologist_respond_uses_tool_call(mock_api_call, mock_client, cost_tracker):
    """_oncologist_respond uses tool_choice, never needs JSON parsing."""
    response = {
        "answers": [{"question": "What is the ORR?", "answer": "84% in LIBRETTO-001"}],
        "additional_knowledge": {"approved_drugs": [], "pipeline_drugs": []},
    }
    mock_api_call.return_value = _mock_tool_use(response)

    result = _oncologist_respond(
        mock_client, "RET NSCLC", ["What is the ORR?"],
        '{"approved_drugs": []}', "claude-sonnet-4-6", cost_tracker,
    )

    call_kwargs = mock_api_call.call_args[1]
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "submit_oncologist_response"}
    assert result["answers"][0]["answer"] == "84% in LIBRETTO-001"


@patch("modules.discovery.api_call")
def test_oncologist_respond_returns_dict(mock_api_call, mock_client, cost_tracker):
    """_oncologist_respond always returns a dict with answers."""
    response = {"answers": [], "additional_knowledge": {}}
    mock_api_call.return_value = _mock_tool_use(response)

    result = _oncologist_respond(
        mock_client, "dx", [], "{}", "claude-sonnet-4-6", cost_tracker,
    )
    assert isinstance(result, dict)
    assert "answers" in result


# --- Discovery loop tests ---


@patch("modules.discovery.api_call")
def test_discovery_loop_converges(mock_api_call):
    """Test that loop exits when advocate is satisfied."""
    knowledge = _q1q8_knowledge()
    eval_round1 = {
        "scores": _q1q8_scores(low_q="Q6", low_score=6.0),
        "questions": ["What about LOXO-260?"], "all_satisfied": False,
    }
    response = {
        "answers": [{"question": "What about LOXO-260?", "answer": "LOXO-260 is in Phase I by Lilly"}],
        "additional_knowledge": {"Q6_pipeline": {"drugs": [{"name": "LOXO-260", "phase": "I"}]}},
    }
    eval_round2 = {
        "scores": _q1q8_scores(),
        "questions": [], "all_satisfied": True,
    }

    mock_api_call.side_effect = [
        _mock_tool_use(knowledge),
        _mock_tool_use(eval_round1),
        _mock_tool_use(response),
        _mock_tool_use(eval_round2),
    ]

    ct = CostTracker()
    result = run_discovery("RET fusion NSCLC", "claude-sonnet-4-6", ct, api_key="fake-key")

    assert result["converged"] is True
    assert result["rounds"] == 2
    assert len(result["conversation"]) > 0
    assert "knowledge_map" in result


@patch("modules.discovery.api_call")
def test_discovery_loop_respects_max_rounds(mock_api_call):
    """Test that loop exits after max rounds even if not satisfied."""
    knowledge = _q1q8_knowledge()
    never_satisfied = {
        "scores": _q1q8_scores(low_q="Q1", low_score=5.0),
        "questions": ["More info needed"], "all_satisfied": False,
    }
    response = {"answers": [{"question": "More info needed", "answer": "Some info"}], "additional_knowledge": {}}

    responses = [_mock_tool_use(knowledge)]
    for _ in range(5):
        responses.append(_mock_tool_use(never_satisfied))
        responses.append(_mock_tool_use(response))
    mock_api_call.side_effect = responses

    ct = CostTracker()
    result = run_discovery("RET fusion NSCLC", "claude-sonnet-4-6", ct, api_key="fake-key", max_rounds=5)

    assert result["converged"] is False
    assert result["rounds"] == 5


def test_merge_knowledge_deduplicates():
    base = {
        "Q2_treatment": {"approved_drugs": [{"name": "selpercatinib", "brand": "Retevmo"}]},
        "Q6_pipeline": {"drugs": []},
    }
    additional = {
        "Q2_treatment": {
            "approved_drugs": [
                {"name": "selpercatinib", "brand": "Retevmo"},  # duplicate
                {"name": "pralsetinib", "brand": "Gavreto"},    # new
            ],
        },
        "Q6_pipeline": {"drugs": [{"name": "LOXO-260", "phase": "I"}]},
    }
    result = _merge_knowledge(base, additional)
    assert len(result["Q2_treatment"]["approved_drugs"]) == 2
    assert len(result["Q6_pipeline"]["drugs"]) == 1
    drug_names = [d["name"] for d in result["Q2_treatment"]["approved_drugs"]]
    assert "selpercatinib" in drug_names
    assert "pralsetinib" in drug_names


def test_discovery_no_api_key():
    """Test graceful fallback with no API key."""
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
    assert "DISCOVERY CONVERSATION" in prompt


# --- Conversation history pruning ---


@patch("modules.discovery.api_call")
def test_advocate_receives_pruned_history(mock_api_call, mock_client, cost_tracker):
    """Advocate receives at most last 2 conversation exchanges, not full history."""
    evaluation = {
        "scores": _q1q8_scores(),
        "questions": [], "all_satisfied": True,
    }
    mock_api_call.return_value = _mock_tool_use(evaluation)

    long_conversation = [f"exchange {i}" for i in range(5)]
    _advocate_evaluate(
        mock_client, "RET NSCLC", "knowledge text", long_conversation, "claude-sonnet-4-6", cost_tracker
    )

    call_kwargs = mock_api_call.call_args[1]
    user_content = call_kwargs["messages"][0]["content"]
    # 3 exchanges omitted, only last 2 included
    assert "3 earlier exchanges omitted" in user_content
    assert "exchange 3" in user_content
    assert "exchange 4" in user_content
    assert "exchange 0" not in user_content
