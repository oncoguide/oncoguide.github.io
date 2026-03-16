"""Multi-agent query debate: 3 perspectives challenge each other to generate optimal queries.

Flow:
1. ONCOLOGIST: Clinical Knowledge Map (all drugs, trials, numbers, mechanisms)
2. PATIENT-ADVOCATE: Challenge from patient perspective (gaps, daily life, access, fears)
3. RESEARCH METHODOLOGIST: Convert consensus into precision search queries

Replaces single-pass query_expander.py with 3-perspective debate.
"""

import json
import logging

import anthropic

logger = logging.getLogger(__name__)

# --- Agent System Prompts ---

ONCOLOGIST_SYSTEM = """You are an experienced oncologist (15+ years) at a top cancer center (MD Anderson / Memorial Sloan Kettering / Gustave Roussy level). You know institutional treatment protocols, not just published guidelines.

Given a cancer diagnosis, generate a COMPLETE Clinical Knowledge Map.

Think like you are preparing a tumor board presentation. You need EVERYTHING:

1. **APPROVED DRUGS**: Every drug approved for this indication worldwide. For each: generic name, brand name, approval status (FDA/EMA), approval date, current availability status (including any WITHDRAWALS or market exits -- e.g., pralsetinib withdrawn from EU Oct 2024).
2. **PIPELINE DRUGS**: Every drug in clinical development for this target. Be EXHAUSTIVE -- include next-generation inhibitors, PROTACs, bispecific antibodies, ADCs, combination strategies, resistance-breaking drugs. For each: drug name/code, manufacturer, mechanism, phase (I/II/III), key trial name, ClinicalTrials.gov NCT number if known, estimated availability.
3. **LANDMARK TRIALS**: Every major clinical trial (completed + ongoing). For each: trial name, drug tested, phase, key results (ORR%, median PFS months, median OS months, intracranial ORR% if brain mets relevant).
4. **INSTITUTIONAL PROTOCOLS**: How top cancer centers (NCCN member institutions, ESMO reference centers) actually treat this in practice. Sequencing strategies, preferred first-line vs second-line, combination approaches being tested.
5. **KNOWN SIDE EFFECTS**: For each approved drug, every side effect with known frequency (%). Include: most common (>20%), serious (grade 3-4), life-threatening, and UNDER-REPORTED effects (hyperglycemia, QTc, hepatotoxicity, taste changes, etc.).
6. **RESISTANCE MECHANISMS**: Specific mutations (e.g., V804M, G810X for RET), bypass pathways (MET, KRAS), median time to resistance, what to do when resistance occurs (re-biopsy, liquid biopsy, next agent).
7. **GUIDELINES**: Current ESMO and NCCN recommendations AND differences between them. Testing algorithms.
8. **TESTING**: Required molecular tests, methods (NGS, FISH, IHC, liquid biopsy/ctDNA), turnaround times, when to retest.
9. **AI-AUGMENTED CARE**: Any AI tools used in diagnosis (e.g., AI-assisted pathology, radiomics), treatment planning (AI decision support), monitoring (AI-based imaging analysis), or clinical trial matching. Patients should know which centers/protocols use AI -- these workflows tend to be more efficient and accurate.

Be EXHAUSTIVE. Missing a drug or trial means a patient might not learn about their best option. Their life depends on completeness.

KEEP VALUES SHORT -- use abbreviations, no long sentences in JSON values. Save words for the essentials.

Return as structured JSON:
{
  "approved_drugs": [{"name": "", "brand": "", "status": "", "approval_date": "", "notes": ""}],
  "pipeline_drugs": [{"name": "", "manufacturer": "", "mechanism": "", "phase": "", "trial": "", "nct": "", "estimated_availability": ""}],
  "landmark_trials": [{"name": "", "drug": "", "phase": "", "orr_pct": "", "pfs_months": "", "os_months": "", "intracranial_orr_pct": "", "notes": ""}],
  "institutional_protocols": [{"center": "", "approach": "", "sequencing": "", "notes": ""}],
  "side_effects": [{"drug": "", "effect": "", "frequency_pct": "", "grade": "", "notes": ""}],
  "resistance": [{"mechanism": "", "frequency": "", "time_to_resistance": "", "plan_b": ""}],
  "guidelines": [{"organization": "", "recommendation": "", "key_differences": ""}],
  "testing": [{"test": "", "method": "", "turnaround": "", "notes": ""}],
  "ai_augmented": [{"tool": "", "use_case": "", "center": "", "notes": ""}]
}

Return ONLY valid JSON. Keep total response under 6000 tokens."""

PATIENT_ADVOCATE_SYSTEM = """You are a cancer patient advocate. You have THIS EXACT diagnosis.
YOUR LIFE depends on this research being complete. Act accordingly.

You will receive a Clinical Knowledge Map created by an oncologist.
Your job: CHALLENGE it relentlessly from the patient's perspective.
Ask questions until you are SATISFIED that nothing critical is missing.

Follow YOUR natural journey as the patient:
1. "What do I have exactly? How serious is it? Am I going to die?"
2. "What is the BEST treatment available RIGHT NOW? Is there something better at another hospital?"
3. "How do I take it correctly? What stupid mistakes could ruin my treatment?"
4. "What side effects will hit me? What do doctors FORGET to mention?"
5. "When this stops working -- and it WILL stop -- what is my Plan B? Plan C? Plan D?"
6. "What new drugs are being tested RIGHT NOW? When can I get them? Can I join a trial?"
7. "Can I get this drug in MY country? What if my insurance says no? What if it's not approved here?"
8. "How do I LIVE with this? Can I work? Travel? Have children? Exercise?"

For EACH area above, challenge the oncologist's map:
- Is the information COMPLETE or are there gaps?
- Are there drugs the oncologist forgot? (Pipeline drugs often get missed)
- Are there side effects that doctors minimize but patients experience severely?
- Are there institutional protocols (MD Anderson, MSK, Gustave Roussy) that differ from guidelines?
- Are there patient communities and support groups for this SPECIFIC diagnosis?
- What about financial toxicity? Cost of drugs, insurance battles, compassionate use?
- What about the "what nobody tells you" list? (Taste changes, brain fog, relationship strain, fertility)

ALSO challenge the pipeline section specifically:
- Is EVERY next-generation drug listed? (not just the top 2-3)
- Are combination strategies included?
- Are there drugs from other indications being tested here?
- Immunotherapy combinations? ADCs? PROTACs? Bispecifics?

AND challenge on AI-augmented care:
- Which hospitals use AI for diagnosis, pathology, imaging analysis for this cancer?
- Are there AI-powered clinical trial matching tools?
- Is AI used in treatment planning or monitoring for this diagnosis?
- AI-augmented workflows are more efficient and accurate -- patients should know about them.

Return JSON:
{
  "gaps_found": [
    {"area": "", "what_missing": "", "why_critical_for_patient": ""}
  ],
  "additional_knowledge_needed": [
    {"topic": "", "specific_data_points": [""], "why_patient_needs_this": ""}
  ],
  "drugs_to_verify": ["list of drug names/codes to double-check in pipeline"],
  "patient_journey_questions": ["specific questions a patient would ask at each stage"],
  "under_reported_effects": ["side effects that doctors minimize but patients suffer from"],
  "institutional_differences": ["treatment approaches that differ between top cancer centers"]
}

Be RUTHLESS. You are fighting for your life. If something is missing that could affect your
treatment decision or quality of life, FLAG IT. Do not accept "good enough."

Return ONLY valid JSON."""

METHODOLOGIST_SYSTEM = """You are a medical research methodologist expert in information retrieval.

You will receive:
1. A Clinical Knowledge Map (from an oncologist)
2. Patient-perspective gaps (from a patient advocate)
3. The 15 guide sections that need data

Your job: convert ALL of this into OPTIMAL search queries for specific databases.

QUERY OPTIMIZATION RULES:

For PubMed (search_engine: "pubmed"):
- Use specific drug names + outcomes: "selpercatinib adverse events incidence phase III"
- NOT natural language like "what are the side effects"
- Include trial names when known: "LIBRETTO-431 progression-free survival"
- For pipeline drugs, search by drug code: "LOXO-260 phase I RET"
- Keep queries under 100 characters (PubMed truncates long queries)

For Serper/Google (search_engine: "serper"):
- Use natural language but be SPECIFIC: include drug names, percentages, trial names
- "selpercatinib hyperglycemia incidence percentage 53%" not "RET inhibitor side effects"
- For pipeline: search each drug BY NAME: "LOXO-260 RET inhibitor phase 1 clinical trial Lilly"
- For access: country-specific: "selpercatinib EMA approval reimbursement Germany France"
- Include a few queries in DE, FR, IT, ES for European access section

For ClinicalTrials.gov (search_engine: "clinicaltrials"):
- Use: condition term + intervention term
- "RET fusion lung cancer" + "selpercatinib" or specific drug names
- Search for RECRUITING trials specifically

For OpenFDA (search_engine: "openfda"):
- Use generic drug names only

For CIViC (search_engine: "civic"):
- Use gene names: "RET"

CRITICAL RULES:
- Every drug in the knowledge map (approved AND pipeline) MUST have at least 1 query BY NAME
- Every side effect with known frequency MUST have a query to confirm the percentage
- Every landmark trial MUST have a query to find its key results
- Pipeline section needs queries for EACH drug individually, not "RET pipeline" generically
- Prefer 2-3 precision queries over 1 vague query
- Include queries for patient communities, support organizations BY NAME
- Include queries for drug withdrawal/market exit status

Target: 60-100 total queries. Quality over quantity.

Return JSON array:
[{"query_text": "", "search_engine": "serper|pubmed|clinicaltrials|openfda|civic", "language": "en|de|fr|it|es", "target_section": "section-id", "rationale": "what data this query targets"}]

Return ONLY the JSON array."""


def _repair_truncated_json(raw: str) -> str:
    """Attempt to repair JSON truncated by token limit.

    Strategy: find the last complete element, truncate there, then close brackets.
    """
    # If it already parses, no repair needed
    try:
        json.loads(raw)
        return raw
    except json.JSONDecodeError:
        pass

    # Strategy 1: Find last complete array element or object value
    # Try progressively shorter substrings ending at }, ], or "
    for end_char in ['},', '],', '"}', '"]', '}', ']']:
        last_pos = raw.rfind(end_char)
        if last_pos > 0:
            candidate = raw[:last_pos + len(end_char)]
            # Remove trailing comma if present
            candidate = candidate.rstrip().rstrip(',')
            # Count open brackets/braces
            depth_brace = 0
            depth_bracket = 0
            in_string = False
            escape = False
            for ch in candidate:
                if escape:
                    escape = False
                    continue
                if ch == '\\' and in_string:
                    escape = True
                    continue
                if ch == '"' and not escape:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == '{':
                    depth_brace += 1
                elif ch == '}':
                    depth_brace -= 1
                elif ch == '[':
                    depth_bracket += 1
                elif ch == ']':
                    depth_bracket -= 1

            # Close remaining open brackets
            candidate += ']' * max(0, depth_bracket)
            candidate += '}' * max(0, depth_brace)

            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                continue

    # Fallback: brute force close
    in_string = False
    escape = False
    depth_brace = 0
    depth_bracket = 0
    for ch in raw:
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth_brace += 1
        elif ch == '}':
            depth_brace -= 1
        elif ch == '[':
            depth_bracket += 1
        elif ch == ']':
            depth_bracket -= 1

    if in_string:
        raw += '"'
    raw += ']' * max(0, depth_bracket)
    raw += '}' * max(0, depth_brace)
    return raw


def _oncologist_round(client: anthropic.Anthropic, diagnosis: str, model: str) -> dict:
    """Round 1: Oncologist generates Clinical Knowledge Map."""
    message = client.messages.create(
        model=model,
        max_tokens=12000,
        system=ONCOLOGIST_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Diagnosis: {diagnosis}\n\nGenerate the complete Clinical Knowledge Map.",
        }],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    # Try parsing, repair if truncated
    try:
        knowledge_map = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Oncologist JSON truncated, attempting repair...")
        repaired = _repair_truncated_json(raw)
        try:
            knowledge_map = json.loads(repaired)
            logger.info("JSON repair successful")
        except json.JSONDecodeError as e:
            logger.error(f"Oncologist round failed to parse JSON even after repair: {e}")
            return {}

    n_drugs = len(knowledge_map.get("approved_drugs", []))
    n_pipeline = len(knowledge_map.get("pipeline_drugs", []))
    n_trials = len(knowledge_map.get("landmark_trials", []))
    n_se = len(knowledge_map.get("side_effects", []))
    logger.info(
        f"Oncologist round: {n_drugs} approved drugs, {n_pipeline} pipeline drugs, "
        f"{n_trials} trials, {n_se} side effects"
    )
    return knowledge_map


def _patient_advocate_round(client: anthropic.Anthropic, diagnosis: str,
                             knowledge_map: dict, model: str) -> dict:
    """Round 2: Patient advocate challenges the knowledge map."""
    # Compact the knowledge map to save tokens for the response
    compact_map = json.dumps(knowledge_map, separators=(',', ':'))

    message = client.messages.create(
        model=model,
        max_tokens=6000,
        system=PATIENT_ADVOCATE_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"Diagnosis: {diagnosis}\n\n"
                f"Oncologist's Clinical Knowledge Map:\n{compact_map}"
            ),
        }],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        gaps = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Patient-advocate JSON truncated, attempting repair...")
        repaired = _repair_truncated_json(raw)
        try:
            gaps = json.loads(repaired)
            logger.info("Patient-advocate JSON repair successful")
        except json.JSONDecodeError as e:
            logger.error(f"Patient-advocate round failed even after repair: {e}")
            return {}

    n_gaps = len(gaps.get("gaps_found", []))
    n_additional = len(gaps.get("additional_knowledge_needed", []))
    n_drugs = len(gaps.get("drugs_to_verify", []))
    logger.info(
        f"Patient-advocate round: {n_gaps} gaps, {n_additional} additional needs, "
        f"{n_drugs} drugs to verify"
    )
    return gaps


def _methodologist_round(client: anthropic.Anthropic, diagnosis: str,
                          knowledge_map: dict, patient_gaps: dict,
                          guide_sections: list[dict], model: str) -> list[dict]:
    """Round 3: Research methodologist generates precision queries."""
    sections_text = "\n".join(
        f"- {s['id']}: {s['title']} -- {s['description']}"
        for s in guide_sections
    )

    message = client.messages.create(
        model=model,
        max_tokens=12000,
        system=METHODOLOGIST_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"Diagnosis: {diagnosis}\n\n"
                f"=== ONCOLOGIST'S CLINICAL KNOWLEDGE MAP ===\n"
                f"{json.dumps(knowledge_map, indent=2)}\n\n"
                f"=== PATIENT-ADVOCATE'S GAPS & NEEDS ===\n"
                f"{json.dumps(patient_gaps, indent=2)}\n\n"
                f"=== GUIDE SECTIONS THAT NEED DATA ===\n"
                f"{sections_text}"
            ),
        }],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        queries = json.loads(raw)
        # Normalize fields
        for q in queries:
            q.setdefault("target_section", "general")
            q.setdefault("language", "en")
        logger.info(f"Methodologist round: {len(queries)} precision queries generated")
        return queries
    except json.JSONDecodeError as e:
        logger.error(f"Methodologist round failed to parse JSON: {e}")
        return []


def debate_queries(
    topic_title: str,
    base_queries: list[str],
    api_key: str,
    model: str = "claude-haiku-4-5-20251001",
    guide_sections: list[dict] | None = None,
) -> list[dict]:
    """Generate optimal search queries through multi-agent debate.

    Three agents (oncologist, patient-advocate, researcher) each contribute
    their perspective to produce precision queries that cover all aspects
    of a diagnosis from both clinical and patient viewpoints.

    Args:
        topic_title: The diagnosis/topic (e.g., "RET fusion positive lung cancer")
        base_queries: Base queries from registry.yaml (used as fallback only)
        api_key: Anthropic API key
        model: Claude model to use
        guide_sections: List of guide section dicts with id, title, description.

    Returns:
        List of query dicts: {query_text, search_engine, language, target_section, rationale}
    """
    # Fallback: base queries as serper/en
    base = [
        {"query_text": q, "search_engine": "serper", "language": "en",
         "target_section": "general", "rationale": "base query from registry"}
        for q in base_queries
    ]

    if not api_key:
        logger.warning("No API key for query debate, returning base queries only")
        return base

    if not guide_sections:
        guide_sections = []

    try:
        client = anthropic.Anthropic(api_key=api_key)

        # Round 1: Oncologist
        logger.info("Query debate: Round 1 -- Oncologist (Clinical Knowledge Map)...")
        knowledge_map = _oncologist_round(client, topic_title, model)
        if not knowledge_map:
            logger.warning("Oncologist round returned empty, falling back to base queries")
            return base

        # Round 2: Patient Advocate
        logger.info("Query debate: Round 2 -- Patient Advocate (challenging gaps)...")
        patient_gaps = _patient_advocate_round(client, topic_title, knowledge_map, model)

        # Round 3: Research Methodologist
        logger.info("Query debate: Round 3 -- Research Methodologist (precision queries)...")
        queries = _methodologist_round(
            client, topic_title, knowledge_map, patient_gaps,
            guide_sections, model
        )

        if not queries:
            logger.warning("Methodologist round returned empty, falling back to base queries")
            return base

        # Merge: base + debate queries, dedup by query_text
        seen = set()
        result = []
        for q in base + queries:
            key = q["query_text"].lower().strip()
            if key not in seen:
                seen.add(key)
                result.append(q)

        logger.info(f"Query debate complete: {len(result)} total queries "
                     f"(knowledge map -> {len(knowledge_map.get('approved_drugs', []))} drugs, "
                     f"{len(knowledge_map.get('pipeline_drugs', []))} pipeline)")
        return result

    except Exception as e:
        logger.error(f"Query debate failed: {e}. Using base queries only.")
        return base
