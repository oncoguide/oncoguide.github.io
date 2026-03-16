"""Expand base search queries using Claude to generate section-targeted queries."""

import json
import logging

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a medical research query generator for an oncology patient education blog.

You will receive:
1. A topic title and base search queries
2. A list of 15 guide sections, each with a description of what information it needs

Your job: generate search queries that will find the SPECIFIC data each section needs.

For EACH section, generate 2-4 targeted queries. Also generate 3-5 general queries for broad coverage.

Query rules per search backend:
- "serper": natural language Google queries (English). Be SPECIFIC: drug names, trial names, percentages, mechanisms.
- "pubmed": MeSH terms and structured PubMed queries
- "clinicaltrials": condition and intervention terms for ClinicalTrials.gov
- "openfda": drug generic names for FDA adverse events and label searches
- "civic": gene names, variant names for CIViC genomics database

Also include 3-5 multilingual queries (de, fr, it, es) for the European access section.

CRITICAL: Generate queries that will find:
- Exact response rates, survival data, trial names (for treatment-efficacy)
- Specific drug interactions, CYP metabolism, food effects (for interactions)
- Real adverse event frequencies with percentages (for side-effects)
- Named clinical trials recruiting NOW, next-gen drug names (for pipeline)
- EMA approval dates, ESMO guidelines, reimbursement status (for european-access)
- Patient communities, support organizations by name (for daily-life)
- Prescribing information, dosing, administration rules (for how-to-take)

Return a JSON array of objects: {"query_text": "...", "search_engine": "serper|pubmed|clinicaltrials|openfda|civic", "language": "en|de|fr|it|es", "target_section": "section-id or general"}

Target: 50-80 total queries.
Return ONLY the JSON array, no other text."""


def expand_queries(
    topic_title: str,
    base_queries: list[str],
    api_key: str,
    model: str = "claude-haiku-4-5-20251001",
    guide_sections: list[dict] | None = None,
) -> list[dict]:
    """Expand base queries into section-targeted queries for all search backends.

    Args:
        topic_title: The topic being researched
        base_queries: 3-5 base queries from registry.yaml
        api_key: Anthropic API key
        model: Claude model to use
        guide_sections: List of guide section dicts with id, title, description.
            If provided, generates section-targeted queries for deeper coverage.

    Returns list of {query_text, search_engine, language, target_section}.
    Base queries are always included as serper/en even if expansion fails.
    """
    # Always include base queries as serper/en
    base = [
        {"query_text": q, "search_engine": "serper", "language": "en", "target_section": "general"}
        for q in base_queries
    ]

    if not api_key:
        logger.warning("No API key for query expansion, returning base queries only")
        return base

    try:
        client = anthropic.Anthropic(api_key=api_key)

        # Build sections context if provided
        sections_text = ""
        if guide_sections:
            sections_text = "\n\nGuide sections that need data:\n"
            for s in guide_sections:
                sections_text += f"- {s['id']}: {s['title']} -- {s['description']}\n"

        message = client.messages.create(
            model=model,
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Topic: {topic_title}\n\n"
                        f"Base queries:\n"
                        + "\n".join(f"- {q}" for q in base_queries)
                        + sections_text
                    ),
                }
            ],
        )
        text = message.content[0].text.strip()
        # Parse JSON, handle markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        expanded = json.loads(text)

        # Normalize: ensure target_section field exists
        for q in expanded:
            if "target_section" not in q:
                q["target_section"] = "general"

        # Merge: base + expanded, dedup by query_text
        seen = set()
        result = []
        for q in base + expanded:
            key = q["query_text"].lower().strip()
            if key not in seen:
                seen.add(key)
                result.append(q)

        logger.info(f"Query expansion: {len(base_queries)} base -> {len(result)} total")
        return result

    except Exception as e:
        logger.error(f"Query expansion failed: {e}. Using base queries only.")
        return base
