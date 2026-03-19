"""Analyze findings coverage per lifecycle stage and generate targeted queries to fill gaps."""

import json
import logging
from typing import Optional

import anthropic

from .cost_tracker import CostTracker

logger = logging.getLogger(__name__)

# v6: Thresholds per lifecycle stage (SPEC Faza 4)
LIFECYCLE_THRESHOLDS = {
    "Q1": 5, "Q2": 15, "Q3": 20, "Q4": 5,
    "Q5": 10, "Q6": 8, "Q7": 5, "Q8": 3,
}

GAP_QUERIES_TOOL = {
    "name": "submit_gap_queries",
    "description": "Submit targeted queries to fill weak lifecycle stages",
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
                        "lifecycle_stage": {"type": "string"},
                        "language": {"type": "string"},
                    },
                    "required": ["query_text", "search_engine", "lifecycle_stage"],
                },
            }
        },
        "required": ["queries"],
    },
}

SYSTEM_PROMPT = """You are a medical research gap analyzer for an oncology patient education blog.

You will receive a topic and coverage per LIFECYCLE STAGE (Q1-Q8).

Lifecycle stages and minimum thresholds (findings with relevance >= 7):
  Q1 Diagnostic: 5
  Q2 Treatment: 15
  Q3 Living with treatment: 20 (largest -- affects daily life)
  Q4 Metastases: 5 per common site
  Q5 Resistance: 10
  Q6 Pipeline: 8
  Q7 Mistakes: 5
  Q8 Community: 3

For each stage BELOW threshold, generate 2-4 highly specific queries.

Query rules:
- "serper": natural language, specific drug/trial names
- "pubmed": MeSH terms for clinical data
- "clinicaltrials": condition + intervention for active trials

DO NOT generate queries for stages that are well-covered.
Use the submit_gap_queries tool. If all stages are covered, submit empty queries array."""


def analyze_gaps(
    topic_title: str,
    findings: list[dict],
    sections: list[dict],
    api_key: str,
    model: str = "claude-haiku-4-5-20251001",
    cost: Optional[CostTracker] = None,
) -> list[dict]:
    """Analyze coverage gaps per lifecycle stage and return targeted queries.

    v6: Uses lifecycle_stage field from findings (populated by enrichment)
    instead of calling Haiku to map findings to sections.

    Returns:
        List of query dicts to execute in round 2, or empty list if no gaps.
    """
    if not findings or not api_key:
        return []

    client = anthropic.Anthropic(api_key=api_key)

    # Step 1: Count findings per lifecycle stage (using lifecycle_stage field)
    stage_counts = {}
    stage_samples = {}
    for i, f in enumerate(findings):
        ls = f.get("lifecycle_stage")
        if not ls:
            continue
        rel = f.get("relevance_score", 0)
        if rel < 7:
            continue  # only count high-quality findings
        stage_counts[ls] = stage_counts.get(ls, 0) + 1
        if ls not in stage_samples:
            stage_samples[ls] = []
        if len(stage_samples[ls]) < 3:
            stage_samples[ls].append(f.get("title_english", "N/A")[:80])

    # Step 2: Build coverage summary
    coverage_lines = []
    weak_stages = []
    for stage, threshold in LIFECYCLE_THRESHOLDS.items():
        count = stage_counts.get(stage, 0)
        samples = stage_samples.get(stage, [])
        status = "OK" if count >= threshold else f"WEAK ({count}/{threshold})"
        samples_text = "\n".join(f"    - {s}" for s in samples) if samples else "    (no samples)"
        coverage_lines.append(f"{stage}: {count} findings (threshold: {threshold}) -- {status}\n{samples_text}")
        if count < threshold:
            weak_stages.append(stage)

    if not weak_stages:
        logger.info("Gap analysis: all lifecycle stages well-covered")
        return []

    coverage_text = "\n\n".join(coverage_lines)

    # Step 3: Ask Claude to generate queries for weak stages
    try:
        message = client.messages.create(
            model=model,
            max_tokens=3000,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"Topic: {topic_title}\n"
                    f"Total findings: {len(findings)}\n"
                    f"Weak stages: {', '.join(weak_stages)}\n\n"
                    f"Coverage per lifecycle stage:\n{coverage_text}"
                ),
            }],
            tools=[GAP_QUERIES_TOOL],
            tool_choice={"type": "tool", "name": "submit_gap_queries"},
        )

        if cost:
            cost.track(model, message.usage.input_tokens, message.usage.output_tokens)
        gap_queries_raw = message.content[0].input["queries"]

        # Normalize field names
        gap_queries = []
        for q in gap_queries_raw:
            normalized = dict(q)
            normalized.setdefault("language", "en")
            normalized.setdefault("lifecycle_stage", "Q3")
            gap_queries.append(normalized)

        if gap_queries:
            gap_stages = set(q.get("lifecycle_stage", "?") for q in gap_queries)
            logger.info(f"Gap analysis: {len(gap_queries)} queries for stages: {gap_stages}")
        else:
            logger.info("Gap analysis: Claude found no gaps to fill")

        return gap_queries

    except Exception as e:
        logger.error(f"Gap analysis failed: {e}. Skipping round 2.")
        return []
