"""Extract precision search queries from oncologist<->advocate discovery conversation.

The methodologist agent reads the entire conversation and converts it into
optimized search queries per backend (PubMed, Serper, ClinicalTrials, etc.).
"""

import json
import logging

import anthropic

from .cost_tracker import CostTracker
from .guide_generator import GUIDE_SECTIONS
from .utils import api_call

logger = logging.getLogger(__name__)

KEYWORD_TOOL = {
    "name": "submit_queries",
    "description": "Submit precision search queries extracted from discovery conversation",
    "input_schema": {
        "type": "object",
        "properties": {
            "queries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "query_text": {"type": "string"},
                        "search_engine": {
                            "type": "string",
                            "enum": ["pubmed", "serper", "clinicaltrials", "openfda", "civic"],
                        },
                        "lifecycle_stage": {
                            "type": "string",
                            "enum": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9"],
                            "description": "Which patient lifecycle question this query serves",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "language": {"type": "string"},
                    },
                    "required": ["query_text", "search_engine", "lifecycle_stage"],
                },
            },
        },
        "required": ["queries"],
    },
}

# v6: Minimum queries per lifecycle stage (SPEC Faza 2)
LIFECYCLE_MINIMUMS = {
    "Q1": 5, "Q2": 10, "Q3": 20, "Q4": 8, "Q5": 10,
    "Q6": 12, "Q7": 5, "Q8": 4, "Q9": 5,
}

SYSTEM_PROMPT = """You are a medical research methodologist expert in information retrieval.

You will receive:
1. A cancer diagnosis
2. A complete discovery conversation between an oncologist and patient advocate
3. A Q1-Q8 lifecycle knowledge map
4. The 16 guide sections that need data

Your job: extract OPTIMAL search queries organized by LIFECYCLE STAGE (Q1-Q9).
Each query MUST have a lifecycle_stage tag.

LIFECYCLE STAGES AND MINIMUM QUERIES:
  Q1 Diagnostic (min 5): molecular tests, staging, subtypes
  Q2 Treatment (min 10): per approved drug x per endpoint (efficacy, safety, comparison)
  Q3 Living with treatment (min 20): per drug CYP, side effects, interactions, monitoring + nutrition, exercise, emergencies, access
  Q4 Metastases (min 8): per common metastasis site
  Q5 Resistance (min 10): per mechanism + per next-line drug
  Q6 Pipeline (min 12): per named pipeline drug + per modality (ADC, PROTAC, etc.)
  Q7 Mistakes (min 5): dangerous interactions, myths, common errors
  Q8 Community (min 4): forums, patient stories, caregiver, organizations
  Q9 Geographic access (min 5): per country/region, legal access mechanisms

QUERY RULES PER BACKEND:

PubMed (search_engine: "pubmed"):
- Specific drug names + outcomes. Keep under 100 chars.

Serper (search_engine: "serper"):
- Natural language, SPECIFIC. Include queries in DE, FR, IT, ES, RO for European access (Q9).
- Key Q2, Q3, Q5 queries should be translated to 6+ languages.

ClinicalTrials.gov (search_engine: "clinicaltrials"):
- condition + intervention for each approved and pipeline drug.

OpenFDA (search_engine: "openfda"):
- Per approved drug: adverse_events, label.

CIViC (search_engine: "civic"):
- Per gene: RESISTANCE + PREDICTIVE evidence.

MANDATORY: Every NAMED ENTITY from discovery (drug, trial, mutation) must have >= 1 dedicated query.

Target: 100-170 queries. Every lifecycle stage must meet its minimum.

Use the submit_queries tool."""


def extract_queries(
    diagnosis: str,
    conversation: list[str],
    knowledge_map: dict,
    api_key: str,
    model: str,
    cost: CostTracker,
) -> list[dict]:
    """Extract precision search queries from discovery conversation.

    Args:
        diagnosis: The diagnosis string
        conversation: Full oncologist<->advocate conversation transcript
        knowledge_map: Final merged knowledge map from discovery
        api_key: Anthropic API key
        model: Claude model (should be Sonnet for quality)
        cost: CostTracker instance

    Returns:
        List of query dicts with query_text, search_engine, language, target_section
    """
    if not api_key:
        logger.warning("No API key for keyword extraction")
        return []

    sections_text = "\n".join(
        f"- {s['id']}: {s['title']} -- {s['description']}"
        for s in GUIDE_SECTIONS
    )

    conversation_text = "\n\n---\n\n".join(conversation)
    knowledge_text = json.dumps(knowledge_map, indent=2)

    client = anthropic.Anthropic(api_key=api_key)

    try:
        message = api_call(
            client,
            model=model,
            max_tokens=12000,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"Diagnosis: {diagnosis}\n\n"
                    f"=== DISCOVERY CONVERSATION ===\n{conversation_text}\n\n"
                    f"=== FINAL KNOWLEDGE MAP ===\n{knowledge_text}\n\n"
                    f"=== GUIDE SECTIONS ===\n{sections_text}"
                ),
            }],
            tools=[KEYWORD_TOOL],
            tool_choice={"type": "tool", "name": "submit_queries"},
        )
        cost.track(model, message.usage.input_tokens, message.usage.output_tokens)

        queries = message.content[0].input["queries"]

        # Normalize defaults
        for q in queries:
            q.setdefault("lifecycle_stage", "Q3")  # default to largest stage
            q.setdefault("language", "en")
            # backward compat: set target_section from lifecycle_stage
            if "target_section" not in q:
                q["target_section"] = q["lifecycle_stage"]

        # Log per-stage distribution
        stage_counts = {}
        for q in queries:
            ls = q.get("lifecycle_stage", "?")
            stage_counts[ls] = stage_counts.get(ls, 0) + 1
        logger.info(f"Keyword extraction: {len(queries)} queries. Distribution: {stage_counts}")

        # Warn if any stage is below minimum
        for stage, minimum in LIFECYCLE_MINIMUMS.items():
            actual = stage_counts.get(stage, 0)
            if actual < minimum:
                logger.warning(f"  GATE 2: {stage} has {actual} queries (min {minimum})")

        return queries

    except Exception as e:
        logger.error(f"Keyword extraction failed: {e}")
        return []
