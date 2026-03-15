"""Expand base search queries using Claude to generate additional angles."""

import json
import logging

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a medical research query generator for an oncology education blog.
Given a topic and base search queries, generate additional queries that cover:
- Different angles (patient perspective, clinical perspective, research perspective)
- Synonyms and alternative medical terminology
- Specific subtopics within the main topic
- Queries optimized for different search backends:
  - "serper": natural language Google queries
  - "pubmed": MeSH terms and structured PubMed queries
  - "clinicaltrials": condition and intervention terms
  - "openfda": drug names for FDA adverse events and label searches
  - "civic": gene names, therapy names for genomics evidence
- Multilingual queries for European languages (en, de, fr, it, es)

Return a JSON array of objects with: query_text, search_engine, language
Target: 15-25 total queries including the base queries.
Return ONLY the JSON array, no other text."""


def expand_queries(
    topic_title: str,
    base_queries: list[str],
    api_key: str,
    model: str = "claude-haiku-4-5-20251001",
) -> list[dict]:
    """Expand base queries into a comprehensive set for all search backends.

    Returns list of {query_text, search_engine, language}.
    Base queries are always included as serper/en even if expansion fails.
    """
    # Always include base queries as serper/en
    base = [{"query_text": q, "search_engine": "serper", "language": "en"} for q in base_queries]

    if not api_key:
        logger.warning("No API key for query expansion, returning base queries only")
        return base

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Topic: {topic_title}\n\nBase queries:\n"
                    + "\n".join(f"- {q}" for q in base_queries),
                }
            ],
        )
        text = message.content[0].text.strip()
        # Parse JSON, handle markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        expanded = json.loads(text)

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
