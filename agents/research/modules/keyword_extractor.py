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
                        "target_section": {"type": "string"},
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "language": {"type": "string"},
                    },
                    "required": ["query_text", "search_engine", "target_section"],
                },
            },
        },
        "required": ["queries"],
    },
}

SYSTEM_PROMPT = """You are a medical research methodologist expert in information retrieval.

You will receive:
1. A cancer diagnosis
2. A complete discovery conversation between an oncologist and patient advocate
3. A clinical knowledge map with all known drugs, trials, side effects, etc.
4. The 15 guide sections that need data

Your job: extract OPTIMAL search queries to VERIFY and EXPAND on the knowledge discussed.

CRITICAL: The conversation contains CLAIMS (drug names, percentages, trial results).
Your queries must VERIFY these claims against real sources AND find data NOT discussed.

QUERY RULES PER BACKEND:

PubMed (search_engine: "pubmed"):
- Specific drug names + outcomes: "selpercatinib adverse events incidence phase III"
- Trial names: "LIBRETTO-431 progression-free survival"
- Pipeline drugs by code: "LOXO-260 phase I RET"
- Keep under 100 chars

Serper/Google (search_engine: "serper"):
- Natural language, SPECIFIC: drug names, percentages, trial names
- Pipeline: each drug BY NAME
- Access: country-specific: "selpercatinib EMA reimbursement Germany"
- Include some queries in DE, FR, IT, ES for European access
- Patient communities: by name

ClinicalTrials.gov (search_engine: "clinicaltrials"):
- condition + intervention: "RET fusion lung cancer" + drug name
- Focus on RECRUITING trials

OpenFDA (search_engine: "openfda"):
- Generic drug names only

CIViC (search_engine: "civic"):
- Gene names: "RET"

MANDATORY COVERAGE:
- Every drug mentioned (approved + pipeline) MUST have >= 1 query BY NAME
- Every side effect with % MUST have a verification query
- Every landmark trial MUST have a results query
- Pipeline: individual drug queries, NOT generic "RET pipeline"
- Drug withdrawal/market exit status queries

Target: 60-100 queries. Quality over quantity. Precision over breadth.

Use the submit_queries tool to submit your query list."""


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
            q.setdefault("target_section", "general")
            q.setdefault("language", "en")

        logger.info(f"Keyword extraction: {len(queries)} queries from discovery conversation")
        return queries

    except Exception as e:
        logger.error(f"Keyword extraction failed: {e}")
        return []
