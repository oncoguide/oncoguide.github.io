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
    "mistakes",         # wrong info here = patient endangers themselves
    "side-effects",     # missing effect = patient unprepared
    "emergency-signs",  # wrong alarm sign = direct danger
    "resistance",       # missing Plan B = patient left without options
}

# v6: 16 lifecycle sections mapped from Q1-Q8
GUIDE_SECTIONS = [
    {
        "id": "understanding-diagnosis",
        "title": "WHAT YOU HAVE -- UNDERSTANDING YOUR DIAGNOSIS",
        "lifecycle": "Q1",
        "description": "What this diagnosis means exactly. Molecular testing, staging, subtypes and why they matter. Real prognosis with numbers.",
    },
    {
        "id": "best-treatment",
        "title": "THE BEST TREATMENT RIGHT NOW",
        "lifecycle": "Q2",
        "description": "Approved drugs per line. Table: treatment | line | ORR% | PFS months | OS months | source. ESMO vs NCCN. Immunotherapy role. Head-to-head if available.",
    },
    {
        "id": "mistakes",
        "title": "WHAT NOT TO DO -- MISTAKES THAT CAN COST YOU",
        "lifecycle": "Q7",
        "description": "Format per mistake: MISTAKE: {what} / WHY DANGEROUS: {consequence} / INSTEAD: {alternative}. Dangerous interactions, contraindicated supplements, myths, stopping treatment.",
    },
    {
        "id": "how-to-take",
        "title": "HOW TO TAKE YOUR TREATMENT CORRECTLY",
        "lifecycle": "Q3-dosing",
        "description": "Per approved drug: dose, timing, food rules, pH/PPI/dairy interactions. Table: situation | what to do | why it matters.",
    },
    {
        "id": "side-effects",
        "title": "SIDE EFFECTS -- REAL PROBABILITIES",
        "lifecycle": "Q3-effects",
        "description": "Per drug: table: effect | frequency % | grade | what to do. Include under-reported effects (hyperglycemia, QTc, taste changes). Practical management per major effect.",
    },
    {
        "id": "interactions",
        "title": "DRUG AND FOOD INTERACTIONS",
        "lifecycle": "Q3-interactions",
        "description": "Table: drug/food | effect | action. 'NEVER with X', 'take 2h before Y'. Supplements, OTC, natural remedies. CYP profile explained simply.",
    },
    {
        "id": "monitoring",
        "title": "WHAT MONITORING YOU NEED",
        "lifecycle": "Q3-monitoring",
        "description": "Table: test | frequency | why | what to watch. ECG, liver, glucose, thyroid, creatinine. Include liquid biopsy/ctDNA if relevant for this diagnosis.",
    },
    {
        "id": "emergency-signs",
        "title": "WHEN TO GO TO THE ER -- NOW",
        "lifecycle": "Q3-emergency",
        "description": "PRINTABLE checklist with checkboxes: - [ ] Symptom -> Immediate action. Bold, clear, no ambiguity. 'Print this page and put it on your fridge.'",
    },
    {
        "id": "metastases",
        "title": "WHERE IT SPREADS AND WHAT TO DO",
        "lifecycle": "Q4",
        "description": "Per common metastasis site: frequency %, detection, standard treatment, local options (SBRT, surgery, ablation), site-specific supportive care.",
    },
    {
        "id": "resistance",
        "title": "WHEN TREATMENT STOPS WORKING",
        "lifecycle": "Q5",
        "description": "How resistance develops. Specific mechanisms BY NAME. Median time. Plan B, C, D -- CONCRETE with data. Re-biopsy: when, what to look for. 'You need a plan BEFORE you need it.'",
    },
    {
        "id": "pipeline",
        "title": "WHAT'S COMING -- PIPELINE AND TRIALS",
        "lifecycle": "Q6",
        "description": "Per drug in development: table: drug | phase | mechanism | timeline | targets resistance? Active clinical trials with NCT, locations, eligibility. Realistic hope, not hype.",
    },
    {
        "id": "daily-life",
        "title": "DAILY LIFE",
        "lifecycle": "Q3-daily",
        "description": "Nutrition (specific, evidence-based). Exercise. Fatigue management. Work, travel, relationships. Psychological support. Sexuality and fertility. Realistic timeline: Week 1-2, Month 1-3, Month 3-12, Year 1-2.",
    },
    {
        "id": "treatment-access",
        "title": "ACCESS TO TREATMENT",
        "lifecycle": "Q3-access+Q9",
        "description": "Per major European country: how to get treatment. Presidential ordinance (Romania), ATU (France), Hartefallprogramm (Germany), NHS Cancer Drugs Fund (UK). Compassionate use (EMA). Financial assistance programs.",
    },
    {
        "id": "community",
        "title": "YOU ARE NOT ALONE",
        "lifecycle": "Q8",
        "description": "Patient communities specific to this diagnosis (with links). Real patient experiences. Caregiver support. Organizations and resources.",
    },
    {
        "id": "questions-for-doctor",
        "title": "WHAT TO ASK YOUR DOCTOR",
        "lifecycle": "Q1-Q8-derived",
        "description": "Concrete questions per stage: At diagnosis (5), At treatment start (5), At progression (5). Context for each (why it matters).",
    },
    {
        "id": "international-guidelines",
        "title": "INTERNATIONAL GUIDELINES",
        "lifecycle": "Q2-guidelines",
        "description": "ESMO vs NCCN -- explicit differences. EMA approvals vs FDA. Availability per country.",
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

You will receive a list of 16 predefined sections and research findings.
Your job is to assign finding numbers to each section based on relevance.

Rules:
- Use ALL 16 sections, in the order given
- A finding can appear in multiple sections if relevant
- If no findings are relevant to a section, set finding_ids to empty array []
- Prioritize findings with higher relevance scores
- Be thorough: scan ALL findings, not just the first few
- Use the lifecycle_stage tag on findings to guide initial placement (Q1->section 1, Q2->section 2, etc.)

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

# v6: Section briefs -- what each section MUST contain (for validation Layer 1b)
SECTION_BRIEFS = {
    "understanding-diagnosis": "Diagnostic explained plainly + tests + staging + prognosis with numbers",
    "best-treatment": "Comparative treatment table with ORR/PFS/OS + ESMO/NCCN guidelines",
    "mistakes": "Min 8 mistakes in format MISTAKE/WHY DANGEROUS/WHAT TO DO INSTEAD",
    "how-to-take": "Per drug: dose, timing, food, pH, PPI -- practical table",
    "side-effects": "Per drug: table side effects with frequency %, grade, action",
    "interactions": "Table interactions (drugs, food, supplements) with action",
    "monitoring": "Table monitoring (test, frequency, why) + liquid biopsy if relevant",
    "emergency-signs": "Min 5 PRINTABLE checkboxes: symptom -> immediate action",
    "metastases": "Per metastasis site: frequency %, treatment, local options",
    "resistance": "Resistance mechanisms BY NAME + Plan B/C/D CONCRETE + rebiopsy",
    "pipeline": "Table pipeline drugs (drug, phase, mechanism, timeline) + active trials NCT",
    "daily-life": "Nutrition + exercise + fatigue + work + travel + psych + fertility + realistic timeline",
    "treatment-access": "Per country: legal access mechanisms + financial assistance",
    "community": "Diagnosis-SPECIFIC communities with links + patient stories + caregiver support",
    "questions-for-doctor": "Min 5 questions per stage (diagnosis, treatment, progression) with context",
    "international-guidelines": "Explicit ESMO/NCCN differences + availability per country",
}

EXECUTIVE_SUMMARY_SYSTEM = """You are a patient who just received a cancer diagnosis.
Write a MAX 200-word "BEFORE ANYTHING ELSE" section that answers:
1. What do I have? (1-2 sentences, plain language)
2. Is there treatment? (YES/NO + the specific drug name)
3. How serious is it? (REAL prognosis with numbers -- not vague, not falsely optimistic)
4. What do I do RIGHT NOW? (direct the reader to sections 3 and 4)

End with: "The rest comes when you are ready. You have time. The information is not going anywhere."

Tone: warm, direct, no condescension. You have been through this yourself.
Do NOT use emojis, typographic quotes, or em-dashes. Use standard quotes and double hyphens."""

GUIDE_HEADER = """# {title} -- Master Guide

**Generated:** {date}
**Findings analyzed:** {count}
**Top sources:** {top_sources}
**Last updated:** {date}

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
    """Ask Claude to map findings to the 16 predefined guide sections."""
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

    # Look up description and brief from GUIDE_SECTIONS
    section_id = section.get("id", "")
    section_def = next((s for s in GUIDE_SECTIONS if s["id"] == section_id), None)
    description = section.get("description") or (section_def["description"] if section_def else "")
    brief = SECTION_BRIEFS.get(section_id, "")
    brief_block = f"\n\nSECTION BRIEF (this section MUST contain): {brief}" if brief else ""

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
                    f"{brief_block}\n"
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

    # Pass 3: Generate executive summary from sections 1-3 (SPEC 10.4)
    exec_summary = ""
    sections_1_3 = "\n\n".join(guide_parts[:3]) if len(guide_parts) >= 3 else "\n\n".join(guide_parts)
    try:
        print(f"  Executive summary: BEFORE ANYTHING ELSE [Haiku]")
        exec_msg = api_call(
            client,
            model=model,  # Haiku -- not safety-critical, just a summary
            max_tokens=500,
            system=EXECUTIVE_SUMMARY_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Diagnosis: {topic_title}\n\n"
                    f"Here are the first 3 sections of the guide:\n\n{sections_1_3}"
                ),
            }],
        )
        exec_summary = exec_msg.content[0].text.strip()
    except Exception as e:
        logger.error(f"Executive summary generation failed: {e}")
        exec_summary = (
            "**What you have:** [Could not generate -- see Section 1]\n"
            "**Is there treatment:** [See Section 2]\n"
            "**How serious:** [See Section 1]\n"
            "**What to do NOW:** Read Section 3 (what NOT to do) and Section 4 (how to take treatment)."
        )

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
        # Executive summary before all sections
        f.write(f"## BEFORE ANYTHING ELSE\n\n{exec_summary}\n\n---\n\n")
        f.write("\n\n".join(guide_parts))

    total_size = os.path.getsize(output_path)
    logger.info(f"Guide generated: {output_path} ({len(findings)} findings, {len(sections)} sections, {total_size // 1024}KB)")
