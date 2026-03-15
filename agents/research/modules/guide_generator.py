"""Generate master guide markdown from enriched findings.

Multi-pass approach: first plan sections, then generate each section separately.
This produces comprehensive, patient-focused guides (30-70KB) instead of short summaries.
"""

import logging
import os
import json
from datetime import datetime

import anthropic

from .utils import extract_domain

logger = logging.getLogger(__name__)

# --- Prompts ---

PLANNER_SYSTEM = """You are a medical content strategist planning a comprehensive patient guide.
Given research findings about a cancer topic, plan the guide sections.

Return a JSON array of section objects. Each section must have:
- "id": short kebab-case id (e.g., "big-picture", "treatment-efficacy")
- "title": section title in CAPS (e.g., "THE BIG PICTURE -- WHAT YOU'RE DEALING WITH")
- "description": 2-3 sentence description of what this section must cover
- "finding_ids": array of finding numbers [1, 5, 23, ...] most relevant to this section

Plan 8-14 sections. MUST include these types (adapt titles to the specific topic):
1. Big picture / overview (what this condition is, who gets it, what it means)
2. Diagnosis and testing (how it's detected, what tests are needed)
3. Treatment options and efficacy (honest numbers, response rates, survival data)
4. Side effects and safety (real probabilities, not vague warnings)
5. When treatment stops working / resistance (what happens next)
6. Clinical trials and research pipeline (what's coming)
7. Practical daily life (how to live with this condition/treatment)
8. What NOT to do / Red flags (common mistakes patients make)
9. What to ask your doctor (concrete questions)
10. European/international context (access, guidelines differences)

Return ONLY valid JSON, no markdown, no explanation."""

SECTION_SYSTEM = """You are a medical writer creating ONE section of a comprehensive patient guide
for an oncology education blog (OncoGuide).

VOICE AND TONE:
- Write as a knowledgeable patient advocate, NOT a textbook
- Address the reader directly ("you", "your")
- Be honest and direct -- patients deserve real numbers, not vague reassurance
- Explain medical terms immediately when first used
- Short paragraphs (max 4 lines)
- Use tables for comparative data (response rates, survival, side effects)
- Bold key facts and warnings

RULES:
- Every claim MUST cite a finding by number: [[Finding N](URL)]
- Include ALL relevant data from the assigned findings -- do not summarize away important details
- Include specific numbers (percentages, months, dosages) whenever available
- Do NOT invent or extrapolate data beyond what findings provide
- If findings contain contradictory data, present both with context
- Use standard quotes (""), double hyphens (--), NO emojis, NO typographic quotes, NO em-dashes

LENGTH: Write 800-2000 words per section. Be comprehensive. Do not cut corners."""

GUIDE_HEADER = """# {title} -- Master Guide

**Generated:** {date}
**Findings analyzed:** {count}
**Top sources:** {top_sources}

---

"""


def _build_findings_text(findings: list[dict]) -> str:
    """Build formatted findings text for Claude context."""
    parts = []
    for i, f in enumerate(findings, 1):
        parts.append(
            f"[{i}] Score: {f.get('relevance_score', '?')}/10\n"
            f"Title: {f.get('title_english', 'N/A')}\n"
            f"Summary: {f.get('summary_english', 'N/A')}\n"
            f"URL: {f.get('source_url', 'N/A')}"
        )
    return "\n\n".join(parts)


def _plan_sections(
    client: anthropic.Anthropic,
    topic_title: str,
    findings_text: str,
    findings_count: int,
    model: str,
) -> list[dict]:
    """Ask Claude to plan the guide sections based on findings."""
    message = client.messages.create(
        model=model,
        max_tokens=4000,
        system=PLANNER_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Topic: {topic_title}\n"
                    f"Total findings: {findings_count}\n\n"
                    f"Findings:\n{findings_text}"
                ),
            }
        ],
    )

    raw = message.content[0].text.strip()
    # Handle markdown code blocks
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    sections = json.loads(raw)
    logger.info(f"Planned {len(sections)} sections for guide")
    return sections


def _generate_section(
    client: anthropic.Anthropic,
    topic_title: str,
    section: dict,
    section_num: int,
    findings_text: str,
    model: str,
) -> str:
    """Generate one section of the guide."""
    message = client.messages.create(
        model=model,
        max_tokens=8000,
        system=SECTION_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Topic: {topic_title}\n"
                    f"Section {section_num}: {section['title']}\n"
                    f"Section scope: {section['description']}\n"
                    f"Key finding IDs to use: {section.get('finding_ids', 'all relevant')}\n\n"
                    f"ALL findings (reference by number):\n{findings_text}"
                ),
            }
        ],
    )
    return message.content[0].text.strip()


def generate_guide(
    topic_title: str,
    findings: list[dict],
    output_path: str,
    api_key: str,
    model: str = "claude-haiku-4-5-20251001",
):
    """Generate a comprehensive master guide from findings using multi-pass generation.

    Pass 1: Plan sections based on all findings
    Pass 2: Generate each section individually with full context
    """
    if not findings:
        logger.warning(f"No findings for '{topic_title}', skipping guide generation")
        return

    client = anthropic.Anthropic(api_key=api_key)
    findings_text = _build_findings_text(findings)

    # Pass 1: Plan sections
    try:
        sections = _plan_sections(client, topic_title, findings_text, len(findings), model)
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Section planning failed: {e}. Falling back to single-pass.")
        sections = [
            {
                "id": "full-guide",
                "title": "COMPLETE GUIDE",
                "description": "Full comprehensive guide covering all aspects of the topic.",
                "finding_ids": list(range(1, len(findings) + 1)),
            }
        ]

    # Pass 2: Generate each section
    guide_parts = []
    for i, section in enumerate(sections, 1):
        print(f"  Section {i}/{len(sections)}: {section['title']}")
        try:
            content = _generate_section(
                client, topic_title, section, i, findings_text, model
            )
            guide_parts.append(f"## {i}. {section['title']}\n\n{content}")
        except Exception as e:
            logger.error(f"Section generation failed for '{section['title']}': {e}")
            guide_parts.append(f"## {i}. {section['title']}\n\n*Generation failed: {e}*")

    # Assemble guide
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
        f.write("\n\n".join(guide_parts))

    total_size = os.path.getsize(output_path)
    logger.info(f"Guide generated: {output_path} ({len(findings)} findings, {len(sections)} sections, {total_size // 1024}KB)")
