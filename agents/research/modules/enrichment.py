"""Enrich search findings using Claude -- classify relevance and score."""

import json
import logging
import time

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a medical research classifier for an oncology education blog.
Given a search finding and a research topic, determine:
1. Is this finding relevant to the topic? (true/false)
2. Relevance score (1-10, where 10 = directly addresses the topic with authoritative data)
3. Title in English (translate if needed)
4. Summary in English (2-3 sentences capturing the key information)

Return ONLY a JSON object:
{"relevant": true/false, "relevance_score": N, "title_english": "...", "summary_english": "..."}"""

USER_TEMPLATE = """TOPIC: {topic}

FINDING:
TITLE: {title}
URL: {url}
SNIPPET: {snippet}
SOURCE LANGUAGE: {language}
DATE: {date}"""

# Token tracking
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
        )
        _token_usage["input"] += message.usage.input_tokens
        _token_usage["output"] += message.usage.output_tokens

        text = message.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)

    except Exception as e:
        logger.error(f"Enrichment failed for '{finding.get('title', '?')}': {e}")
        return {"relevant": False, "relevance_score": 0, "title_english": "", "summary_english": ""}


def enrich_batch(
    findings: list[dict],
    topic_title: str,
    api_key: str,
    model: str = "claude-haiku-4-5-20251001",
    delay: float = 0.3,
    progress_callback=None,
) -> list[dict]:
    """Enrich a batch of findings. Returns list of enrichment results."""
    results = []
    for i, finding in enumerate(findings):
        result = enrich_finding(finding, topic_title, api_key, model)
        results.append(result)
        if progress_callback:
            progress_callback(i + 1, len(findings))
        if delay > 0 and i < len(findings) - 1:
            time.sleep(delay)
    return results
