"""Iterative oncologist <-> advocate discovery loop (v6 lifecycle).

Input: diagnosis string only.
Output: conversation transcript, Q1-Q8 knowledge map, lifecycle scores.

The loop continues until the advocate scores all Q1-Q8 lifecycle questions >= 8.5/10,
or max_rounds is reached (default 5).
"""

import json
import logging
import os

import anthropic

from .cost_tracker import CostTracker
from .guide_generator import GUIDE_SECTIONS
from .utils import api_call, load_skill_context

logger = logging.getLogger(__name__)

SECTION_SCORE_THRESHOLD = 8.5
DEFAULT_MAX_ROUNDS = 5

# Resolve skill files relative to project root
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_MODULE_DIR, "..", "..", ".."))
SKILLS_DIR = os.path.join(_PROJECT_ROOT, ".claude", "skills")

# --- Tool schemas (API-enforced structured output) ---
# v6: Lifecycle Q1-Q8 structured schemas per SPEC.md 10.3

ONCOLOGIST_LIFECYCLE_TOOL = {
    "name": "submit_lifecycle_knowledge",
    "description": "Submit structured clinical knowledge organized by patient lifecycle questions Q1-Q8",
    "input_schema": {
        "type": "object",
        "properties": {
            "Q1_diagnostic": {
                "type": "object",
                "description": "Diagnosis confirmation: molecular tests, staging, subtypes",
                "properties": {
                    "molecular_tests": {"type": "array", "items": {"type": "object"}},
                    "staging": {"type": "string"},
                    "subtypes": {"type": "array", "items": {"type": "object"}},
                },
            },
            "Q2_treatment": {
                "type": "object",
                "description": "Standard treatment: approved drugs, guidelines, immunotherapy role",
                "properties": {
                    "approved_drugs": {"type": "array", "items": {"type": "object"}},
                    "guidelines": {"type": "object"},
                    "immunotherapy_role": {"type": "string"},
                },
            },
            "Q3_living": {
                "type": "object",
                "description": "Living with treatment: dosing, side effects, CYP, monitoring, emergencies, access",
                "properties": {
                    "per_drug": {"type": "array", "items": {"type": "object"}},
                    "emergency_signs": {"type": "array", "items": {"type": "string"}},
                    "nutrition": {"type": "string"},
                    "access": {"type": "object"},
                },
            },
            "Q4_metastases": {
                "type": "object",
                "description": "Common metastasis sites with frequency, detection, treatment",
                "properties": {
                    "sites": {"type": "array", "items": {"type": "object"}},
                },
            },
            "Q5_resistance": {
                "type": "object",
                "description": "Resistance mechanisms, next-line options, rebiopsy",
                "properties": {
                    "mechanisms": {"type": "array", "items": {"type": "object"}},
                    "median_time_months": {"type": "number"},
                    "next_line": {"type": "array", "items": {"type": "object"}},
                },
            },
            "Q6_pipeline": {
                "type": "object",
                "description": "Drugs in development, novel modalities, active trials",
                "properties": {
                    "drugs": {"type": "array", "items": {"type": "object"}},
                    "novel_modalities": {"type": "array", "items": {"type": "object"}},
                },
            },
            "Q7_mistakes": {
                "type": "object",
                "description": "Dangerous mistakes patients make",
                "properties": {
                    "items": {"type": "array", "items": {"type": "object"}},
                },
            },
            "Q8_community": {
                "type": "object",
                "description": "Patient communities and support resources",
                "properties": {
                    "resources": {"type": "array", "items": {"type": "object"}},
                },
            },
        },
        "required": ["Q1_diagnostic", "Q2_treatment", "Q3_living", "Q4_metastases",
                      "Q5_resistance", "Q6_pipeline", "Q7_mistakes", "Q8_community"],
    },
}

ONCOLOGIST_RESPOND_TOOL = {
    "name": "submit_oncologist_response",
    "description": "Submit answers to the patient advocate's questions with updated lifecycle knowledge",
    "input_schema": {
        "type": "object",
        "properties": {
            "answers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"},
                    },
                    "required": ["question", "answer"],
                },
            },
            "additional_knowledge": {
                "type": "object",
                "description": "New Q1-Q8 data not in the original submission",
                "properties": {
                    "Q1_diagnostic": {"type": "object"},
                    "Q2_treatment": {"type": "object"},
                    "Q3_living": {"type": "object"},
                    "Q4_metastases": {"type": "object"},
                    "Q5_resistance": {"type": "object"},
                    "Q6_pipeline": {"type": "object"},
                    "Q7_mistakes": {"type": "object"},
                    "Q8_community": {"type": "object"},
                },
            },
        },
        "required": ["answers", "additional_knowledge"],
    },
}

ADVOCATE_LIFECYCLE_TOOL = {
    "name": "submit_lifecycle_evaluation",
    "description": "Submit evaluation of the oncologist's lifecycle knowledge with Q1-Q8 scores",
    "input_schema": {
        "type": "object",
        "properties": {
            "scores": {
                "type": "object",
                "description": "Score per lifecycle question Q1-Q8",
                "properties": {
                    "Q1": {"type": "object", "properties": {"score": {"type": "number"}, "assessment": {"type": "string"}}, "required": ["score", "assessment"]},
                    "Q2": {"type": "object", "properties": {"score": {"type": "number"}, "assessment": {"type": "string"}}, "required": ["score", "assessment"]},
                    "Q3": {"type": "object", "properties": {"score": {"type": "number"}, "assessment": {"type": "string"}}, "required": ["score", "assessment"]},
                    "Q4": {"type": "object", "properties": {"score": {"type": "number"}, "assessment": {"type": "string"}}, "required": ["score", "assessment"]},
                    "Q5": {"type": "object", "properties": {"score": {"type": "number"}, "assessment": {"type": "string"}}, "required": ["score", "assessment"]},
                    "Q6": {"type": "object", "properties": {"score": {"type": "number"}, "assessment": {"type": "string"}}, "required": ["score", "assessment"]},
                    "Q7": {"type": "object", "properties": {"score": {"type": "number"}, "assessment": {"type": "string"}}, "required": ["score", "assessment"]},
                    "Q8": {"type": "object", "properties": {"score": {"type": "number"}, "assessment": {"type": "string"}}, "required": ["score", "assessment"]},
                },
                "required": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"],
            },
            "all_satisfied": {"type": "boolean"},
            "questions": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["scores", "all_satisfied", "questions"],
    },
}

# Backward compat aliases for tests that import old names
ONCOLOGIST_INITIAL_TOOL = ONCOLOGIST_LIFECYCLE_TOOL
ADVOCATE_EVAL_TOOL = ADVOCATE_LIFECYCLE_TOOL


# --- Sections summary for prompts ---


def _sections_summary() -> str:
    return "\n".join(
        f"- **{s['id']}**: {s['title']} -- {s['description']}"
        for s in GUIDE_SECTIONS
    )


# --- System prompts (built from skill files + task-specific instructions) ---


def _oncologist_system(skill_context: str, pre_search_context: str = "") -> str:
    pre_search_block = ""
    if pre_search_context:
        pre_search_block = f"""

=== REAL-WORLD RESEARCH DATA ===
The following findings come from PubMed, ClinicalTrials.gov, FDA, and other
authoritative sources. Use this data as your foundation. It may contain drugs,
trials, or data you were not previously aware of -- incorporate ALL of it.

{pre_search_context}

"""

    return f"""{skill_context}
{pre_search_block}
You are participating in a DISCOVERY CONVERSATION about a specific cancer diagnosis.
Your role: provide COMPLETE clinical knowledge organized by the PATIENT LIFECYCLE (Q1-Q8).

Answer these 8 questions as if a patient's life depends on completeness (it does):

Q1 DIAGNOSTIC: What tests confirm this diagnosis? Staging? Molecular subtypes and why they matter?
Q2 TREATMENT: What drugs are approved per line? Key trials (ORR%, PFS, OS)? ESMO vs NCCN differences? Immunotherapy role?
Q3 LIVING WITH TREATMENT: Per drug -- dosing, CYP profile, ALL side effects with %, monitoring tests, emergency signs. Access per country.
Q4 METASTASES: Top 3-5 metastasis sites with frequency %, detection, treatment (systemic + local options).
Q5 RESISTANCE: Specific mechanisms BY NAME, median time, Plan B/C/D with data, rebiopsy guidance.
Q6 PIPELINE: EVERY drug in development BY NAME -- phase, manufacturer, mechanism, targets resistance?, NCT number.
Q7 MISTAKES: Dangerous interactions, contraindicated supplements, myths. Format: MISTAKE / WHY DANGEROUS / ALTERNATIVE.
Q8 COMMUNITY: Patient communities specific to this diagnosis, caregiver resources.

MANDATORY per question:
- Q2: every approved drug with FDA/EMA status, any withdrawals
- Q3: CYP profile per drug, ALL side effects with percentages
- Q4: frequency % per metastasis site
- Q5: each resistance mechanism BY NAME
- Q6: each pipeline drug BY NAME with phase
- Q7: each dangerous interaction BY NAME

Use the submit_lifecycle_knowledge tool. Be EXHAUSTIVE.
Keep values short -- abbreviations, key facts, no long sentences."""


def _advocate_system(skill_context: str) -> str:
    return f"""{skill_context}

You are evaluating an oncologist's knowledge about a specific cancer diagnosis.
YOUR LIFE depends on this information being complete. Act accordingly.

You will receive the oncologist's lifecycle knowledge (Q1-Q8) and the ongoing conversation.

Score EACH lifecycle question Q1-Q8 (1-10):

Q1 DIAGNOSTIC: Are the tests complete? Is staging explained? Subtypes with significance?
Q2 TREATMENT: ALL approved drugs listed? Key trial data (ORR%, PFS, OS)? ESMO vs NCCN? Immunotherapy addressed?
Q3 LIVING: Per drug -- is dosing correct? CYP profile? ALL side effects with %? Monitoring? Emergency signs? Access info?
Q4 METASTASES: Top 3-5 sites with frequency %? Treatment per site?
Q5 RESISTANCE: Mechanisms BY NAME? Median time? Plan B/C/D CONCRETE? Rebiopsy guidance?
Q6 PIPELINE: EVERY drug in development BY NAME with phase? Novel modalities? Active trials with NCT?
Q7 MISTAKES: Specific dangerous interactions? Contraindicated supplements? Common myths?
Q8 COMMUNITY: Diagnosis-specific patient groups? Caregiver resources?

For any Q scoring below {SECTION_SCORE_THRESHOLD}, ask SPECIFIC questions.

The patient's journey:
- "What do I have exactly?" (Q1)
- "What is the BEST treatment RIGHT NOW?" (Q2)
- "What can HURT me?" (Q7, Q3)
- "When this stops working?" (Q5)
- "What's coming?" (Q6)
- "Can I get this in MY country?" (Q3-access)

Use the submit_lifecycle_evaluation tool.
Set all_satisfied to true ONLY when ALL Q1-Q8 score >= {SECTION_SCORE_THRESHOLD}."""


def _oncologist_respond_system(skill_context: str) -> str:
    return f"""{skill_context}

You are responding to specific questions from a patient advocate about a cancer diagnosis.
The advocate has identified gaps in your clinical knowledge.

Answer EACH question with SPECIFIC data: drug names, percentages, trial names, dates.
Do NOT give vague answers. If you don't know, say so explicitly.
Keep each answer concise -- key facts only, no lengthy explanations.

Use the submit_oncologist_response tool to submit your answers.
The additional_knowledge object should contain any NEW structured data (same format as
the original knowledge map: approved_drugs, pipeline_drugs, etc.) that was missing before."""


# --- Round functions ---


def _oncologist_initial(
    client: anthropic.Anthropic, diagnosis: str, model: str, cost: CostTracker,
    pre_search_context: str = "",
) -> dict:
    """Round 1: Oncologist generates lifecycle knowledge Q1-Q8 using tool use."""
    skill_context = load_skill_context(os.path.join(SKILLS_DIR, "oncologist.md"))
    message = api_call(
        client,
        model=model,
        max_tokens=12000,
        system=_oncologist_system(skill_context, pre_search_context=pre_search_context),
        messages=[{"role": "user", "content": (
            f"Diagnosis: {diagnosis}\n\n"
            f"Generate the complete lifecycle knowledge map (Q1-Q8)."
        )}],
        tools=[ONCOLOGIST_LIFECYCLE_TOOL],
        tool_choice={"type": "tool", "name": "submit_lifecycle_knowledge"},
    )
    cost.track(model, message.usage.input_tokens, message.usage.output_tokens)
    return message.content[0].input


def _advocate_evaluate(
    client: anthropic.Anthropic,
    diagnosis: str,
    knowledge_text: str,
    conversation_history: list[str],
    model: str,
    cost: CostTracker,
) -> dict:
    """Advocate evaluates current knowledge, scores Q1-Q8, asks questions."""
    skill_context = load_skill_context(os.path.join(SKILLS_DIR, "patient-advocate.md"))
    # Keep only last 2 exchanges to prevent O(n^2) token growth
    recent_history = conversation_history[-2:] if len(conversation_history) > 2 else conversation_history
    history_text = "\n\n---\n\n".join(recent_history) if recent_history else ""
    if len(conversation_history) > 2:
        history_text = f"[{len(conversation_history)-2} earlier exchanges omitted]\n\n" + history_text

    content = f"Diagnosis: {diagnosis}\n\nLifecycle Knowledge (Q1-Q8):\n{knowledge_text}"
    if history_text:
        content += f"\n\nConversation so far:\n{history_text}"

    message = api_call(
        client,
        model=model,
        max_tokens=6000,
        system=_advocate_system(skill_context),
        messages=[{"role": "user", "content": content}],
        tools=[ADVOCATE_LIFECYCLE_TOOL],
        tool_choice={"type": "tool", "name": "submit_lifecycle_evaluation"},
    )
    cost.track(model, message.usage.input_tokens, message.usage.output_tokens)
    return message.content[0].input


def _oncologist_respond(
    client: anthropic.Anthropic,
    diagnosis: str,
    questions: list[str],
    knowledge_text: str,
    model: str,
    cost: CostTracker,
) -> dict:
    """Oncologist responds to advocate's specific questions using tool use."""
    skill_context = load_skill_context(os.path.join(SKILLS_DIR, "oncologist.md"))
    questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    message = api_call(
        client,
        model=model,
        max_tokens=24000,
        system=_oncologist_respond_system(skill_context),
        messages=[{
            "role": "user",
            "content": (
                f"Diagnosis: {diagnosis}\n\n"
                f"Your previous knowledge:\n{knowledge_text}\n\n"
                f"Patient advocate's questions:\n{questions_text}"
            ),
        }],
        tools=[ONCOLOGIST_RESPOND_TOOL],
        tool_choice={"type": "tool", "name": "submit_oncologist_response"},
    )
    cost.track(model, message.usage.input_tokens, message.usage.output_tokens)
    logger.info(f"oncologist_respond: stop_reason={message.stop_reason}, output_tokens={message.usage.output_tokens}")
    return message.content[0].input


def _merge_knowledge(base: dict, additional: dict) -> dict:
    """Merge additional Q1-Q8 knowledge into base knowledge map.

    For each Q key, merges arrays by deduplicating on name fields.
    Non-array values (strings, objects) are overwritten if the additional
    value is non-empty.
    """
    for q_key in ("Q1_diagnostic", "Q2_treatment", "Q3_living", "Q4_metastases",
                   "Q5_resistance", "Q6_pipeline", "Q7_mistakes", "Q8_community"):
        if q_key not in additional or not additional[q_key]:
            continue
        if q_key not in base:
            base[q_key] = {}

        for field, new_val in additional[q_key].items():
            if isinstance(new_val, list) and new_val:
                existing = base[q_key].get(field, [])
                if not isinstance(existing, list):
                    existing = []
                # Dedup by name
                existing_names = set()
                for item in existing:
                    if isinstance(item, dict):
                        name = item.get("name", item.get("test", item.get("mechanism",
                               item.get("site", item.get("mistake", str(item))))))
                        existing_names.add(name.lower() if isinstance(name, str) else "")
                for new_item in new_val:
                    if isinstance(new_item, dict):
                        name = new_item.get("name", new_item.get("test", new_item.get("mechanism",
                               new_item.get("site", new_item.get("mistake", str(new_item))))))
                        if isinstance(name, str) and name.lower() not in existing_names:
                            existing.append(new_item)
                            existing_names.add(name.lower())
                    else:
                        existing.append(new_item)
                base[q_key][field] = existing
            elif isinstance(new_val, str) and new_val:
                base[q_key][field] = new_val
            elif isinstance(new_val, dict) and new_val:
                if field not in base[q_key]:
                    base[q_key][field] = {}
                base[q_key][field].update(new_val)
    return base


# --- Main entry point ---


def run_discovery(
    diagnosis: str,
    model: str,
    cost: CostTracker,
    api_key: str = "",
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    pre_search_context: str = "",
) -> dict:
    """Run iterative oncologist <-> advocate discovery loop.

    Args:
        diagnosis: The cancer diagnosis (e.g., "RET fusion-positive lung adenocarcinoma (NSCLC)")
        model: Claude model for discovery (should be Sonnet)
        cost: CostTracker instance
        api_key: Anthropic API key
        max_rounds: Maximum discovery rounds (default 5)
        pre_search_context: Formatted findings from pre-search phase (injected into oncologist prompts)

    Returns:
        {
            "converged": bool,
            "rounds": int,
            "knowledge_map": dict,       # Q1-Q8 structured
            "section_scores": dict,      # backward compat alias for lifecycle_scores
            "lifecycle_scores": dict,    # Q1-Q8 scores
            "conversation": list[str],
            "final_questions": list[str],
        }
    """
    empty = {"converged": False, "rounds": 0, "knowledge_map": {},
             "section_scores": {}, "lifecycle_scores": {},
             "conversation": [], "final_questions": []}
    if not api_key:
        logger.warning("No API key for discovery, returning empty result")
        return empty

    client = anthropic.Anthropic(api_key=api_key)
    conversation: list[str] = []
    knowledge_map: dict = {}
    lifecycle_scores: dict = {}

    # Step 1: Oncologist initial lifecycle knowledge
    logger.info("Discovery Round 1: Oncologist initial lifecycle knowledge (Q1-Q8)...")
    knowledge_map = _oncologist_initial(client, diagnosis, model, cost,
                                        pre_search_context=pre_search_context)
    if not knowledge_map:
        logger.error("Oncologist returned empty knowledge map")
        return empty

    knowledge_text = json.dumps(knowledge_map, indent=2)
    conversation.append(f"ONCOLOGIST (initial):\n{knowledge_text}")

    questions: list[str] = []
    for round_num in range(1, max_rounds + 1):
        logger.info(f"Discovery Round {round_num}: Advocate evaluating Q1-Q8...")

        # Advocate evaluates per Q1-Q8
        evaluation = _advocate_evaluate(
            client, diagnosis, knowledge_text, conversation, model, cost
        )
        lifecycle_scores = evaluation.get("scores", {})
        questions = evaluation.get("questions", [])
        all_satisfied = evaluation.get("all_satisfied", False)

        conversation.append(
            f"ADVOCATE (round {round_num}):\n"
            f"Scores: {json.dumps(lifecycle_scores, indent=2)}\n"
            f"Questions: {json.dumps(questions)}\n"
            f"Satisfied: {all_satisfied}"
        )

        # Log low scores
        low_qs = [
            f"{qid}: {info.get('score', 0)}"
            for qid, info in lifecycle_scores.items()
            if isinstance(info, dict) and info.get("score", 0) < SECTION_SCORE_THRESHOLD
        ]
        if low_qs:
            logger.info(f"  Low lifecycle scores: {', '.join(low_qs)}")

        if all_satisfied or not questions:
            logger.info(f"Discovery converged after {round_num} rounds")
            return {
                "converged": True,
                "rounds": round_num,
                "knowledge_map": knowledge_map,
                "lifecycle_scores": lifecycle_scores,
                "section_scores": lifecycle_scores,  # backward compat
                "conversation": conversation,
                "final_questions": [],
            }

        # Oncologist responds to questions
        if not cost.has_budget(reserve_usd=0.50):
            logger.warning("Budget running low, stopping discovery loop")
            break

        logger.info(f"Discovery Round {round_num}: Oncologist responding to {len(questions)} questions...")
        response = _oncologist_respond(client, diagnosis, questions, knowledge_text, model, cost)

        # Merge new Q1-Q8 knowledge
        additional = response.get("additional_knowledge", {})
        if additional:
            knowledge_map = _merge_knowledge(knowledge_map, additional)
            knowledge_text = json.dumps(knowledge_map, indent=2)

        if response:
            conversation.append(
                f"ONCOLOGIST (round {round_num} response):\n"
                f"{json.dumps(response.get('answers', []), indent=2)}"
            )
        else:
            logger.warning(f"Discovery Round {round_num}: oncologist response empty")

    logger.warning(f"Discovery did not converge after {max_rounds} rounds")
    return {
        "converged": False,
        "rounds": max_rounds,
        "knowledge_map": knowledge_map,
        "lifecycle_scores": lifecycle_scores,
        "section_scores": lifecycle_scores,  # backward compat
        "conversation": conversation,
        "final_questions": questions,
    }
