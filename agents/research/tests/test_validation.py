import json
import pytest
from unittest.mock import patch, MagicMock, Mock

from modules.validation import validate_guide, refine_guide, _apply_patches
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
    "section_scores": {"understanding-diagnosis": {"score": 9.0, "assessment": "Good"},
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
        "section_scores": {"understanding-diagnosis": {"score": 9.0, "assessment": "OK"},
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
        "safety_concerns": [{"section": "best-treatment", "concern": "Dangerous dosing error"}],
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


# --- refine_guide tests ---

def test_apply_patches_replaces_text():
    text = "Take ibuprofen for pain. Avoid NSAIDs."
    patches = [{"find": "ibuprofen", "replace": "acetaminophen", "severity": "CRITICAL"}]
    result, applied = _apply_patches(text, patches)
    assert "acetaminophen" in result
    assert "ibuprofen" not in result
    assert len(applied) == 1


def test_apply_patches_skips_unfound():
    text = "Some guide content here."
    patches = [{"find": "text not in guide", "replace": "replacement", "severity": "MAJOR"}]
    result, applied = _apply_patches(text, patches)
    assert result == text
    assert len(applied) == 0


@patch("modules.validation.api_call")
def test_refine_guide_fixes_language(mock_api_call):
    """refine_guide applies language patches from Haiku then validates."""
    lang_result = {"issues": [{"find": "CE AI DE FAPT", "replace": "THE BIG PICTURE", "language_detected": "Romanian"}], "is_clean": False}
    mock_api_call.side_effect = [
        _mock_tool_use(lang_result),           # language check (Haiku)
        _mock_tool_use(GOOD_ONCO_REVIEW),      # validate oncologist
        _mock_tool_use(GOOD_ADVOCATE_REVIEW),  # validate advocate
    ]

    ct = CostTracker()
    guide = "## CE AI DE FAPT\nContent here."
    result = refine_guide(
        guide_text=guide, diagnosis="RET fusion NSCLC", knowledge_map={},
        api_key="fake-key", sonnet_model="claude-sonnet-4-6",
        haiku_model="claude-haiku-4-5-20251001", cost=ct,
    )
    assert result["language_issues_found"] == 1
    assert "THE BIG PICTURE" in result["guide_text"]
    assert "CE AI DE FAPT" not in result["guide_text"]
    assert len(result["patches_applied"]) == 1


@patch("modules.validation.api_call")
def test_refine_guide_applies_medical_corrections(mock_api_call):
    """refine_guide applies medical corrections when oncologist finds accuracy issues."""
    lang_clean = {"issues": [], "is_clean": True}
    bad_onco = {
        "overall": "NEEDS CORRECTION",
        "accuracy_issues": [{"section": "treatment", "issue": "Wrong drug", "severity": "CRITICAL"}],
        "missing_data": [],
        "safety_concerns": [],
    }
    bad_adv = {**GOOD_ADVOCATE_REVIEW, "passed": False, "overall_score": 6.0}
    med_corrections = {"corrections": [{"find": "ibuprofen", "replace": "acetaminophen", "rationale": "Hepatotoxicity risk", "severity": "CRITICAL"}], "has_corrections": True}

    mock_api_call.side_effect = [
        _mock_tool_use(lang_clean),        # language check round 1
        _mock_tool_use(bad_onco),          # validate oncologist round 1
        _mock_tool_use(bad_adv),           # validate advocate round 1
        _mock_tool_use(med_corrections),   # medical correction
        _mock_tool_use(lang_clean),        # language check round 2
        _mock_tool_use(GOOD_ONCO_REVIEW),  # validate oncologist round 2
        _mock_tool_use(GOOD_ADVOCATE_REVIEW),  # validate advocate round 2
    ]

    ct = CostTracker()
    result = refine_guide(
        guide_text="Take ibuprofen for pain.", diagnosis="RET fusion NSCLC", knowledge_map={},
        api_key="fake-key", sonnet_model="claude-sonnet-4-6",
        haiku_model="claude-haiku-4-5-20251001", cost=ct,
    )
    assert result["medical_corrections_applied"] >= 1
    assert "acetaminophen" in result["guide_text"]


@patch("modules.validation.api_call")
def test_refine_guide_has_backward_compat_keys(mock_api_call):
    """refine_guide result contains all keys from validate_guide plus new keys."""
    lang_clean = {"issues": [], "is_clean": True}
    mock_api_call.side_effect = [
        _mock_tool_use(lang_clean),
        _mock_tool_use(GOOD_ONCO_REVIEW),
        _mock_tool_use(GOOD_ADVOCATE_REVIEW),
    ]

    ct = CostTracker()
    result = refine_guide(
        guide_text="# Guide", diagnosis="RET fusion NSCLC", knowledge_map={},
        api_key="fake-key", sonnet_model="claude-sonnet-4-6",
        haiku_model="claude-haiku-4-5-20251001", cost=ct,
    )
    # Original validate_guide keys
    for key in ("passed", "overall_score", "accuracy_issues", "safety_concerns",
                "missing_keywords", "section_scores", "learnings"):
        assert key in result, f"Missing key: {key}"
    # New refine_guide keys
    for key in ("guide_text", "patches_applied", "language_issues_found",
                "medical_corrections_applied", "rounds_completed"):
        assert key in result, f"Missing refine key: {key}"
