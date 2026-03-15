"""Generate master guide markdown from enriched findings."""

import logging
import os
from datetime import datetime

import anthropic

from .utils import extract_domain

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a medical content researcher creating a comprehensive master guide
for an oncology education blog. You will receive a list of research findings about a specific topic.

Generate a well-structured markdown guide that includes:
1. Executive Summary (3-5 key takeaways)
2. Main content organized by subtopics (derive subtopics from the findings)
3. Key statistics and data points (cite sources)
4. Current guidelines and protocols (ESMO, NCCN where applicable)
5. Controversies or areas of active debate
6. Sources list with URLs

Rules:
- Every claim must be traceable to a specific finding
- Use clear, patient-accessible language
- Include source URLs for key claims
- Organize from most important to least important
- Do NOT invent data -- use only what is in the findings"""

GUIDE_HEADER = """# {title} -- Master Guide

**Generated:** {date}
**Findings analyzed:** {count}
**Top sources:** {top_sources}

---

"""


def generate_guide(
    topic_title: str,
    findings: list[dict],
    output_path: str,
    api_key: str,
    model: str = "claude-haiku-4-5-20251001",
):
    """Generate a master guide markdown from findings. Skips if no findings."""
    if not findings:
        logger.warning(f"No findings for '{topic_title}', skipping guide generation")
        return

    # Build findings context for Claude
    findings_text = ""
    for i, f in enumerate(findings, 1):
        findings_text += (
            f"\n[{i}] Score: {f.get('relevance_score', '?')}/10\n"
            f"Title: {f.get('title_english', 'N/A')}\n"
            f"Summary: {f.get('summary_english', 'N/A')}\n"
            f"URL: {f.get('source_url', 'N/A')}\n"
        )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Topic: {topic_title}\n\nFindings ({len(findings)} total):\n{findings_text}",
                }
            ],
        )
        guide_content = message.content[0].text.strip()

        # Build top sources list
        top_sources = ", ".join(
            extract_domain(f.get("source_url", ""))
            for f in sorted(findings, key=lambda x: x.get("relevance_score", 0), reverse=True)[:5]
        )

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(GUIDE_HEADER.format(
                title=topic_title,
                date=datetime.now().strftime("%Y-%m-%d"),
                count=len(findings),
                top_sources=top_sources,
            ))
            f.write(guide_content)

        logger.info(f"Guide generated: {output_path} ({len(findings)} findings)")

    except Exception as e:
        logger.error(f"Guide generation failed for '{topic_title}': {e}")
