import json
import pytest
from unittest.mock import patch, MagicMock, Mock

from modules.validation import validate_guide
from modules.cost_tracker import CostTracker


def _mock_tool_use(input_dict):
    mock_tool = Mock()
    mock_tool.type = "tool_use"
    mock_tool.input = input_dict
    mock_msg = Mock()
    mock_msg.content = [mock_tool]
    mock_msg.usage = Mock(input_tokens=3000, output_tokens=2000)
    return mock_msg


GOOD_ONCO_REVIEW = {
    "overall": "ACCURATE",
    "accuracy_issues": [],
    "missing_data": [],
    "safety_concerns": [],
}

GOOD_ADVOCATE_REVIEW = {
    "section_scores": {"big-picture": {"score": 9.0, "assessment": "Good"},
                       "pipeline": {"score": 9.0, "assessment": "Complete"}},
    "missing_keywords": [],
    "overall_score": 9.0,
    "passed": True,
    "learnings": [],
}


@patch("modules.validation.api_call")
def test_oncologist_review_uses_tool_call(mock_api_call):
    """validate_guide oncologist call uses tool_choice."""
    mock_api_call.side_effect = [
        _mock_tool_use(GOOD_ONCO_REVIEW),
        _mock_tool_use(GOOD_ADVOCATE_REVIEW),
    ]

    ct = CostTracker()
    validate_guide(
        guide_text="# Guide", diagnosis="RET fusion NSCLC",
        knowledge_map={}, api_key="fake-key", model="claude-sonnet-4-6", cost=ct,
    )

    first_call_kwargs = mock_api_call.call_args_list[0][1]
    assert first_call_kwargs["tool_choice"] == {"type": "tool", "name": "submit_oncologist_review"}


@patch("modules.validation.api_call")
def test_advocate_review_uses_tool_call(mock_api_call):
    """validate_guide advocate call uses tool_choice."""
    mock_api_call.side_effect = [
        _mock_tool_use(GOOD_ONCO_REVIEW),
        _mock_tool_use(GOOD_ADVOCATE_REVIEW),
    ]

    ct = CostTracker()
    validate_guide(
        guide_text="# Guide", diagnosis="RET fusion NSCLC",
        knowledge_map={}, api_key="fake-key", model="claude-sonnet-4-6", cost=ct,
    )

    second_call_kwargs = mock_api_call.call_args_list[1][1]
    assert second_call_kwargs["tool_choice"] == {"type": "tool", "name": "submit_advocate_review"}


@patch("modules.validation.api_call")
def test_validation_passes(mock_api_call):
    mock_api_call.side_effect = [
        _mock_tool_use(GOOD_ONCO_REVIEW),
        _mock_tool_use(GOOD_ADVOCATE_REVIEW),
    ]

    ct = CostTracker()
    result = validate_guide(
        guide_text="# Guide\n\nContent here...",
        diagnosis="RET fusion NSCLC",
        knowledge_map={"approved_drugs": []},
        api_key="fake-key",
        model="claude-sonnet-4-6",
        cost=ct,
    )
    assert result["passed"] is True
    assert result["missing_keywords"] == []


@patch("modules.validation.api_call")
def test_validation_finds_gaps(mock_api_call):
    bad_onco_review = {
        "overall": "NEEDS CORRECTION",
        "accuracy_issues": [{"section": "side-effects", "issue": "Missing hyperglycemia 53%", "severity": "MAJOR"}],
        "missing_data": [],
        "safety_concerns": [],
    }
    bad_advocate_review = {
        "section_scores": {"big-picture": {"score": 9.0, "assessment": "OK"},
                           "pipeline": {"score": 6.0, "assessment": "Incomplete"}},
        "missing_keywords": ["LOXO-260 phase I RET", "hyperglycemia selpercatinib incidence"],
        "overall_score": 7.5,
        "passed": False,
        "learnings": [],
    }
    mock_api_call.side_effect = [
        _mock_tool_use(bad_onco_review),
        _mock_tool_use(bad_advocate_review),
    ]

    ct = CostTracker()
    result = validate_guide(
        guide_text="# Guide\n\nIncomplete content...",
        diagnosis="RET fusion NSCLC",
        knowledge_map={"approved_drugs": []},
        api_key="fake-key",
        model="claude-sonnet-4-6",
        cost=ct,
    )
    assert result["passed"] is False
    assert len(result["missing_keywords"]) > 0
    assert len(result["accuracy_issues"]) > 0


@patch("modules.validation.api_call")
def test_safety_concerns_block_pass(mock_api_call):
    """POTENTIALLY HARMFUL oncologist result forces passed=False."""
    harmful_onco_review = {
        "overall": "POTENTIALLY HARMFUL",
        "accuracy_issues": [],
        "missing_data": [],
        "safety_concerns": [{"section": "treatment-efficacy", "concern": "Dangerous dosing error"}],
    }
    # Advocate passes, but oncologist found harm
    mock_api_call.side_effect = [
        _mock_tool_use(harmful_onco_review),
        _mock_tool_use(GOOD_ADVOCATE_REVIEW),
    ]

    ct = CostTracker()
    result = validate_guide(
        guide_text="# Guide", diagnosis="RET", knowledge_map={},
        api_key="fake-key", model="claude-sonnet-4-6", cost=ct,
    )
    assert result["passed"] is False
    assert len(result["safety_concerns"]) == 1
