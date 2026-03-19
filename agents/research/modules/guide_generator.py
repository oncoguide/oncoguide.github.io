"""Generate master guide markdown from enriched findings.

v6: Lifecycle-filtered generation. Each section receives only findings matching
its lifecycle_stage, sorted by authority_score DESC. No planner call needed --
lifecycle_stage from enrichment IS the mapping.
"""

import logging
import os
import json
import re
from collections import defaultdict
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
        "description": "What this diagnosis means exactly. Molecular testing, staging, subtypes and why they matter. Real prognosis with numbers. Where to get expert molecular testing (academic centers, reference labs). Second opinion value.",
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
        "description": "Table: test | frequency | why | what to watch. ECG, liver, glucose, thyroid, creatinine. Include liquid biopsy/ctDNA if relevant for this diagnosis. Advanced imaging technologies (PCCT, PET/CT innovations). AI-assisted pathology if emerging.",
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
        "description": "Per drug in development: table: drug | phase | mechanism | timeline | targets resistance? Include frontier immunotherapy, vaccine platforms, PROTACs, bispecifics, CAR-T -- not just next-gen inhibitors. Active clinical trials with NCT, locations, eligibility. Realistic hope, not hype.",
    },
    {
        "id": "daily-life",
        "title": "DAILY LIFE",
        "lifecycle": "Q3-daily",
        "description": "Nutrition (specific, evidence-based). Exercise. Fatigue management. Supportive care protocols (bone health, dental, vitamin D). Work, travel, relationships. Psychological support. Sexuality and fertility. Realistic timeline: Week 1-2, Month 1-3, Month 3-12, Year 1-2.",
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

CITATION AND AUTHORITY RULES (CRITICAL):
- Every claim MUST cite a finding by number: [[Finding N](URL)]
- **AUTHORITY HIERARCHY**: Always prefer higher-authority findings:
  - Authority 5 (NEJM, Lancet, JCO, ESMO/NCCN guidelines) = gold standard, cite first
  - Authority 4 (FDA/EMA decisions, systematic reviews) = strong evidence
  - Authority 3 (peer-reviewed reviews, registries) = supportive
  - Authority 2 (press releases, medical news) = use only if no better source exists
  - Authority 1 (blogs, forums) = NEVER cite alone for medical claims
- When findings contradict each other, ALWAYS use the higher-authority source
- Include specific numbers (percentages, months, dosages) whenever available
- Do NOT invent or extrapolate data beyond what findings provide

FORMATTING RULES:
- Use standard quotes (""), double hyphens (--), NO emojis, NO typographic quotes, NO em-dashes
- Prefer tables over prose for any comparative or list-like data
- For emergency sections: use checkbox format - [ ] Symptom -> Action (min 5 checkboxes)
- For pipeline sections: use table format drug | phase | mechanism | timeline
- For treatment/side-effects: use comparative tables with real numbers

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
    "understanding-diagnosis": "Diagnostic explained plainly + tests + staging + prognosis with numbers + expert centers for molecular testing",
    "best-treatment": "Comparative treatment table with ORR/PFS/OS + ESMO/NCCN guidelines",
    "mistakes": "Min 8 mistakes in format MISTAKE/WHY DANGEROUS/WHAT TO DO INSTEAD",
    "how-to-take": "Per drug: dose, timing, food, pH, PPI -- practical table",
    "side-effects": "Per drug: table side effects with frequency %, grade, action",
    "interactions": "Table interactions (drugs, food, supplements) with action",
    "monitoring": "Table monitoring (test, frequency, why) + liquid biopsy if relevant + advanced imaging",
    "emergency-signs": "Min 5 PRINTABLE checkboxes: symptom -> immediate action",
    "metastases": "Per metastasis site: frequency %, treatment, local options",
    "resistance": "Resistance mechanisms BY NAME + Plan B/C/D CONCRETE + rebiopsy",
    "pipeline": "Table pipeline drugs (drug, phase, mechanism, timeline) + frontier immunotherapy/vaccines/PROTACs + active trials NCT",
    "daily-life": "Nutrition + exercise + fatigue + supportive care (bone health, dental) + work + travel + psych + fertility + realistic timeline",
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


# ── v6: Lifecycle-based finding filtering ───────────────────────────

def _get_lifecycle_prefixes(lifecycle: str) -> list[str]:
    """Get all lifecycle_stage prefixes that match a section's lifecycle tag.

    Section lifecycle tags like "Q3-dosing" match findings with lifecycle_stage
    "Q3" (parent) plus any Q3-* sub-stage. Special cases:
    - "Q3-access+Q9" matches Q3, Q3-access, Q9
    - "Q1-Q8-derived" matches ALL stages (questions-for-doctor needs full context)
    - "Q2-guidelines" matches Q2
    """
    if lifecycle == "Q1-Q8-derived":
        # Questions-for-doctor needs a sample from all stages
        return ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9"]
    if "+" in lifecycle:
        # Multi-stage: "Q3-access+Q9" -> ["Q3", "Q9"]
        parts = lifecycle.split("+")
        prefixes = []
        for part in parts:
            base = part.split("-")[0]  # "Q3-access" -> "Q3"
            if base not in prefixes:
                prefixes.append(base)
        return prefixes
    # Single stage: "Q3-dosing" -> "Q3", "Q7" -> "Q7"
    base = lifecycle.split("-")[0]
    return [base]


def _filter_findings_for_section(
    findings: list[dict], lifecycle: str
) -> list[dict]:
    """Filter findings matching a section's lifecycle, sorted by authority DESC."""
    prefixes = _get_lifecycle_prefixes(lifecycle)

    matching = [
        f for f in findings
        if any(
            (f.get("lifecycle_stage") or "").startswith(prefix)
            for prefix in prefixes
        )
    ]

    # Sort by authority_score DESC, then relevance_score DESC
    matching.sort(
        key=lambda f: (f.get("authority_score", 0), f.get("relevance_score", 0)),
        reverse=True,
    )

    return matching


def _build_findings_text(findings: list[dict], start_index: int = 1) -> str:
    """Build formatted findings text for Claude context."""
    parts = []
    for i, f in enumerate(findings, start_index):
        authority = f.get('authority_score', 0)
        lifecycle = f.get('lifecycle_stage', '?')
        parts.append(
            f"[{i}] Score: {f.get('relevance_score', '?')}/10 | Authority: {authority}/5 | Stage: {lifecycle}\n"
            f"Title: {f.get('title_english', 'N/A')}\n"
            f"Summary: {f.get('summary_english', 'N/A')}\n"
            f"URL: {f.get('source_url', 'N/A')}"
        )
    return "\n\n".join(parts)


def _format_grouped_findings(groups, token_budget=180_000, prefer_patient_sources=False):
    """Format findings in tiers within groups, respecting token budget.

    Per group:
      - Top 15-20 findings: FULL DETAIL (title + summary + URL + authority)
      - Remaining: SUMMARY ONLY ([F:id] summary_english)

    Token budget measured as chars // 3 (conservative for medical text).
    Tier 1 is NEVER truncated (budget exempt). Tier 2 truncated if budget exceeded.
    """
    output_parts = []
    tokens_used = 0
    total_tier1 = 0
    total_tier2_shown = 0
    total_tier2_truncated = 0

    for group in groups:
        findings = group["findings"]
        header = f"\n=== {group['name'].upper()} ({len(findings)} findings) ===\n"
        tokens_used += len(header) // 3

        if prefer_patient_sources:
            sort_key = lambda f: (-f.get("relevance_score", 0), f.get("authority_score", 0), f.get("content_hash", ""))
        else:
            sort_key = lambda f: (-f.get("authority_score", 0), -f.get("relevance_score", 0), f.get("content_hash", ""))
        sorted_findings = sorted(findings, key=sort_key)

        tier1_count = min(20, max(15, len(sorted_findings) // 5))
        tier1 = sorted_findings[:tier1_count]
        tier2 = sorted_findings[tier1_count:]
        total_tier1 += len(tier1)

        tier1_text = "\n[HIGH-DETAIL FINDINGS]\n"
        for f in tier1:
            entry = (
                f'[F:{f["id"]}] Authority:{f.get("authority_score", 0)} | '
                f'{f.get("title_english", "N/A")}\n'
                f'{f.get("summary_english", "N/A")}\n'
                f'URL: {f.get("source_url", "N/A")}\n'
            )
            tier1_text += entry
        tokens_used += len(tier1_text) // 3

        tier2_text = "\n[ADDITIONAL FINDINGS]\n"
        truncated = False
        for idx, f in enumerate(tier2):
            entry = f'[F:{f["id"]}] {f.get("summary_english", f.get("title_english", "N/A"))}\n'
            entry_tokens = len(entry) // 3
            if tokens_used + entry_tokens >= token_budget:
                remaining = len(tier2) - idx
                tier2_text += f"... plus {remaining} more findings in this group\n"
                total_tier2_truncated += remaining
                truncated = True
                break
            tier2_text += entry
            tokens_used += entry_tokens
            total_tier2_shown += 1

        if not truncated:
            total_tier2_shown += len(tier2)

        output_parts.append(header + tier1_text + tier2_text)

    metadata = {
        "total_findings": sum(len(g["findings"]) for g in groups),
        "tier1_count": total_tier1,
        "tier2_shown": total_tier2_shown,
        "tier2_truncated": total_tier2_truncated,
        "tokens_used": tokens_used,
        "tokens_budget": token_budget,
        "pct_used": f"{tokens_used / token_budget:.0%}" if token_budget else "N/A",
    }
    return "\n".join(output_parts), metadata


# ── Smart Grouping + Q3 Routing ───────────────────────────────────

GROUP_FINDINGS_TOOL = {
    "name": "group_findings",
    "description": "Assign each finding to one or more topic groups based on its title and subject matter.",
    "input_schema": {
        "type": "object",
        "properties": {
            "groups": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Short descriptive group name (3-6 words)"},
                        "finding_ids": {"type": "array", "items": {"type": "integer"}},
                    },
                    "required": ["name", "finding_ids"],
                },
                "minItems": 5,
                "maxItems": 15,
            }
        },
        "required": ["groups"],
    },
}

ROUTE_Q3_TOOL = {
    "name": "route_q3_findings",
    "description": "Route each Q3 finding to one or more guide sections.",
    "input_schema": {
        "type": "object",
        "properties": {
            "routes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "finding_id": {"type": "integer"},
                        "categories": {
                            "type": "array",
                            "items": {"enum": ["dosing", "side-effects", "interactions",
                                               "monitoring", "emergency", "daily-life", "access"]},
                        },
                    },
                    "required": ["finding_id", "categories"],
                },
            }
        },
        "required": ["routes"],
    },
}

GROUPING_SYSTEM = """You are organizing medical research findings into topic groups for a patient guide about {diagnosis}.

Rules:
- Create 8-12 groups based on subject matter similarity
- A finding can be assigned to MULTIPLE groups if it covers multiple topics
- Order groups by clinical importance (most important for patient first)
- Group names should be specific: "Selpercatinib First-Line Efficacy" not "Treatment"
- Do not create groups smaller than 3 findings; merge small topics into related groups"""

Q3_ROUTING_SYSTEM = """You are routing medical findings to guide sections. A finding can belong to MULTIPLE sections if it covers multiple topics.

Assign each finding to ALL relevant sections:
- "dosing": drug doses, timing, administration, food requirements
- "side-effects": adverse events, toxicity, frequency, management
- "interactions": drug-drug, drug-food, CYP metabolism, supplements
- "monitoring": lab tests, imaging, frequency, what to watch for
- "emergency": urgent symptoms, when to go to ER, danger signs
- "daily-life": nutrition, exercise, fatigue, work, travel, fertility, psychology
- "access": treatment cost, insurance, reimbursement, patient programs"""

ROUTE_TO_SECTION = {
    "dosing": "how-to-take",
    "side-effects": "side-effects",
    "interactions": "interactions",
    "monitoring": "monitoring",
    "emergency": "emergency-signs",
    "daily-life": "daily-life",
    "access": "treatment-access",
}

GUIDELINES_KEYWORDS = {"esmo", "nccn", "guideline", "fda", "ema",
                       "approval", "regulatory", "recommendation"}


def _group_findings_by_topic(findings, section_key, topic_title,
                              api_key=None, model=None):
    """Group findings into topic clusters. Returns list of group dicts.

    For < 500 findings or no api_key: returns single group (no AI call).
    For >= 500 findings: uses Haiku to cluster by topic.
    On failure: falls back to authority-tier grouping.
    """
    if len(findings) < 50 or not api_key:
        return [{"name": "all", "findings": findings}]

    findings_by_id = {f["id"]: f for f in findings}
    table = "\n".join(
        f'{f["id"]} | {f.get("authority_score", 0)} | {f.get("title_english", "N/A")}'
        for f in findings
    )

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = api_call(
            client, model=model or "claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=GROUPING_SYSTEM.format(diagnosis=topic_title),
            messages=[{"role": "user", "content":
                       f"Section: {section_key} ({len(findings)} findings)\n\n"
                       f"ID | Authority | Title\n{table}"}],
            tools=[GROUP_FINDINGS_TOOL],
            tool_choice={"type": "tool", "name": "group_findings"},
        )
        groups_raw = response.content[0].input["groups"]

        # Build groups with full finding objects; findings can appear in multiple groups
        groups = []
        all_assigned = set()
        for g in groups_raw:
            group_findings = [findings_by_id[fid] for fid in g["finding_ids"]
                            if fid in findings_by_id]
            if group_findings:
                groups.append({"name": g["name"], "findings": group_findings})
                all_assigned.update(f["id"] for f in group_findings)

        # Orphan check: findings not in any group
        orphans = [f for f in findings if f["id"] not in all_assigned]
        if orphans:
            groups.append({"name": "Other Findings", "findings": orphans})
            logger.warning(f"Grouping: {len(orphans)} orphan findings added to 'Other'")

        return groups if groups else [{"name": "all", "findings": findings}]

    except Exception as e:
        logger.warning(f"Grouping failed ({e}), falling back to authority-tier grouping")
        return _authority_tier_fallback(findings)


def _authority_tier_fallback(findings):
    """Fallback grouping by authority score tiers."""
    tiers = defaultdict(list)
    labels = {5: "Highest Authority", 4: "High Authority", 3: "Medium Authority",
              2: "Lower Authority", 1: "Other Sources"}
    for f in findings:
        score = f.get("authority_score", 1)
        tiers[score].append(f)
    groups = []
    for score in sorted(tiers.keys(), reverse=True):
        label = labels.get(score, f"Authority {score}")
        groups.append({"name": label, "findings": tiers[score]})
    return groups if groups else [{"name": "all", "findings": findings}]


def _route_q3_findings(findings, api_key, model, topic_title):
    """Route Q3 findings to section categories. Returns {category: set(finding_ids)}."""
    if not findings:
        return {}

    table = "\n".join(
        f'{f["id"]} | {f.get("title_english", "N/A")}'
        for f in findings
    )

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = api_call(
            client, model=model or "claude-haiku-4-5-20251001",
            max_tokens=8192,
            system=Q3_ROUTING_SYSTEM,
            messages=[{"role": "user", "content":
                       f"Diagnosis: {topic_title}\n{len(findings)} Q3 findings to route:\n\n"
                       f"ID | Title\n{table}"}],
            tools=[ROUTE_Q3_TOOL],
            tool_choice={"type": "tool", "name": "route_q3_findings"},
        )
        routes_raw = response.content[0].input["routes"]

        routes = defaultdict(set)
        for r in routes_raw:
            for cat in r["categories"]:
                routes[cat].add(r["finding_id"])

        # Orphan check
        all_routed = set()
        for ids in routes.values():
            all_routed.update(ids)
        orphans = {f["id"] for f in findings} - all_routed
        if orphans:
            routes["daily-life"].update(orphans)  # safe default
            logger.warning(f"Q3 routing: {len(orphans)} orphans defaulted to daily-life")

        return dict(routes)

    except Exception as e:
        logger.warning(f"Q3 routing failed ({e}), assigning all to all sections")
        all_ids = {f["id"] for f in findings}
        return {cat: all_ids for cat in
                ["dosing", "side-effects", "interactions", "monitoring",
                 "emergency", "daily-life", "access"]}


def _identify_guidelines_groups(groups):
    """Identify which groups are guidelines-related by keyword matching."""
    matched = []
    for g in groups:
        name_words = set(g["name"].lower().split())
        if name_words & GUIDELINES_KEYWORDS:
            matched.append(g)
    return matched


def _assign_findings_to_sections(findings, api_key, model, topic_title):
    """Assign findings to sections. Q3 routed via AI, others by lifecycle prefix.

    Returns {section_id: [list of finding dicts]}.
    Section 15 (questions-for-doctor) is NOT populated here -- it uses prior section text.
    Section 16 (international-guidelines) receives Q9 findings.
    """
    section_findings = defaultdict(list)

    q3 = [f for f in findings if (f.get("lifecycle_stage") or "").startswith("Q3")]
    non_q3 = [f for f in findings if not (f.get("lifecycle_stage") or "").startswith("Q3")]

    # Route Q3 findings to specific sections via AI
    if q3:
        routes = _route_q3_findings(q3, api_key, model, topic_title)
        for route_key, finding_ids in routes.items():
            section_key = ROUTE_TO_SECTION.get(route_key)
            if section_key:
                section_findings[section_key].extend(
                    [f for f in q3 if f["id"] in finding_ids]
                )

    # Assign non-Q3 findings by lifecycle prefix
    for section in GUIDE_SECTIONS:
        key = section["id"]
        if key in ("questions-for-doctor", "international-guidelines"):
            continue  # handled separately
        prefixes = _get_lifecycle_prefixes(section["lifecycle"])
        matched = [f for f in non_q3
                   if any((f.get("lifecycle_stage") or "").startswith(p) for p in prefixes)]
        section_findings[key].extend(matched)

    # Section 16: Q9 findings
    q9 = [f for f in findings if (f.get("lifecycle_stage") or "").startswith("Q9")]
    section_findings["international-guidelines"] = list(q9)

    return dict(section_findings)


# ── Mini-discovery for data-first mode ────────────────────────────

MINI_DISCOVERY_TOOL = {
    "name": "submit_insights",
    "description": "Submit cross-domain clinical insights connecting multiple findings.",
    "input_schema": {
        "type": "object",
        "properties": {
            "insights": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "insight": {"type": "string", "description": "The cross-domain connection (1-2 sentences)"},
                        "finding_ids": {"type": "array", "items": {"type": "integer"}, "description": "IDs of findings that support this insight"},
                        "clinical_relevance": {"type": "string", "description": "Why this matters for the patient"},
                    },
                    "required": ["insight", "finding_ids", "clinical_relevance"],
                },
            }
        },
        "required": ["insights"],
    },
}

MINI_DISCOVERY_SYSTEM = """You are an expert oncologist reviewing research findings for a patient guide about {diagnosis}.

Your task: identify CROSS-DOMAIN insights that connect findings from different areas.
These are connections that no single finding states, but that emerge when you read multiple findings together.

Examples of cross-domain insights:
- Drug X causes hyperglycemia (53%) + hyperglycemia causes gastroparesis + Drug X is pH-dependent = patients must monitor glucose closely or drug absorption drops
- Drug Y has 69% reduced absorption with PPI fasting + Drug Y should be taken with food when on PPI = specific dosing guidance
- Resistance mutation Z appears at median 18 months + Drug W targets mutation Z in Phase II = start discussing backup plan at month 12

Focus on insights that are ACTIONABLE for patients. Skip trivial connections.
Maximum 10 insights. Each must cite the finding IDs that support it."""


def mini_discovery(findings, diagnosis, api_key, model="claude-sonnet-4-6", max_findings=50):
    """Generate cross-domain clinical insights from top findings.

    Used in data-first mode to compensate for skipping the discovery loop.
    Single Sonnet call with top findings, returns list of insight dicts.
    Cost: ~$0.05 per call.
    """
    if not findings or not api_key:
        return []

    # Select diverse top findings: top by authority, then sample from each lifecycle stage
    sorted_by_auth = sorted(findings, key=lambda f: (-f.get("authority_score", 0), -f.get("relevance_score", 0)))
    selected = sorted_by_auth[:max_findings]

    findings_text = "\n\n".join(
        f"[F:{f['id']}] Authority:{f.get('authority_score', 0)} | Stage:{f.get('lifecycle_stage', '?')}\n"
        f"Title: {f.get('title_english', 'N/A')}\n"
        f"Summary: {f.get('summary_english', 'N/A')}"
        for f in selected
    )

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = api_call(
            client, model=model, max_tokens=4000,
            system=MINI_DISCOVERY_SYSTEM.format(diagnosis=diagnosis),
            messages=[{"role": "user", "content":
                       f"Diagnosis: {diagnosis}\n\n"
                       f"{len(selected)} top findings to analyze:\n\n{findings_text}"}],
            tools=[MINI_DISCOVERY_TOOL],
            tool_choice={"type": "tool", "name": "submit_insights"},
        )
        insights = response.content[0].input["insights"]
        logger.info(f"Mini-discovery: {len(insights)} cross-domain insights generated")
        return insights
    except Exception as e:
        logger.warning(f"Mini-discovery failed ({e}), continuing without insights")
        return []


ANTI_HALLUCINATION_RULES = """
ABSOLUTE RULES -- VIOLATION OF THESE RULES MAKES THE GUIDE DANGEROUS:

1. EVERY number (percentage, months, mg, dose) MUST come from a finding
   cited as [F:N]. If no finding supports a number, do NOT write that number.

2. EVERY drug name, trial name (NCT), mutation name must appear in at
   least one finding provided to you.

3. If you do not have data for something, write explicitly:
   "Data not available in current sources -- discuss with your oncologist."
   This is SAFER than guessing.

4. NEVER round, estimate, or extrapolate. If a finding says 64.8%, write
   64.8%, not "approximately 65%" and not "64%".

5. When two findings give different numbers for the same metric, present
   BOTH with their sources:
   "PFS 24.8 months (LIBRETTO-431 [F:12]) vs 22 months (real-world [F:512])"
   Contradictions are VALUABLE information for the patient. Never hide them.

6. Do NOT cite a Finding ID that was not provided to you. Every [F:N] must
   correspond to a finding in your input.
"""

# Sections that need oncologist expertise in system prompt
ONCOLOGIST_SECTIONS = {"understanding-diagnosis", "best-treatment", "mistakes",
                       "side-effects", "emergency-signs", "resistance",
                       "international-guidelines"}

# Patient-centric sections where relevance > authority for sorting
PATIENT_CENTRIC_SECTIONS = {"daily-life", "community"}


def _build_section_system(section_id, section_num, topic_title, section,
                          oncologist_ctx="", advocate_ctx=""):
    """Build the system prompt for a section, including expert skills and anti-hallucination rules."""
    parts = [SECTION_SYSTEM]

    if section_id in ONCOLOGIST_SECTIONS and oncologist_ctx:
        parts.append(f"\n=== ONCOLOGIST GUIDANCE ===\n{oncologist_ctx}")

    if advocate_ctx:
        parts.append(f"\n=== PATIENT ADVOCATE GUIDANCE ===\n{advocate_ctx}")

    parts.append(ANTI_HALLUCINATION_RULES)

    return "\n\n".join(parts)


def _generate_section(
    client: anthropic.Anthropic,
    topic_title: str,
    section: dict,
    section_num: int,
    findings_text: str,
    findings_count: int,
    model: str,
    cross_verify_report: str = "",
    oncologist_ctx: str = "",
    advocate_ctx: str = "",
) -> str:
    """Generate one section of the guide using grouped + tiered findings."""
    cross_verify_block = ""
    if cross_verify_report:
        cross_verify_block = (
            f"\n\n=== CROSS-VERIFICATION REPORT ===\n"
            f"The following report compares the AI oncologist's initial claims against real findings.\n"
            f"When a claim is CONTRADICTED, use the finding's number instead.\n"
            f"When a claim is UNVERIFIED, note it as unconfirmed.\n\n"
            f"{cross_verify_report}\n"
        )

    brief = SECTION_BRIEFS.get(section["id"], "")
    brief_block = f"\n\nSECTION BRIEF (this section MUST contain): {brief}" if brief else ""

    system = _build_section_system(
        section["id"], section_num, topic_title, section,
        oncologist_ctx=oncologist_ctx, advocate_ctx=advocate_ctx,
    )

    message = api_call(
        client,
        model=model,
        max_tokens=4000,
        system=system,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Topic: {topic_title}\n"
                    f"Section {section_num}: {section['title']}\n"
                    f"Section scope: {section['description']}\n"
                    f"{brief_block}\n"
                    f"You have {findings_count} findings specifically selected for this section.\n"
                    f"Use as many as possible -- every finding was selected because it is relevant.\n\n"
                    f"Findings for this section:\n{findings_text}"
                    f"{cross_verify_block}"
                ),
            }
        ],
    )
    return message.content[0].text.strip()


def _generate_section_from_context(client, topic_title, section, section_num,
                                    context_text, model, advocate_ctx=""):
    """Generate a section from prior section text instead of findings.

    Used for Section 15 (Questions for Doctor) which derives its content
    from the guide itself, not from raw findings.
    """
    system_parts = [
        f"You are writing Section {section_num} of a patient guide about {topic_title}.\n"
        f"Section: {section['title']}\n"
        f"Brief: {section['description']}\n\n"
        f"IMPORTANT: Generate questions based ONLY on the guide sections provided below. "
        f"Do not invent medical information. Every question should help the patient "
        f"discuss topics covered in the guide with their oncologist."
    ]
    if advocate_ctx:
        system_parts.append(f"\n=== PATIENT ADVOCATE GUIDANCE ===\n{advocate_ctx}")

    user_msg = (
        f"Here are the first 14 sections of the guide. "
        f"Generate questions the patient should ask their doctor, organized by stage "
        f"(at diagnosis, during treatment, at progression).\n\n"
        f"{context_text}"
    )
    message = api_call(client, model=model, max_tokens=4000,
                       system="\n\n".join(system_parts),
                       messages=[{"role": "user", "content": user_msg}])
    return message.content[0].text.strip()


def _format_insights(insights):
    """Format mini-discovery insights as context text for section generation."""
    if not insights:
        return ""
    lines = ["\n=== CROSS-DOMAIN INSIGHTS (from mini-discovery) ===",
             "These insights connect multiple findings. Use them to enrich your section where relevant.\n"]
    for i, ins in enumerate(insights, 1):
        lines.append(f"{i}. {ins['insight']}")
        lines.append(f"   Supporting findings: {ins['finding_ids']}")
        lines.append(f"   Clinical relevance: {ins['clinical_relevance']}\n")
    return "\n".join(lines)


def generate_guide(
    topic_title: str,
    findings: list[dict],
    output_path: str,
    api_key: str,
    model: str = "claude-haiku-4-5-20251001",
    critical_model: str = "",
    cross_verify_report: str = "",
    insights: list[dict] = None,
):
    """Generate a comprehensive master guide from findings.

    v6.1: Smart grouping + tiered formatting + expert skills + anti-hallucination.
    Uses _assign_findings_to_sections() for lifecycle + Q3 routing,
    _group_findings_by_topic() for large sections, _format_grouped_findings()
    for tiered output, and verify_section_citations() post-generation.

    Args:
        model: Model for non-critical sections (default Haiku).
        critical_model: Model for safety-critical sections (mistakes, side-effects,
            emergency-signs, resistance). If empty, uses `model` for all sections.
        cross_verify_report: Formatted cross-verification report.
        insights: Cross-domain insights from mini_discovery() (data-first mode).
    """
    from .utils import load_skill_context, TokenBudgetExceeded

    if not findings:
        logger.warning(f"No findings for '{topic_title}', skipping guide generation")
        return

    client = anthropic.Anthropic(api_key=api_key)

    # Load expert skill contexts
    oncologist_ctx = load_skill_context(".claude/skills/oncologist.md")
    advocate_ctx = load_skill_context(".claude/skills/patient-advocate.md")

    # Format mini-discovery insights (appended to cross_verify_report for each section)
    insights_text = _format_insights(insights or [])
    if insights_text:
        cross_verify_report = (cross_verify_report + "\n\n" + insights_text) if cross_verify_report else insights_text
        logger.info(f"Mini-discovery insights injected into section context ({len(insights or [])} insights)")

    # Step 1: Assign findings to sections (Q3 routing + lifecycle filtering)
    section_findings = _assign_findings_to_sections(findings, api_key, model, topic_title)

    # Step 2: Generate sections 1-14
    guide_parts = []
    generated_sections = {}  # key -> text, for Section 15
    total_findings_used = 0
    failed_sections = []

    for i, section in enumerate(GUIDE_SECTIONS[:14], 1):
        section_id = section["id"]
        is_critical = section_id in CRITICAL_SECTIONS
        section_model = critical_model if (is_critical and critical_model) else model
        model_label = "Sonnet" if section_model == critical_model and critical_model else "Haiku"

        my_findings = section_findings.get(section_id, [])
        total_findings_used += len(my_findings)

        print(f"  Section {i}/{len(GUIDE_SECTIONS)}: {section['title']} [{model_label}] ({len(my_findings)} findings)")

        if not my_findings:
            logger.warning(f"No findings for section '{section_id}' (lifecycle={section['lifecycle']})")
            part = f"## {i}. {section['title']}\n\n*No findings available for this section. This section needs additional research.*"
            guide_parts.append(part)
            generated_sections[section_id] = part
            continue

        # Group within section if large
        groups = _group_findings_by_topic(my_findings, section_id, topic_title,
                                           api_key=api_key, model=model)

        # Tiered formatting with patient source priority for patient-centric sections
        prefer_patient = section_id in PATIENT_CENTRIC_SECTIONS
        findings_text, meta = _format_grouped_findings(
            groups, token_budget=180_000, prefer_patient_sources=prefer_patient
        )
        logger.info(
            f"[Section {i}] {meta['total_findings']} findings | "
            f"{len(groups)} groups | T1:{meta['tier1_count']} T2:{meta['tier2_shown']} | "
            f"{meta['tokens_used'] // 1000}K/{meta['tokens_budget'] // 1000}K tokens ({meta['pct_used']})"
        )

        try:
            content = _generate_section(
                client, topic_title, section, i,
                findings_text, len(my_findings), section_model,
                cross_verify_report=cross_verify_report,
                oncologist_ctx=oncologist_ctx,
                advocate_ctx=advocate_ctx,
            )

            # Post-generation citation verification
            issues = verify_section_citations(content, my_findings)
            critical_issues = [iss for iss in issues if iss["severity"] == "CRITICAL"]
            if critical_issues:
                logger.warning(
                    f"[Section {i}] {len(critical_issues)} CRITICAL citation issues: "
                    f"{[iss['detail'] for iss in critical_issues]}"
                )

            part = f"## {i}. {section['title']}\n\n{content}"
            guide_parts.append(part)
            generated_sections[section_id] = content

        except TokenBudgetExceeded:
            # Retry once with halved token budget
            logger.warning(f"[Section {i}] TokenBudgetExceeded, retrying with halved budget")
            try:
                findings_text_retry, meta_retry = _format_grouped_findings(
                    groups, token_budget=90_000, prefer_patient_sources=prefer_patient
                )
                content = _generate_section(
                    client, topic_title, section, i,
                    findings_text_retry, len(my_findings), section_model,
                    cross_verify_report=cross_verify_report,
                    oncologist_ctx=oncologist_ctx,
                    advocate_ctx=advocate_ctx,
                )
                part = f"## {i}. {section['title']}\n\n{content}"
                guide_parts.append(part)
                generated_sections[section_id] = content
            except Exception as e2:
                logger.error(f"[Section {i}] Retry also failed: {e2}")
                part = f"## {i}. {section['title']}\n\n*[FAILED - token overflow]*"
                guide_parts.append(part)
                failed_sections.append(section_id)

        except Exception as e:
            logger.error(f"Section generation failed for '{section['title']}': {e}")
            part = f"## {i}. {section['title']}\n\n*Generation failed: {e}*"
            guide_parts.append(part)
            failed_sections.append(section_id)

    # Step 3: Section 15 -- Questions for Doctor (from prior sections text, NOT findings)
    print(f"  Section 15/{len(GUIDE_SECTIONS)}: {GUIDE_SECTIONS[14]['title']} [Haiku] (from prior sections)")
    try:
        prior_sections_text = "\n\n".join(
            f"## Section {i + 1}: {GUIDE_SECTIONS[i]['title']}\n{text}"
            for i, (key, text) in enumerate(generated_sections.items())
        )
        section_15_text = _generate_section_from_context(
            client, topic_title, GUIDE_SECTIONS[14], 15,
            context_text=prior_sections_text,
            model=model,
            advocate_ctx=advocate_ctx,
        )
        guide_parts.append(f"## 15. {GUIDE_SECTIONS[14]['title']}\n\n{section_15_text}")
    except Exception as e:
        logger.error(f"Section 15 generation failed: {e}")
        guide_parts.append(f"## 15. {GUIDE_SECTIONS[14]['title']}\n\n*Generation failed: {e}*")
        failed_sections.append("questions-for-doctor")

    # Step 4: Section 16 -- International Guidelines (Q9 + Q2 guidelines groups)
    guidelines_findings = section_findings.get("international-guidelines", [])
    print(f"  Section 16/{len(GUIDE_SECTIONS)}: {GUIDE_SECTIONS[15]['title']} [Haiku] ({len(guidelines_findings)} findings)")
    try:
        if guidelines_findings:
            guidelines_groups = [{"name": "all", "findings": guidelines_findings}]
            guidelines_text, _ = _format_grouped_findings(guidelines_groups, token_budget=180_000)
            section_16_text = _generate_section(
                client, topic_title, GUIDE_SECTIONS[15], 16,
                guidelines_text, len(guidelines_findings), model,
                cross_verify_report=cross_verify_report,
                oncologist_ctx=oncologist_ctx,
            )
        else:
            section_16_text = "*No guidelines findings available. This section needs additional research.*"
        guide_parts.append(f"## 16. {GUIDE_SECTIONS[15]['title']}\n\n{section_16_text}")
    except Exception as e:
        logger.error(f"Section 16 generation failed: {e}")
        guide_parts.append(f"## 16. {GUIDE_SECTIONS[15]['title']}\n\n*Generation failed: {e}*")
        failed_sections.append("international-guidelines")

    total_findings_used += len(guidelines_findings)
    logger.info(f"Total finding-section assignments: {total_findings_used} (from {len(findings)} unique findings)")

    if failed_sections:
        critical_failed = [s for s in failed_sections if s in CRITICAL_SECTIONS]
        if critical_failed:
            logger.error(f"UNSAFE: Critical sections failed: {critical_failed}")
        logger.warning(f"Failed sections: {failed_sections}")

    # Step 5: Executive summary from sections 1-3
    exec_summary = ""
    sections_1_3 = "\n\n".join(guide_parts[:3]) if len(guide_parts) >= 3 else "\n\n".join(guide_parts)
    try:
        print(f"  Executive summary: BEFORE ANYTHING ELSE [Haiku]")
        exec_msg = api_call(
            client,
            model=model,
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
        f.write(f"## BEFORE ANYTHING ELSE\n\n{exec_summary}\n\n---\n\n")
        f.write("\n\n".join(guide_parts))

    total_size = os.path.getsize(output_path)
    guide_status = "guide_needs_review" if failed_sections else "guide_ready"
    logger.info(
        f"Guide generated: {output_path} ({len(findings)} findings, "
        f"{len(GUIDE_SECTIONS)} sections, {total_size // 1024}KB, status={guide_status})"
    )


def verify_section_citations(section_text, provided_findings):
    """Verify citations and numbers in generated text are grounded in findings.

    Returns list of issues: [{type, severity, detail}]

    Issue types:
    - PHANTOM_CITATION (CRITICAL): [F:N] references a finding not in input
    - UNGROUNDED_NUMBER (MAJOR): number cited with [F:N] but not in that finding
    - UNCITED_NUMBER (WARNING): number in text with no nearby [F:N] citation
    """
    issues = []
    provided_ids = {f["id"] for f in provided_findings}
    provided_texts = {
        f["id"]: f"{f.get('title_english', '')} {f.get('summary_english', '')}"
        for f in provided_findings
    }

    # 1. Phantom citations
    cited_ids = [int(m) for m in re.findall(r'\[F:(\d+)\]', section_text)]
    for fid in set(cited_ids):
        if fid not in provided_ids:
            issues.append({
                "type": "PHANTOM_CITATION", "severity": "CRITICAL",
                "detail": f"[F:{fid}] cited but not in provided findings",
            })

    # 2. Numbers with unit suffixes: check grounding
    for match in re.finditer(r'(\d+\.?\d*)\s*(%|months?|mg|years?|weeks?)', section_text):
        num_str = match.group(1)
        pos = match.start()
        nearby = section_text[max(0, pos - 300):pos + 300]
        citation_match = re.search(r'\[F:(\d+)\]', nearby)

        if not citation_match:
            issues.append({
                "type": "UNCITED_NUMBER", "severity": "WARNING",
                "detail": f"{match.group(0)} at pos {pos} has no nearby citation",
            })
        else:
            fid = int(citation_match.group(1))
            if fid in provided_texts and num_str not in provided_texts[fid]:
                issues.append({
                    "type": "UNGROUNDED_NUMBER", "severity": "MAJOR",
                    "detail": f"{match.group(0)} cited as [F:{fid}] but '{num_str}' not in that finding",
                })

    return issues
