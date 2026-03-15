import json
import pytest
from unittest.mock import patch, MagicMock

from modules.validation import validate_guide


def _mock_message(text):
    return MagicMock(
        content=[MagicMock(text=text)],
        usage=MagicMock(input_tokens=3000, output_tokens=2000),
    )


@patch("modules.validation.anthropic.Anthropic")
def test_validation_passes(mock_cls):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    oncologist_review = {
        "accuracy_issues": [],
        "overall": "ACCURATE",
    }
    advocate_review = {
        "section_scores": {"big-picture": {"score": 9.0}, "pipeline": {"score": 9.0}},
        "missing_keywords": [],
        "overall_score": 9.0,
        "passed": True,
    }
    mock_client.messages.create.side_effect = [
        _mock_message(json.dumps(oncologist_review)),
        _mock_message(json.dumps(advocate_review)),
    ]

    from modules.cost_tracker import CostTracker
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


@patch("modules.validation.anthropic.Anthropic")
def test_validation_finds_gaps(mock_cls):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    oncologist_review = {
        "accuracy_issues": [{"section": "side-effects", "issue": "Missing hyperglycemia 53%"}],
        "overall": "NEEDS CORRECTION",
    }
    advocate_review = {
        "section_scores": {"big-picture": {"score": 9.0}, "pipeline": {"score": 6.0}},
        "missing_keywords": ["LOXO-260 phase I RET", "hyperglycemia selpercatinib incidence"],
        "overall_score": 7.5,
        "passed": False,
    }
    mock_client.messages.create.side_effect = [
        _mock_message(json.dumps(oncologist_review)),
        _mock_message(json.dumps(advocate_review)),
    ]

    from modules.cost_tracker import CostTracker
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
