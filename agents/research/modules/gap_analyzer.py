"""Analyze findings coverage per guide section and generate targeted queries to fill gaps."""

import json
import logging

import anthropic

logger = logging.getLogger(__name__)

SECTION_MAP_TOOL = {
    "name": "submit_section_map",
    "description": "Map guide section IDs to relevant finding indices",
    "input_schema": {
        "type": "object",
        "properties": {
            "section_map": {
                "type": "object",
                "description": "Keys are section IDs, values are arrays of finding indices",
                "additionalProperties": {"type": "array", "items": {"type": "integer"}},
            }
        },
        "required": ["section_map"],
    },
}

GAP_QUERIES_TOOL = {
    "name": "submit_gap_queries",
    "description": "Submit targeted queries to fill weak guide sections",
    "input_schema": {
        "type": "object",
        "properties": {
            "queries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "query_text": {"type": "string"},
                        "search_engine": {"type": "string"},
                        "section_id": {"type": "string"},
                        "language": {"type": "string"},
                    },
                    "required": ["query_text", "search_engine", "section_id"],
                },
            }
        },
        "required": ["queries"],
    },
}

SYSTEM_PROMPT = """You are a medical research gap analyzer for an oncology patient education blog.

You will receive:
1. A topic title
2. A list of 15 guide sections with descriptions
3. For each section, the findings currently assigned to it (title + score)

Your job: identify sections with INSUFFICIENT data and generate targeted search queries to fill the gaps.

A section is WEAK if:
- It has fewer than 5 findings
- Its findings are low-scored (mostly below 7/10)
- Its findings don't cover the specific data described in the section description
  (e.g., "side effects" section needs percentage frequencies, not just general articles)

For each weak section, generate 2-4 highly specific queries designed to find the MISSING data.

Query rules:
- "serper": Google queries in English, very specific (drug names, exact data types, trial names)
- "pubmed": MeSH terms for clinical data
- "clinicaltrials": condition + intervention for active trials

DO NOT generate queries for sections that are already well-covered (10+ good findings).

Use the submit_gap_queries tool. If ALL sections are well-covered, submit an empty queries array."""


def _map_findings_to_sections(
    findings: list[dict], sections: list[dict],
    client: anthropic.Anthropic, model: str,
) -> dict:
    """Quick mapping of existing findings to sections for gap analysis."""
    finding_summaries = []
    for i, f in enumerate(findings[:500], 1):
        finding_summaries.append(
            f"[{i}] (Score {f.get('relevance_score', '?')}) {f.get('title_english', 'N/A')}"
        )
    findings_text = "\n".join(finding_summaries)

    sections_json = json.dumps(
        [{"id": s["id"], "title": s["title"], "description": s["description"]}
         for s in sections],
        indent=2,
    )

    message = client.messages.create(
        model=model,
        max_tokens=4000,
        system="Map findings to guide sections. Use the submit_section_map tool. "
               "Keys are section IDs, values are arrays of finding numbers most relevant "
               "to that section. Be thorough but fast -- use titles and scores to judge relevance.",
        messages=[{
            "role": "user",
            "content": (
                f"Sections:\n{sections_json}\n\n"
                f"Findings:\n{findings_text}"
            ),
        }],
        tools=[SECTION_MAP_TOOL],
        tool_choice={"type": "tool", "name": "submit_section_map"},
    )

    return message.content[0].input["section_map"]


def analyze_gaps(
    topic_title: str,
    findings: list[dict],
    sections: list[dict],
    api_key: str,
    model: str = "claude-haiku-4-5-20251001",
) -> list[dict]:
    """Analyze coverage gaps and return targeted queries to fill them.

    Args:
        topic_title: The topic being researched
        findings: All findings collected so far
        sections: Guide sections (from GUIDE_SECTIONS)
        api_key: Anthropic API key
        model: Claude model for analysis

    Returns:
        List of query dicts to execute in round 2, or empty list if no gaps.
    """
    if not findings or not api_key:
        return []

    client = anthropic.Anthropic(api_key=api_key)

    # Step 1: Map findings to sections
    section_map = _map_findings_to_sections(findings, sections, client, model)

    # Step 2: Build coverage summary for gap analyzer
    coverage_lines = []
    for s in sections:
        mapped_ids = section_map.get(s["id"], [])
        count = len(mapped_ids)
        if count > 0 and mapped_ids:
            sample_titles = []
            for fid in mapped_ids[:5]:
                if 1 <= fid <= len(findings):
                    f = findings[fid - 1]
                    score = f.get("relevance_score", "?")
                    title = f.get("title_english", "N/A")[:80]
                    sample_titles.append(f"    [{fid}] (Score {score}) {title}")
            titles_text = "\n".join(sample_titles)
            coverage_lines.append(
                f"Section '{s['id']}' ({s['title']}): {count} findings\n"
                f"  Description: {s['description']}\n"
                f"  Sample findings:\n{titles_text}"
            )
        else:
            coverage_lines.append(
                f"Section '{s['id']}' ({s['title']}): 0 findings\n"
                f"  Description: {s['description']}\n"
                f"  ** NO DATA -- CRITICAL GAP **"
            )

    coverage_text = "\n\n".join(coverage_lines)

    # Step 3: Ask Claude to identify gaps and generate queries
    try:
        message = client.messages.create(
            model=model,
            max_tokens=3000,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"Topic: {topic_title}\n"
                    f"Total findings: {len(findings)}\n\n"
                    f"Coverage per section:\n{coverage_text}"
                ),
            }],
            tools=[GAP_QUERIES_TOOL],
            tool_choice={"type": "tool", "name": "submit_gap_queries"},
        )

        gap_queries_raw = message.content[0].input["queries"]

        # Normalize field names (section_id -> target_section for downstream compatibility)
        gap_queries = []
        for q in gap_queries_raw:
            normalized = dict(q)
            if "section_id" in normalized and "target_section" not in normalized:
                normalized["target_section"] = normalized.pop("section_id")
            normalized.setdefault("language", "en")
            gap_queries.append(normalized)

        if gap_queries:
            gap_sections = set(q.get("target_section", "?") for q in gap_queries)
            logger.info(f"Gap analysis: {len(gap_queries)} queries for sections: {gap_sections}")
        else:
            logger.info("Gap analysis: all sections well-covered")

        return gap_queries

    except Exception as e:
        logger.error(f"Gap analysis failed: {e}. Skipping round 2.")
        return []
