# modules/validation.py
"""Post-generation validation: oncologist + advocate review the guide.

Returns pass/fail, accuracy issues, and missing keywords for targeted search.
"""

import json
import logging
import os

import anthropic

from .cost_tracker import CostTracker
from .guide_generator import GUIDE_SECTIONS
from .utils import api_call, load_skill_context

logger = logging.getLogger(__name__)

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_MODULE_DIR, "..", "..", ".."))
SKILLS_DIR = os.path.join(_PROJECT_ROOT, ".claude", "skills")

ONCOLOGIST_REVIEW_TOOL = {
    "name": "submit_oncologist_review",
    "description": "Submit medical accuracy review of the patient guide",
    "input_schema": {
        "type": "object",
        "properties": {
            "overall": {
                "type": "string",
                "enum": ["ACCURATE", "NEEDS CORRECTION", "POTENTIALLY HARMFUL"],
            },
            "accuracy_issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string"},
                        "issue": {"type": "string"},
                        "severity": {"type": "string", "enum": ["CRITICAL", "MAJOR", "MINOR"]},
                    },
                    "required": ["section", "issue", "severity"],
                },
            },
            "missing_data": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string"},
                        "what_missing": {"type": "string"},
                    },
                    "required": ["section", "what_missing"],
                },
            },
            "safety_concerns": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string"},
                        "concern": {"type": "string"},
                    },
                    "required": ["section", "concern"],
                },
            },
        },
        "required": ["overall", "accuracy_issues", "missing_data", "safety_concerns"],
    },
}

ADVOCATE_REVIEW_TOOL = {
    "name": "submit_advocate_review",
    "description": "Submit patient-perspective review with section scores",
    "input_schema": {
        "type": "object",
        "properties": {
            "passed": {"type": "boolean"},
            "overall_score": {"type": "number", "minimum": 0, "maximum": 10},
            "section_scores": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "score": {"type": "number"},
                        "assessment": {"type": "string"},
                    },
                    "required": ["score", "assessment"],
                },
            },
            "missing_keywords": {"type": "array", "items": {"type": "string"}},
            "learnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["passed", "overall_score", "section_scores", "missing_keywords", "learnings"],
    },
}

ONCOLOGIST_REVIEW_SYSTEM = """You are an experienced oncologist reviewing a patient education guide for medical accuracy.

You will receive:
1. The guide text
2. The original clinical knowledge map (what SHOULD be in the guide)

Review EVERY section for:
- Factual accuracy: Are numbers (ORR%, PFS, frequencies) correct per the knowledge map?
- Completeness: Are any drugs, trials, or side effects from the knowledge map MISSING from the guide?
- Safety: Could any statement lead to harmful patient decisions?
- Currency: Are there outdated claims?

Use the submit_oncologist_review tool to submit your review.
Be thorough. A patient will make treatment decisions based on this guide."""


ADVOCATE_REVIEW_SYSTEM = """You are a patient advocate reviewing a completed guide for YOUR diagnosis.
YOUR LIFE depends on this guide being complete.

Score EACH of the 15 sections 1-10:
- 10 = comprehensive, actionable, specific numbers, nothing missing
- 7 = decent but has gaps a patient would notice
- 5 = surface-level, missing critical information
- 3 = barely useful

For any section scoring below 8.5, identify SPECIFIC missing information as search keywords
that could fill the gaps.

Use the submit_advocate_review tool to submit your review.
Set passed=true ONLY if ALL sections score >= 8.5."""


def validate_guide(
    guide_text: str,
    diagnosis: str,
    knowledge_map: dict,
    api_key: str,
    model: str,
    cost: CostTracker,
) -> dict:
    """Validate a generated guide using oncologist + advocate review.

    Args:
        guide_text: The full guide markdown text
        diagnosis: The diagnosis string
        knowledge_map: Knowledge map from discovery phase
        api_key: Anthropic API key
        model: Claude model (should be Sonnet)
        cost: CostTracker instance

    Returns:
        {
            "passed": bool,
            "overall_score": float,
            "accuracy_issues": list,
            "safety_concerns": list,
            "missing_keywords": list[str],
            "section_scores": dict,
            "learnings": list[str],
        }
    """
    if not api_key:
        logger.warning("No API key for validation")
        return {"passed": False, "overall_score": 0, "accuracy_issues": [],
                "safety_concerns": [], "missing_keywords": [], "section_scores": {}, "learnings": []}

    client = anthropic.Anthropic(api_key=api_key)
    knowledge_text = json.dumps(knowledge_map, indent=2)

    # Oncologist review
    logger.info("Validation: Oncologist reviewing accuracy...")
    onco_skill = load_skill_context(os.path.join(SKILLS_DIR, "oncologist.md"))
    try:
        onco_msg = api_call(
            client,
            model=model,
            max_tokens=4000,
            system=f"{onco_skill}\n\n{ONCOLOGIST_REVIEW_SYSTEM}",
            messages=[{
                "role": "user",
                "content": (
                    f"Diagnosis: {diagnosis}\n\n"
                    f"=== KNOWLEDGE MAP (ground truth) ===\n{knowledge_text}\n\n"
                    f"=== GUIDE TO REVIEW ===\n{guide_text}"
                ),
            }],
            tools=[ONCOLOGIST_REVIEW_TOOL],
            tool_choice={"type": "tool", "name": "submit_oncologist_review"},
        )
        cost.track(model, onco_msg.usage.input_tokens, onco_msg.usage.output_tokens)
        onco_review = onco_msg.content[0].input

        if onco_review.get("safety_concerns"):
            logger.warning(f"SAFETY CONCERNS in validation: {onco_review['safety_concerns']}")
            print(f"  [SAFETY] {len(onco_review['safety_concerns'])} safety concern(s) found -- see review checklist")

    except Exception as e:
        logger.error(f"Oncologist review failed: {e}")
        onco_review = {}

    # Advocate review
    logger.info("Validation: Advocate reviewing completeness...")
    adv_skill = load_skill_context(os.path.join(SKILLS_DIR, "patient-advocate.md"))
    try:
        adv_msg = api_call(
            client,
            model=model,
            max_tokens=6000,
            system=f"{adv_skill}\n\n{ADVOCATE_REVIEW_SYSTEM}",
            messages=[{
                "role": "user",
                "content": (
                    f"Diagnosis: {diagnosis}\n\n"
                    f"=== GUIDE TO REVIEW ===\n{guide_text}"
                ),
            }],
            tools=[ADVOCATE_REVIEW_TOOL],
            tool_choice={"type": "tool", "name": "submit_advocate_review"},
        )
        cost.track(model, adv_msg.usage.input_tokens, adv_msg.usage.output_tokens)
        adv_review = adv_msg.content[0].input
    except Exception as e:
        logger.error(f"Advocate review failed: {e}")
        adv_review = {}

    # Combine results
    passed = adv_review.get("passed", False)
    if onco_review.get("overall") == "POTENTIALLY HARMFUL":
        passed = False

    return {
        "passed": passed,
        "overall_score": adv_review.get("overall_score", 0),
        "accuracy_issues": onco_review.get("accuracy_issues", []) + onco_review.get("missing_data", []),
        "safety_concerns": onco_review.get("safety_concerns", []),
        "missing_keywords": adv_review.get("missing_keywords", []),
        "section_scores": adv_review.get("section_scores", {}),
        "learnings": adv_review.get("learnings", []),
    }
