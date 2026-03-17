"""Generate master guide markdown from enriched findings.

Multi-pass approach: first plan sections, then generate each section separately.
This produces comprehensive, patient-focused guides (30-70KB) instead of short summaries.
"""

import logging
import os
import json
from datetime import datetime

import anthropic

from .utils import api_call, extract_domain

logger = logging.getLogger(__name__)

# --- Prompts ---

# Critical sections use Sonnet (safety-critical for patients)
CRITICAL_SECTIONS = {
    "treatment-efficacy",  # wrong number = wrong treatment decision
    "side-effects",        # missing effect = patient unprepared
    "emergency-signs",     # wrong alarm sign = direct danger
    "resistance",          # missing Plan B = patient left without options
}

GUIDE_SECTIONS = [
    {
        "id": "big-picture",
        "title": "CE AI DE FAPT -- THE BIG PICTURE",
        "description": "What this condition is concretely. Real numbers: incidence, honest prognosis. 'Not the end -- but you need to know exactly what you're fighting.'",
    },
    {
        "id": "demographics",
        "title": "CINE FACE ACEASTA BOALA",
        "description": "Demographics, risk factors (or absence thereof), 'it's not your fault'. Typical age, smokers vs non-smokers, sex if relevant.",
    },
    {
        "id": "treatment-efficacy",
        "title": "CAT DE BINE FUNCTIONEAZA TRATAMENTUL",
        "description": "ORR, median PFS, median OS -- real numbers from published trials. Table: treatment | line | ORR | PFS | OS | source. Compare options. NO marketing ('durable response') -- concrete numbers.",
    },
    {
        "id": "how-to-take",
        "title": "CUM SE IA MEDICAMENTUL CORECT",
        "description": "Dose, timing, with/without food. pH-dependent absorption? Interactions with dairy? PPI? Practical rules that DIRECTLY affect efficacy. Table: situation | what to do | why it matters.",
    },
    {
        "id": "side-effects",
        "title": "EFECTE SECUNDARE -- PROBABILITATI REALE",
        "description": "Table: effect | frequency % | grade | what to do. Not 'possible/rare' -- real percentages. Include effects doctors frequently omit. Hyperglycemia, QTc, hepatotoxicity if relevant.",
    },
    {
        "id": "emergency-signs",
        "title": "CAND MERGI LA URGENTE -- ACUM",
        "description": "Printable checklist. Alarm signs requiring emergency. Format: symptom -> immediate action. Bold, clear, no ambiguity. Can save lives.",
    },
    {
        "id": "interactions",
        "title": "INTERACTIUNI MEDICAMENTE SI ALIMENTE",
        "description": "Table: drug/food | effect | action. 'NEVER with X', 'take 2h before Y'. Include supplements, natural remedies, common OTC.",
    },
    {
        "id": "monitoring",
        "title": "CE TREBUIE MONITORIZAT DE MEDIC",
        "description": "Table: test | frequency | why | what to watch. What to request if doctor doesn't propose it. ECG, liver function, blood sugar, thyroid if relevant.",
    },
    {
        "id": "resistance",
        "title": "CAND TRATAMENTUL NU MAI FUNCTIONEAZA",
        "description": "Resistance: why it happens, how fast, signs. Concrete Plan B/C: re-biopsy, trials, other lines. 'You need a plan BEFORE you need it.'",
    },
    {
        "id": "pipeline",
        "title": "CE URMEAZA -- PIPELINE CERCETARE",
        "description": "New drugs in trials, phase, when they could be available. Table: drug | phase | mechanism | estimated timeline. Realistic hope, not hype.",
    },
    {
        "id": "timeline",
        "title": "TIMELINE-UL TAU REALIST",
        "description": "What to expect chronologically: Week 1-2, Month 1-3, Month 3-12, Year 1-2, Year 2+. Set expectations, reduce anxiety.",
    },
    {
        "id": "daily-life",
        "title": "VIATA DE ZI CU ZI",
        "description": "Exercise (specific, not generic), evidence-based nutrition. Work, travel (restrictions?), relationships, psychological support. Patient communities with links.",
    },
    {
        "id": "red-flags",
        "title": "CE SA NU FACI -- GRESELI SI RED FLAGS",
        "description": "List of frequent mistakes with explanation of why they're dangerous. Format: MISTAKE -> WHY IT'S DANGEROUS -> WHAT TO DO INSTEAD. Dangerous 'natural' treatments, stopping treatment, ignoring side effects.",
    },
    {
        "id": "questions-for-doctor",
        "title": "CE SA INTREBI MEDICUL",
        "description": "Concrete questions per stage: At diagnosis, At treatment start, At progression. Context for each question (why it's important).",
    },
    {
        "id": "european-access",
        "title": "ACCES EUROPEAN SI GHIDURI INTERNATIONALE",
        "description": "ESMO vs NCCN -- relevant differences. EMA approval, availability per country. Access disparities, what to do if not approved in your country. Patient rights, cross-border healthcare directive.",
    },
]

SECTION_PLAN_TOOL = {
    "name": "submit_section_plan",
    "description": "Submit section-to-findings mapping plan for guide generation",
    "input_schema": {
        "type": "object",
        "properties": {
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "finding_ids": {"type": "array", "items": {"type": "integer"}},
                        "priority_claims": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["id", "title", "finding_ids"],
                },
            }
        },
        "required": ["sections"],
    },
}

PLANNER_SYSTEM = """You are a medical content strategist mapping research findings to a fixed guide structure.

You will receive a list of 15 predefined sections and research findings.
Your job is to assign finding numbers to each section based on relevance.

Rules:
- Use ALL 15 sections, in the order given
- A finding can appear in multiple sections if relevant
- If no findings are relevant to a section, set finding_ids to empty array []
- Prioritize findings with higher relevance scores
- Be thorough: scan ALL findings, not just the first few

Use the submit_section_plan tool to submit your mapping."""

SECTION_SYSTEM = """You are a medical writer creating ONE section of a comprehensive patient guide
for an oncology education blog (OncoGuide).

LANGUAGE: Write ENTIRELY in English. Every word, every heading, every table header.
Do NOT switch to Romanian, Spanish, French, German, Italian, or any other language.

VOICE AND TONE:
- Write as a knowledgeable patient advocate who has been through it, NOT a textbook
- Address the reader directly ("you", "your")
- Be honest and direct -- patients deserve real numbers, not vague reassurance
- Explain medical terms immediately when first used (in parentheses)
- Short paragraphs (max 4 lines). Dense with information, not padded with filler.
- Use tables for comparative data (response rates, survival, side effects)
- Bold key facts and warnings
- Be actionable: "Print this", "Ask your doctor this", "Do NOT take X with Y"

FORMATTING:
- Use ### for sub-headings within your section (NEVER ## which is reserved for section titles)
- Use bullet lists and tables, not long paragraphs
- For emergency/checklist sections, use checkbox format: - [ ] Symptom -> Action
- End each section with 1-2 bold KEY TAKEAWAYS

RULES:
- Every claim MUST cite a finding by number: [[Finding N](URL)]
- Include specific numbers (percentages, months, dosages) whenever available
- Do NOT invent or extrapolate data beyond what findings provide
- If findings contain contradictory data, present both with context
- For critical claims (survival, response rates, safety), PREFER findings with Authority 4-5 (top journals, guidelines, agencies). Flag claims based only on Authority 1-2 sources.
- Use standard quotes (""), double hyphens (--), NO emojis, NO typographic quotes, NO em-dashes
- Prefer tables over prose for any comparative or list-like data

LENGTH: 400-1200 words per section. Be dense and precise, not verbose. Every sentence must
earn its place. If a table says it better than a paragraph, use the table.

QUALITY EXAMPLE -- this is the level of density and actionability you must match:

### How to take the drug correctly

| Detail | What to do |
|---|---|
| **Dose** | 120 mg twice daily if <50 kg; 160 mg twice daily if >=50 kg |
| **Food** | Can be taken with or without food -- EXCEPT if you take a PPI, then MUST take with food |
| **Dairy products** | **Avoid milk, yogurt, cheese 2 hours before and 2 hours after taking the pill.** Dairy buffers stomach acid -> drug cannot dissolve. |
| **Vomited after a dose?** | Do NOT re-take it. Next dose at normal time. |
| **Missed a dose?** | Do NOT double up. Resume normal schedule. |

| Factor | How much it hurts | What to do |
|---|---|---|
| **PPI taken fasting** | **-69% drug in blood, -88% peak level** | NEVER take fasting if on a PPI. Always with food. |
| **Antacids (Tums, Rennie)** | Significant | Take drug 2h before OR 2h after antacids |

**KEY TAKEAWAY: Your stomach must be acidic for this drug to dissolve. Anything that raises pH = less drug in your blood = less effective treatment.**

--- END EXAMPLE ---

Notice: tables with real numbers, bold actionable rules, direct language, no filler. Match this."""

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
        authority = f.get('authority_score', 0)
        parts.append(
            f"[{i}] Score: {f.get('relevance_score', '?')}/10 | Authority: {authority}/5\n"
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
    """Ask Claude to map findings to the 15 predefined guide sections."""
    sections_json = json.dumps(
        [{"id": s["id"], "title": s["title"], "description": s["description"]}
         for s in GUIDE_SECTIONS],
        indent=2,
    )

    message = api_call(
        client,
        model=model,
        max_tokens=4000,
        system=PLANNER_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Topic: {topic_title}\n"
                    f"Total findings: {findings_count}\n\n"
                    f"Predefined sections:\n{sections_json}\n\n"
                    f"Findings:\n{findings_text}"
                ),
            }
        ],
        tools=[SECTION_PLAN_TOOL],
        tool_choice={"type": "tool", "name": "submit_section_plan"},
    )

    sections = message.content[0].input["sections"]
    logger.info(f"Mapped findings to {len(sections)} sections for guide")
    return sections


def _generate_section(
    client: anthropic.Anthropic,
    topic_title: str,
    section: dict,
    section_num: int,
    findings_text: str,
    model: str,
    cross_verify_report: str = "",
) -> str:
    """Generate one section of the guide."""
    cross_verify_block = ""
    if cross_verify_report:
        cross_verify_block = (
            f"\n\n=== CROSS-VERIFICATION REPORT ===\n"
            f"The following report compares the AI oncologist's initial claims against real findings.\n"
            f"When a claim is CONTRADICTED, use the finding's number instead.\n"
            f"When a claim is UNVERIFIED, note it as unconfirmed.\n\n"
            f"{cross_verify_report}\n"
        )

    # Look up description from GUIDE_SECTIONS if not in planner output
    section_id = section.get("id", "")
    section_def = next((s for s in GUIDE_SECTIONS if s["id"] == section_id), None)
    description = section.get("description") or (section_def["description"] if section_def else "")

    message = api_call(
        client,
        model=model,
        max_tokens=4000,
        system=SECTION_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Topic: {topic_title}\n"
                    f"Section {section_num}: {section['title']}\n"
                    f"Section scope: {description}\n"
                    f"Key finding IDs to use: {section.get('finding_ids', 'all relevant')}\n\n"
                    f"ALL findings (reference by number):\n{findings_text}"
                    f"{cross_verify_block}"
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
    critical_model: str = "",
    cross_verify_report: str = "",
):
    """Generate a comprehensive master guide from findings using multi-pass generation.

    Pass 1: Plan sections based on all findings
    Pass 2: Generate each section individually with full context

    Args:
        model: Model for non-critical sections and planning (default Haiku).
        critical_model: Model for safety-critical sections (treatment-efficacy, side-effects,
            emergency-signs, resistance). If empty, uses `model` for all sections.
        cross_verify_report: Formatted cross-verification report (VERIFIED/CONTRADICTED/UNVERIFIED).
            When provided, each section generation receives this as context to prefer real findings
            over discovery claims where they differ.
    """
    if not findings:
        logger.warning(f"No findings for '{topic_title}', skipping guide generation")
        return

    client = anthropic.Anthropic(api_key=api_key)
    findings_text = _build_findings_text(findings)

    # Pass 1: Plan sections
    try:
        sections = _plan_sections(client, topic_title, findings_text, len(findings), model)
    except Exception as e:
        logger.error(f"Finding mapping failed: {e}")
        raise

    # Pass 2: Generate each section (critical sections use Sonnet if available)
    guide_parts = []
    for i, section in enumerate(sections, 1):
        section_id = section.get("id", "")
        is_critical = section_id in CRITICAL_SECTIONS
        section_model = critical_model if (is_critical and critical_model) else model
        model_label = "Sonnet" if section_model == critical_model and critical_model else "Haiku"
        print(f"  Section {i}/{len(sections)}: {section['title']} [{model_label}]")
        try:
            content = _generate_section(
                client, topic_title, section, i, findings_text, section_model,
                cross_verify_report=cross_verify_report,
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
