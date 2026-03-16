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
from .utils import load_skill_context

logger = logging.getLogger(__name__)

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_MODULE_DIR, "..", "..", ".."))
SKILLS_DIR = os.path.join(_PROJECT_ROOT, ".claude", "skills")

ONCOLOGIST_REVIEW_SYSTEM = """You are an experienced oncologist reviewing a patient education guide for medical accuracy.

You will receive:
1. The guide text
2. The original clinical knowledge map (what SHOULD be in the guide)

Review EVERY section for:
- Factual accuracy: Are numbers (ORR%, PFS, frequencies) correct per the knowledge map?
- Completeness: Are any drugs, trials, or side effects from the knowledge map MISSING from the guide?
- Safety: Could any statement lead to harmful patient decisions?
- Currency: Are there outdated claims?

Return JSON:
{
  "accuracy_issues": [
    {"section": "section-id", "issue": "description", "severity": "critical|major|minor"}
  ],
  "missing_data": [
    {"section": "section-id", "what_missing": "description"}
  ],
  "safety_concerns": ["any safety issue"],
  "overall": "ACCURATE|NEEDS CORRECTION|POTENTIALLY HARMFUL"
}

Be thorough. A patient will make treatment decisions based on this guide.
Return ONLY valid JSON."""


ADVOCATE_REVIEW_SYSTEM = """You are a patient advocate reviewing a completed guide for YOUR diagnosis.
YOUR LIFE depends on this guide being complete.

Score EACH of the 15 sections 1-10:
- 10 = comprehensive, actionable, specific numbers, nothing missing
- 7 = decent but has gaps a patient would notice
- 5 = surface-level, missing critical information
- 3 = barely useful

For any section scoring below 8.5, identify SPECIFIC missing information as search keywords
that could fill the gaps.

Return JSON:
{
  "section_scores": {
    "section-id": {"score": N, "assessment": "brief reason", "gaps": ["specific gap"]}
  },
  "missing_keywords": ["search query 1 to find missing data", "search query 2"],
  "overall_score": N,
  "passed": true/false,
  "learnings": ["anything learned about this diagnosis that should inform future runs"]
}

Set passed=true ONLY if ALL sections score >= 8.5.
Return ONLY valid JSON."""


def _parse_json(raw: str, label: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"{label}: JSON parse failed: {e}")
        return {}


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
            "missing_keywords": list[str],
            "section_scores": dict,
            "learnings": list[str],
        }
    """
    if not api_key:
        logger.warning("No API key for validation")
        return {"passed": False, "overall_score": 0, "accuracy_issues": [],
                "missing_keywords": [], "section_scores": {}, "learnings": []}

    client = anthropic.Anthropic(api_key=api_key)
    knowledge_text = json.dumps(knowledge_map, indent=2)

    # Oncologist review
    logger.info("Validation: Oncologist reviewing accuracy...")
    onco_skill = load_skill_context(os.path.join(SKILLS_DIR, "oncologist.md"))
    try:
        onco_msg = client.messages.create(
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
        )
        cost.track(model, onco_msg.usage.input_tokens, onco_msg.usage.output_tokens)
        onco_review = _parse_json(onco_msg.content[0].text, "oncologist_review")
    except Exception as e:
        logger.error(f"Oncologist review failed: {e}")
        onco_review = {}

    # Advocate review
    logger.info("Validation: Advocate reviewing completeness...")
    adv_skill = load_skill_context(os.path.join(SKILLS_DIR, "patient-advocate.md"))
    try:
        adv_msg = client.messages.create(
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
        )
        cost.track(model, adv_msg.usage.input_tokens, adv_msg.usage.output_tokens)
        adv_review = _parse_json(adv_msg.content[0].text, "advocate_review")
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
