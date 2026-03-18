# modules/validation.py
"""Post-generation validation: 6-layer quality assurance pipeline.

Layers: structural QA -> brief adherence -> language -> consistency -> medical -> advocate.
"""

import json
import logging
import os
import re

import anthropic

from .cost_tracker import CostTracker
from .guide_generator import GUIDE_SECTIONS, SECTION_BRIEFS, CRITICAL_SECTIONS
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

LANGUAGE_CHECK_TOOL = {
    "name": "submit_language_issues",
    "description": "Submit list of non-English text found in the guide",
    "input_schema": {
        "type": "object",
        "properties": {
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "find": {"type": "string", "description": "Verbatim text to replace (exact copy from guide)"},
                        "replace": {"type": "string", "description": "English replacement text"},
                        "language_detected": {"type": "string", "description": "Language name, e.g. Romanian"},
                    },
                    "required": ["find", "replace", "language_detected"],
                },
            },
            "is_clean": {"type": "boolean", "description": "True if no non-English text found"},
        },
        "required": ["issues", "is_clean"],
    },
}

MEDICAL_CORRECTION_TOOL = {
    "name": "submit_medical_corrections",
    "description": "Submit surgical find/replace corrections for medical accuracy issues",
    "input_schema": {
        "type": "object",
        "properties": {
            "corrections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "find": {"type": "string", "description": "Verbatim text from guide (50-300 chars)"},
                        "replace": {"type": "string", "description": "Corrected version"},
                        "rationale": {"type": "string", "description": "Why this correction is needed"},
                        "severity": {"type": "string", "enum": ["CRITICAL", "MAJOR", "MINOR"]},
                    },
                    "required": ["find", "replace", "rationale", "severity"],
                },
            },
            "has_corrections": {"type": "boolean"},
        },
        "required": ["corrections", "has_corrections"],
    },
}

LANGUAGE_CHECK_SYSTEM = """You are a language quality checker for a medical guide that MUST be entirely in English.

Scan the guide for ANY text that is not English. This includes:
- Romanian words or phrases (e.g., "CE AI DE FAPT", "Ghid complet", section titles in Romanian)
- French, German, Italian, Spanish, or any other non-English language
- Mixed-language sentences or headings

For each non-English fragment found, provide:
1. The EXACT verbatim text from the guide (copy precisely)
2. An English replacement

Use the submit_language_issues tool. Set is_clean=true ONLY if you found zero non-English text."""

MEDICAL_CORRECTION_SYSTEM = """You are a senior oncologist correcting medical accuracy issues in a patient guide.

You will receive:
1. The relevant sections of the guide
2. A list of specific accuracy issues identified by peer review

For each issue, produce a surgical find/replace patch:
- "find": copy the EXACT verbatim text from the guide (50-300 characters, enough context to be unique)
- "replace": the corrected version with accurate medical information
- Keep replacements minimal -- change only what is wrong, preserve surrounding text

Use the submit_medical_corrections tool. Only create corrections for issues you can verify and fix accurately.
Do NOT invent corrections for issues you are uncertain about."""

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

Score EACH of the 16 sections 1-10:
- 10 = comprehensive, actionable, specific numbers, nothing missing
- 7 = decent but has gaps a patient would notice
- 5 = surface-level, missing critical information
- 3 = barely useful

For any section scoring below 8.5, identify SPECIFIC missing information as search keywords
that could fill the gaps.

Use the submit_advocate_review tool to submit your review.
Set passed=true ONLY if ALL sections score >= 8.5."""


# ── v6: Layer 1 -- Structural QA (zero AI cost) ─────────────────────

# Emoji pattern
_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF]+",
    flags=re.UNICODE,
)


def structural_qa(guide_text: str) -> dict:
    """Layer 1: Structural QA -- zero AI cost, pure Python checks.

    Returns: {"blocks": [...], "warnings": [...]}
    BLOCK = must fix before proceeding. WARN = noted in review.
    """
    blocks = []
    warnings = []

    # Parse sections
    sections_found = re.findall(r'^## .+', guide_text, re.MULTILINE)
    section_ids_found = set()
    for heading in sections_found:
        # Extract section id from heading like "## 1. WHAT YOU HAVE..."
        for gs in GUIDE_SECTIONS:
            if gs["title"].split("--")[0].strip().upper()[:20] in heading.upper():
                section_ids_found.add(gs["id"])

    # Check: all 16 sections + executive summary present
    has_exec = "BEFORE ANYTHING ELSE" in guide_text or "INAINTE DE TOATE" in guide_text
    if not has_exec:
        blocks.append("Missing executive summary (BEFORE ANYTHING ELSE)")

    # Count ## headings (rough section count)
    section_count = len(sections_found)
    if section_count < 16:
        blocks.append(f"Only {section_count} sections found (need 16 + executive summary)")

    # Check section word counts
    parts = re.split(r'^## ', guide_text, flags=re.MULTILINE)
    for part in parts[1:]:  # skip header
        lines = part.split("\n")
        title = lines[0].strip() if lines else ""
        body = "\n".join(lines[1:])
        word_count = len(body.split())

        # Executive summary has different limits (100-250 words per SPEC 10.4)
        is_exec = "BEFORE ANYTHING" in title.upper() or "INAINTE DE TOATE" in title.upper()
        if is_exec:
            if word_count > 250:
                warnings.append(f"Executive summary too long: {word_count} words (max 250)")
            continue  # no minimum check for exec summary

        # Check if this is a critical section
        is_critical = any(cs in title.lower() for cs in ["mistake", "side effect", "emergency", "er --", "resistance", "stops working"])
        min_words = 500 if is_critical else 200

        if word_count < min_words:
            blocks.append(f"Section '{title[:50]}' too short: {word_count} words (min {min_words})")

    # Required tables (sections 2, 5, 6, 7, 11)
    table_sections = ["BEST TREATMENT", "SIDE EFFECT", "INTERACTION", "MONITORING", "PIPELINE"]
    for ts in table_sections:
        # Find the section and check for table markers
        pattern = re.compile(rf'^## .*{ts}.*?(?=^## |\Z)', re.MULTILINE | re.DOTALL | re.IGNORECASE)
        match = pattern.search(guide_text)
        if match and "|" not in match.group():
            warnings.append(f"Section matching '{ts}' has no table (| delimiter)")

    # Section 8 (emergency) needs checkboxes
    emergency_pattern = re.compile(r'^## .*(?:EMERGENCY|URGENTE|ER --).*?(?=^## |\Z)', re.MULTILINE | re.DOTALL | re.IGNORECASE)
    em_match = emergency_pattern.search(guide_text)
    if em_match:
        checkbox_count = em_match.group().count("- [ ]")
        if checkbox_count < 5:
            blocks.append(f"Emergency section has {checkbox_count} checkboxes (need >= 5)")

    # No emojis
    if _EMOJI_RE.search(guide_text):
        blocks.append("Guide contains emojis (forbidden)")

    # No curly quotes
    if "\u201c" in guide_text or "\u201d" in guide_text or "\u2018" in guide_text or "\u2019" in guide_text:
        blocks.append("Guide contains typographic/curly quotes (use straight quotes)")

    # No em-dashes
    if "\u2014" in guide_text:
        blocks.append("Guide contains em-dashes (use double hyphens --)")

    # Paragraph check (warn if any > 5 lines)
    for para in guide_text.split("\n\n"):
        lines = [l for l in para.split("\n") if l.strip() and not l.startswith("|") and not l.startswith("#")]
        if len(lines) > 5:
            warnings.append(f"Long paragraph ({len(lines)} lines): {lines[0][:60]}...")
            break  # only report first

    return {"blocks": blocks, "warnings": warnings}


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


def _apply_patches(guide_text: str, patches: list) -> tuple:
    """Apply find/replace patches to guide text. Returns (updated_text, list_of_applied_descriptions)."""
    applied = []
    for patch in patches:
        find = patch.get("find", "")
        replace = patch.get("replace", "")
        if find and replace and find != replace and find in guide_text:
            guide_text = guide_text.replace(find, replace, 1)
            severity = patch.get("severity", patch.get("language_detected", "?"))
            applied.append(f"[{severity}] {find[:60]}...")
        elif find and find not in guide_text:
            logger.warning(f"Patch not applied -- text not found: {find[:80]!r}")
    return guide_text, applied


def _extract_issue_sections(guide_text: str, accuracy_issues: list) -> str:
    """Extract only the guide sections referenced by accuracy issues (reduces Sonnet input tokens)."""
    if not accuracy_issues:
        return guide_text

    mentioned_sections = {issue.get("section", "") for issue in accuracy_issues if issue.get("section")}
    if not mentioned_sections:
        return guide_text

    lines = guide_text.split("\n")
    selected = []
    in_section = False
    current_section_name = ""

    for line in lines:
        if line.startswith("## "):
            current_section_name = line.lower()
            in_section = any(sec.lower() in current_section_name for sec in mentioned_sections)
        if in_section or line.startswith("# "):
            selected.append(line)

    return "\n".join(selected) if selected else guide_text


def _check_language(guide_text: str, api_key: str, haiku_model: str, cost: CostTracker) -> list:
    """Use Haiku to find non-English text. Returns list of patch dicts."""
    client = anthropic.Anthropic(api_key=api_key)
    try:
        msg = api_call(
            client,
            model=haiku_model,
            max_tokens=2000,
            system=LANGUAGE_CHECK_SYSTEM,
            messages=[{"role": "user", "content": f"Scan this guide for non-English text:\n\n{guide_text}"}],
            tools=[LANGUAGE_CHECK_TOOL],
            tool_choice={"type": "tool", "name": "submit_language_issues"},
        )
        cost.track(haiku_model, msg.usage.input_tokens, msg.usage.output_tokens)
        result = msg.content[0].input
        issues = result.get("issues", [])
        if issues:
            logger.info(f"Language check: {len(issues)} non-English fragment(s) found")
        else:
            logger.info("Language check: guide is clean (English only)")
        return issues
    except Exception as e:
        logger.error(f"Language check failed: {e}")
        return []


def _correct_medical_errors(
    guide_text: str,
    diagnosis: str,
    knowledge_map: dict,
    accuracy_issues: list,
    api_key: str,
    sonnet_model: str,
    cost: CostTracker,
) -> list:
    """Use Sonnet to convert accuracy issues into surgical find/replace patches."""
    client = anthropic.Anthropic(api_key=api_key)
    relevant_sections = _extract_issue_sections(guide_text, accuracy_issues)
    issues_text = json.dumps(accuracy_issues, indent=2)
    knowledge_text = json.dumps(knowledge_map, indent=2)

    try:
        msg = api_call(
            client,
            model=sonnet_model,
            max_tokens=3000,
            system=MEDICAL_CORRECTION_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Diagnosis: {diagnosis}\n\n"
                    f"=== KNOWLEDGE MAP (ground truth) ===\n{knowledge_text}\n\n"
                    f"=== ACCURACY ISSUES TO CORRECT ===\n{issues_text}\n\n"
                    f"=== RELEVANT GUIDE SECTIONS ===\n{relevant_sections}"
                ),
            }],
            tools=[MEDICAL_CORRECTION_TOOL],
            tool_choice={"type": "tool", "name": "submit_medical_corrections"},
        )
        cost.track(sonnet_model, msg.usage.input_tokens, msg.usage.output_tokens)
        result = msg.content[0].input
        corrections = result.get("corrections", [])
        if corrections:
            logger.info(f"Medical corrections: {len(corrections)} patch(es) generated")
        return corrections
    except Exception as e:
        logger.error(f"Medical correction failed: {e}")
        return []


def refine_guide(
    guide_text: str,
    diagnosis: str,
    knowledge_map: dict,
    api_key: str,
    sonnet_model: str,
    haiku_model: str,
    cost: CostTracker,
    max_rounds: int = 2,
) -> dict:
    """Validate + auto-correct guide: language check (Haiku) + medical corrections (Sonnet).

    Wraps validate_guide() with automated correction loops. Returns a superset of
    validate_guide() result, plus: guide_text, patches_applied, language_issues_found,
    medical_corrections_applied, rounds_completed.
    """
    all_patches_applied = []
    language_issues_found = 0
    medical_corrections_applied = 0
    sq = {"blocks": [], "warnings": []}

    for round_num in range(1, max_rounds + 1):
        logger.info(f"refine_guide: round {round_num}/{max_rounds}")

        # Layer 1: Structural QA (zero cost)
        sq = structural_qa(guide_text)
        if sq["blocks"]:
            logger.warning(f"  Layer 1 BLOCKS: {sq['blocks']}")
            # Auto-fix: emojis, curly quotes, em-dashes
            guide_text = _EMOJI_RE.sub("", guide_text)
            guide_text = guide_text.replace("\u201c", '"').replace("\u201d", '"')
            guide_text = guide_text.replace("\u2018", "'").replace("\u2019", "'")
            guide_text = guide_text.replace("\u2014", "--")
        if sq["warnings"]:
            logger.info(f"  Layer 1 warnings: {sq['warnings']}")

        # Layer 2: Language check (Haiku, cheap)
        lang_patches = _check_language(guide_text, api_key, haiku_model, cost)
        if lang_patches:
            language_issues_found += len(lang_patches)
            guide_text, applied = _apply_patches(guide_text, lang_patches)
            all_patches_applied.extend(applied)
            logger.info(f"  Applied {len(applied)} language patch(es)")

        # Layer 4+5: Validate (oncologist + advocate)
        val_result = validate_guide(guide_text, diagnosis, knowledge_map, api_key, sonnet_model, cost)
        logger.info(f"  Validation: score={val_result.get('overall_score', '?')}, passed={val_result['passed']}")

        accuracy_issues = val_result.get("accuracy_issues", [])

        # If clean, stop early
        if val_result["passed"] and not accuracy_issues and not lang_patches:
            logger.info("  Guide is clean -- stopping refinement")
            val_result.update({
                "guide_text": guide_text,
                "patches_applied": all_patches_applied,
                "language_issues_found": language_issues_found,
                "medical_corrections_applied": medical_corrections_applied,
                "rounds_completed": round_num,
            })
            return val_result

        # Medical corrections (Sonnet, more expensive)
        if accuracy_issues and cost.has_budget(reserve_usd=0.25):
            med_patches = _correct_medical_errors(
                guide_text, diagnosis, knowledge_map, accuracy_issues, api_key, sonnet_model, cost
            )
            if med_patches:
                medical_corrections_applied += len(med_patches)
                guide_text, applied = _apply_patches(guide_text, med_patches)
                all_patches_applied.extend(applied)
                logger.info(f"  Applied {len(applied)} medical correction(s)")
            else:
                # No patches generated -- no point continuing
                break
        else:
            break

    val_result.update({
        "guide_text": guide_text,
        "patches_applied": all_patches_applied,
        "language_issues_found": language_issues_found,
        "medical_corrections_applied": medical_corrections_applied,
        "rounds_completed": max_rounds,
        "structural_blocks": sq.get("blocks", []),
        "structural_warnings": sq.get("warnings", []),
    })
    return val_result
