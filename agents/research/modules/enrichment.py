"""Enrich search findings using Claude -- classify relevance and score."""

import logging
import time
from typing import Optional

import anthropic

from .cost_tracker import CostTracker

logger = logging.getLogger(__name__)

ENRICHMENT_TOOL = {
    "name": "submit_enrichment",
    "description": "Submit relevance, authority, and lifecycle stage assessment for a medical finding",
    "input_schema": {
        "type": "object",
        "properties": {
            "relevant": {"type": "boolean"},
            "relevance_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "authority_score": {"type": "integer", "minimum": 1, "maximum": 5},
            "lifecycle_stage": {
                "type": "string",
                "enum": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9"],
                "description": "Patient lifecycle stage: Q1=diagnosis, Q2=treatment, Q3=living, Q4=metastases, Q5=resistance, Q6=pipeline, Q7=mistakes, Q8=community, Q9=access",
            },
            "title_english": {"type": "string"},
            "summary_english": {"type": "string"},
        },
        "required": ["relevant", "relevance_score", "authority_score", "lifecycle_stage", "title_english", "summary_english"],
    },
}

SYSTEM_PROMPT = """You are a medical research classifier for an oncology education blog.
Given a search finding and a research topic, determine:
1. Is this finding relevant to the topic? (true/false)
2. Relevance score (1-10, where 10 = directly addresses the topic with authoritative data)
3. Authority score (1-5) based on source quality:
   5 = Trial published in top journal (NEJM, Lancet, JCO), ESMO/NCCN guideline
   4 = Agency decision (FDA approval, EMA), systematic review
   3 = Peer-reviewed review/meta-analysis, clinical registry (ClinicalTrials.gov)
   2 = Press release, medical news, general database
   1 = Blog, forum, unknown source
4. Lifecycle stage -- which patient question does this finding answer?
   Q1 = Diagnosis (molecular tests, staging, subtypes)
   Q2 = Treatment (approved drugs, guidelines, efficacy)
   Q3 = Living with treatment (dosing, side effects, interactions, monitoring, emergency, daily life, access)
   Q4 = Metastases (common sites, detection, local treatment)
   Q5 = Resistance (mechanisms, next-line options, rebiopsy)
   Q6 = Pipeline (drugs in development, clinical trials, novel modalities)
   Q7 = Mistakes (dangerous interactions, contraindicated supplements, myths)
   Q8 = Community (patient groups, caregiver support)
   Q9 = Geographic access (country-specific access, reimbursement)
5. Title in English (translate if needed)
6. Summary in English (2-3 sentences capturing the key information)

Use the submit_enrichment tool to submit your assessment."""

USER_TEMPLATE = """TOPIC: {topic}

FINDING:
TITLE: {title}
URL: {url}
SNIPPET: {snippet}
SOURCE LANGUAGE: {language}
DATE: {date}"""

# Token tracking (module-level, replaced by CostTracker in Task 11)
_token_usage = {"input": 0, "output": 0}


def get_token_usage() -> dict:
    return dict(_token_usage)


def reset_token_usage():
    _token_usage["input"] = 0
    _token_usage["output"] = 0


def enrich_finding(
    finding: dict,
    topic_title: str,
    api_key: str,
    model: str = "claude-haiku-4-5-20251001",
    cost: Optional[CostTracker] = None,
) -> dict:
    """Classify a single finding. Returns dict with relevant, relevance_score, etc."""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": USER_TEMPLATE.format(
                        topic=topic_title,
                        title=finding.get("title", ""),
                        url=finding.get("url", ""),
                        snippet=finding.get("snippet", ""),
                        language=finding.get("language", "en"),
                        date=finding.get("date", "unknown"),
                    ),
                }
            ],
            tools=[ENRICHMENT_TOOL],
            tool_choice={"type": "tool", "name": "submit_enrichment"},
        )
        _token_usage["input"] += message.usage.input_tokens
        _token_usage["output"] += message.usage.output_tokens
        if cost:
            cost.track(model, message.usage.input_tokens, message.usage.output_tokens)
        return message.content[0].input

    except Exception as e:
        logger.error(f"Enrichment failed for '{finding.get('title', '?')}': {e}")
        return {"relevant": False, "relevance_score": 0, "authority_score": 0,
                "title_english": "", "summary_english": ""}


def enrich_batch(
    findings: list[dict],
    topic_title: str,
    api_key: str,
    model: str = "claude-haiku-4-5-20251001",
    delay: float = 0.3,
    progress_callback=None,
    cost: Optional[CostTracker] = None,
) -> list[dict]:
    """Enrich a batch of findings. Returns list of enrichment results."""
    results = []
    for i, finding in enumerate(findings):
        result = enrich_finding(finding, topic_title, api_key, model, cost=cost)
        results.append(result)
        if progress_callback:
            progress_callback(i + 1, len(findings))
        if delay > 0 and i < len(findings) - 1:
            time.sleep(delay)
    return results
