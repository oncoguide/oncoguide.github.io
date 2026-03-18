"""Iterative oncologist <-> advocate discovery loop.

Input: diagnosis string only.
Output: conversation transcript, knowledge map, section scores.

The loop continues until the patient-advocate scores all 15 sections >= 8.5/10,
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

ONCOLOGIST_INITIAL_TOOL = {
    "name": "submit_knowledge_map",
    "description": "Submit the complete Clinical Knowledge Map for this cancer diagnosis",
    "input_schema": {
        "type": "object",
        "properties": {
            "approved_drugs": {"type": "array", "items": {"type": "object"}},
            "pipeline_drugs": {"type": "array", "items": {"type": "object"}},
            "landmark_trials": {"type": "array", "items": {"type": "object"}},
            "institutional_protocols": {"type": "array", "items": {"type": "object"}},
            "side_effects": {"type": "array", "items": {"type": "object"}},
            "resistance": {"type": "array", "items": {"type": "object"}},
            "guidelines": {"type": "array", "items": {"type": "object"}},
            "testing": {"type": "array", "items": {"type": "object"}},
        },
        "required": [
            "approved_drugs", "pipeline_drugs", "landmark_trials",
            "institutional_protocols", "side_effects", "resistance",
            "guidelines", "testing",
        ],
    },
}

ONCOLOGIST_RESPOND_TOOL = {
    "name": "submit_oncologist_response",
    "description": "Submit answers to the patient advocate's questions with updated clinical knowledge",
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
                "properties": {
                    "approved_drugs": {"type": "array", "items": {"type": "object"}},
                    "pipeline_drugs": {"type": "array", "items": {"type": "object"}},
                    "landmark_trials": {"type": "array", "items": {"type": "object"}},
                    "institutional_protocols": {"type": "array", "items": {"type": "object"}},
                    "side_effects": {"type": "array", "items": {"type": "object"}},
                    "resistance": {"type": "array", "items": {"type": "object"}},
                    "guidelines": {"type": "array", "items": {"type": "object"}},
                    "testing": {"type": "array", "items": {"type": "object"}},
                },
            },
        },
        "required": ["answers", "additional_knowledge"],
    },
}

ADVOCATE_EVAL_TOOL = {
    "name": "submit_evaluation",
    "description": "Submit evaluation of the oncologist's knowledge with section scores and questions",
    "input_schema": {
        "type": "object",
        "properties": {
            "section_scores": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "score": {"type": "number"},
                        "assessment": {"type": "string"},
                    },
                    "required": ["score", "assessment"],
                },
            },
            "questions": {"type": "array", "items": {"type": "string"}},
            "all_satisfied": {"type": "boolean"},
        },
        "required": ["section_scores", "questions", "all_satisfied"],
    },
}


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
Your role: provide COMPLETE clinical knowledge for a patient education guide.

Think like you are preparing a tumor board presentation. You need EVERYTHING:

1. APPROVED DRUGS: Every drug approved worldwide. For each: generic name, brand, FDA/EMA status, approval date, ANY withdrawals or market exits.
2. PIPELINE DRUGS: EVERY drug in development for this target. Be EXHAUSTIVE: next-gen inhibitors, PROTACs, bispecifics, ADCs, combinations. For each: drug name/code, manufacturer, mechanism, phase, key trial, NCT number.
3. LANDMARK TRIALS: Every major trial. For each: name, drug, phase, ORR%, PFS months, OS months, intracranial ORR%.
4. INSTITUTIONAL PROTOCOLS: How MD Anderson, MSK, Gustave Roussy ACTUALLY treat this NOW. Sequencing, combinations.
5. SIDE EFFECTS: Every drug's side effects with frequency %. Include under-reported (hyperglycemia, QTc, taste changes).
6. RESISTANCE: Specific mutations, bypass pathways, median time, what to do next.
7. GUIDELINES: Current ESMO and NCCN recommendations AND differences.
8. TESTING: Required molecular tests, methods, turnaround times.

Use the submit_knowledge_map tool to submit your complete findings.
Be EXHAUSTIVE. Missing a drug or trial means a patient might not learn about their best option.
Keep values short -- abbreviations, no long sentences."""


def _advocate_system(skill_context: str) -> str:
    sections = _sections_summary()
    return f"""{skill_context}

You are evaluating an oncologist's knowledge about a specific cancer diagnosis.
YOUR LIFE depends on this information being complete. Act accordingly.

You will receive the oncologist's clinical knowledge and the ongoing conversation.

YOUR JOB:
1. Evaluate completeness for EACH of these 16 guide sections:
{sections}

2. Score each section 1-10 based on:
   - Does the oncologist's knowledge contain enough data to write a comprehensive section?
   - Are there specific numbers (%, months, doses)?
   - Are ALL relevant drugs/trials/effects listed?

3. For sections scoring below {SECTION_SCORE_THRESHOLD}, ask SPECIFIC questions.

4. Follow YOUR natural journey as the patient:
   - "What do I have exactly? How serious is it?"
   - "What is the BEST treatment RIGHT NOW?"
   - "What side effects will hit me? What do doctors FORGET to mention?"
   - "When this stops working, what's my Plan B/C/D?"
   - "What new drugs are being tested? When can I get them?"
   - "Can I get this in my country? Cross-border options?"
   - "How do I LIVE with this?"

5. Challenge the pipeline section HARD: is EVERY drug listed by name?

Use the submit_evaluation tool to submit your evaluation.
Set all_satisfied to true ONLY when ALL 16 sections score >= {SECTION_SCORE_THRESHOLD}."""


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
    """Round 1: Oncologist generates initial Clinical Knowledge Map using tool use."""
    skill_context = load_skill_context(os.path.join(SKILLS_DIR, "oncologist.md"))
    message = api_call(
        client,
        model=model,
        max_tokens=12000,
        system=_oncologist_system(skill_context, pre_search_context=pre_search_context),
        messages=[{"role": "user", "content": (
            f"Diagnosis: {diagnosis}\n\n"
            f"Generate the complete Clinical Knowledge Map."
        )}],
        tools=[ONCOLOGIST_INITIAL_TOOL],
        tool_choice={"type": "tool", "name": "submit_knowledge_map"},
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
    """Advocate evaluates current knowledge, scores sections, asks questions."""
    skill_context = load_skill_context(os.path.join(SKILLS_DIR, "patient-advocate.md"))
    # Keep only last 2 exchanges to prevent O(n^2) token growth
    recent_history = conversation_history[-2:] if len(conversation_history) > 2 else conversation_history
    history_text = "\n\n---\n\n".join(recent_history) if recent_history else ""
    if len(conversation_history) > 2:
        history_text = f"[{len(conversation_history)-2} earlier exchanges omitted]\n\n" + history_text

    content = f"Diagnosis: {diagnosis}\n\nClinical Knowledge:\n{knowledge_text}"
    if history_text:
        content += f"\n\nConversation so far:\n{history_text}"

    message = api_call(
        client,
        model=model,
        max_tokens=6000,
        system=_advocate_system(skill_context),
        messages=[{"role": "user", "content": content}],
        tools=[ADVOCATE_EVAL_TOOL],
        tool_choice={"type": "tool", "name": "submit_evaluation"},
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
    """Merge additional knowledge into base knowledge map."""
    for key in ("approved_drugs", "pipeline_drugs", "landmark_trials",
                "institutional_protocols", "side_effects", "resistance",
                "guidelines", "testing"):
        if key in additional and additional[key]:
            existing = base.get(key, [])
            # Simple dedup by checking if item already exists (by name or first field)
            existing_names = set()
            for item in existing:
                name = item.get("name", item.get("test", item.get("mechanism", str(item))))
                existing_names.add(name.lower() if isinstance(name, str) else "")
            for new_item in additional[key]:
                name = new_item.get("name", new_item.get("test", new_item.get("mechanism", str(new_item))))
                if isinstance(name, str) and name.lower() not in existing_names:
                    existing.append(new_item)
                    existing_names.add(name.lower())
            base[key] = existing
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
            "knowledge_map": dict,
            "section_scores": dict,
            "conversation": list[str],
            "final_questions": list[str],
        }
    """
    if not api_key:
        logger.warning("No API key for discovery, returning empty result")
        return {"converged": False, "rounds": 0, "knowledge_map": {},
                "section_scores": {}, "conversation": [], "final_questions": []}

    client = anthropic.Anthropic(api_key=api_key)
    conversation: list[str] = []
    knowledge_map: dict = {}
    section_scores: dict = {}

    # Step 1: Oncologist initial knowledge dump
    logger.info("Discovery Round 1: Oncologist initial knowledge map...")
    knowledge_map = _oncologist_initial(client, diagnosis, model, cost,
                                        pre_search_context=pre_search_context)
    if not knowledge_map:
        logger.error("Oncologist returned empty knowledge map")
        return {"converged": False, "rounds": 0, "knowledge_map": {},
                "section_scores": {}, "conversation": [], "final_questions": []}

    knowledge_text = json.dumps(knowledge_map, indent=2)
    conversation.append(f"ONCOLOGIST (initial):\n{knowledge_text}")

    questions: list[str] = []
    for round_num in range(1, max_rounds + 1):
        logger.info(f"Discovery Round {round_num}: Advocate evaluating...")

        # Advocate evaluates
        evaluation = _advocate_evaluate(
            client, diagnosis, knowledge_text, conversation, model, cost
        )
        section_scores = evaluation.get("section_scores", {})
        questions = evaluation.get("questions", [])
        all_satisfied = evaluation.get("all_satisfied", False)

        conversation.append(
            f"ADVOCATE (round {round_num}):\n"
            f"Scores: {json.dumps(section_scores, indent=2)}\n"
            f"Questions: {json.dumps(questions)}\n"
            f"Satisfied: {all_satisfied}"
        )

        # Log scores
        low_sections = [
            f"{sid}: {info.get('score', 0)}"
            for sid, info in section_scores.items()
            if isinstance(info, dict) and info.get("score", 0) < SECTION_SCORE_THRESHOLD
        ]
        if low_sections:
            logger.info(f"  Low sections: {', '.join(low_sections)}")

        if all_satisfied or not questions:
            logger.info(f"Discovery converged after {round_num} rounds")
            return {
                "converged": True,
                "rounds": round_num,
                "knowledge_map": knowledge_map,
                "section_scores": section_scores,
                "conversation": conversation,
                "final_questions": [],
            }

        # Oncologist responds to questions
        if not cost.has_budget(reserve_usd=0.50):
            logger.warning("Budget running low, stopping discovery loop")
            break

        logger.info(f"Discovery Round {round_num}: Oncologist responding to {len(questions)} questions...")
        response = _oncologist_respond(client, diagnosis, questions, knowledge_text, model, cost)

        # Merge new knowledge
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
            logger.warning(f"Discovery Round {round_num}: oncologist response empty, skipping conversation update")

    logger.warning(f"Discovery did not converge after {max_rounds} rounds")
    return {
        "converged": False,
        "rounds": max_rounds,
        "knowledge_map": knowledge_map,
        "section_scores": section_scores,
        "conversation": conversation,
        "final_questions": questions,
    }
