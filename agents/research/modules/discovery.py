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
from .utils import load_skill_context

logger = logging.getLogger(__name__)

SECTION_SCORE_THRESHOLD = 8.5
DEFAULT_MAX_ROUNDS = 5

# Resolve skill files relative to project root
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_MODULE_DIR, "..", "..", ".."))
SKILLS_DIR = os.path.join(_PROJECT_ROOT, ".claude", "skills")

# --- Sections summary for prompts ---


def _sections_summary() -> str:
    return "\n".join(
        f"- **{s['id']}**: {s['title']} -- {s['description']}"
        for s in GUIDE_SECTIONS
    )


# --- System prompts (built from skill files + task-specific instructions) ---


def _oncologist_system(skill_context: str) -> str:
    return f"""{skill_context}

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

Return as structured JSON with keys: approved_drugs, pipeline_drugs, landmark_trials, institutional_protocols, side_effects, resistance, guidelines, testing.

Be EXHAUSTIVE. Missing a drug or trial means a patient might not learn about their best option. Keep values short -- abbreviations, no long sentences. Return ONLY valid JSON."""


def _advocate_system(skill_context: str) -> str:
    sections = _sections_summary()
    return f"""{skill_context}

You are evaluating an oncologist's knowledge about a specific cancer diagnosis.
YOUR LIFE depends on this information being complete. Act accordingly.

You will receive the oncologist's clinical knowledge and the ongoing conversation.

YOUR JOB:
1. Evaluate completeness for EACH of these 15 guide sections:
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

Return JSON:
{{
  "section_scores": {{
    "section-id": {{"score": N, "assessment": "brief reason"}}
  }},
  "questions": ["specific question 1", "specific question 2"],
  "all_satisfied": true/false
}}

Set all_satisfied to true ONLY when ALL 15 sections score >= {SECTION_SCORE_THRESHOLD}.
Return ONLY valid JSON."""


def _oncologist_respond_system(skill_context: str) -> str:
    return f"""{skill_context}

You are responding to specific questions from a patient advocate about a cancer diagnosis.
The advocate has identified gaps in your clinical knowledge.

Answer EACH question with SPECIFIC data: drug names, percentages, trial names, dates.
Do NOT give vague answers. If you don't know, say so explicitly.

Return JSON:
{{
  "answers": [
    {{"question": "the question", "answer": "detailed answer with specific data"}}
  ],
  "additional_knowledge": {{}}
}}

The additional_knowledge object should contain any NEW structured data (same format as
the original knowledge map: approved_drugs, pipeline_drugs, etc.) that was missing before.

Return ONLY valid JSON."""


# --- Round functions ---


def _parse_json(raw: str, label: str) -> dict | list:
    """Parse JSON, stripping markdown fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"{label}: JSON parse failed: {e}")
        logger.debug(f"{label} raw output: {text[:500]}")
        return {}


def _oncologist_initial(
    client: anthropic.Anthropic, diagnosis: str, model: str, cost: CostTracker
) -> dict:
    """Round 1: Oncologist generates initial Clinical Knowledge Map."""
    skill_context = load_skill_context(os.path.join(SKILLS_DIR, "oncologist.md"))
    message = client.messages.create(
        model=model,
        max_tokens=12000,
        system=_oncologist_system(skill_context),
        messages=[{"role": "user", "content": f"Diagnosis: {diagnosis}\n\nGenerate the complete Clinical Knowledge Map."}],
    )
    cost.track(model, message.usage.input_tokens, message.usage.output_tokens)
    return _parse_json(message.content[0].text, "oncologist_initial")


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
    history_text = "\n\n---\n\n".join(conversation_history) if conversation_history else ""

    content = f"Diagnosis: {diagnosis}\n\nClinical Knowledge:\n{knowledge_text}"
    if history_text:
        content += f"\n\nConversation so far:\n{history_text}"

    message = client.messages.create(
        model=model,
        max_tokens=6000,
        system=_advocate_system(skill_context),
        messages=[{"role": "user", "content": content}],
    )
    cost.track(model, message.usage.input_tokens, message.usage.output_tokens)
    return _parse_json(message.content[0].text, "advocate_evaluate")


def _oncologist_respond(
    client: anthropic.Anthropic,
    diagnosis: str,
    questions: list[str],
    knowledge_text: str,
    model: str,
    cost: CostTracker,
) -> dict:
    """Oncologist responds to advocate's specific questions."""
    skill_context = load_skill_context(os.path.join(SKILLS_DIR, "oncologist.md"))
    questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    message = client.messages.create(
        model=model,
        max_tokens=8000,
        system=_oncologist_respond_system(skill_context),
        messages=[{
            "role": "user",
            "content": (
                f"Diagnosis: {diagnosis}\n\n"
                f"Your previous knowledge:\n{knowledge_text}\n\n"
                f"Patient advocate's questions:\n{questions_text}"
            ),
        }],
    )
    cost.track(model, message.usage.input_tokens, message.usage.output_tokens)
    return _parse_json(message.content[0].text, "oncologist_respond")


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
) -> dict:
    """Run iterative oncologist <-> advocate discovery loop.

    Args:
        diagnosis: The cancer diagnosis (e.g., "RET fusion-positive lung adenocarcinoma (NSCLC)")
        model: Claude model for discovery (should be Sonnet)
        cost: CostTracker instance
        api_key: Anthropic API key
        max_rounds: Maximum discovery rounds (default 5)

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
    knowledge_map = _oncologist_initial(client, diagnosis, model, cost)
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

        conversation.append(
            f"ONCOLOGIST (round {round_num} response):\n"
            f"{json.dumps(response.get('answers', []), indent=2)}"
        )

    logger.warning(f"Discovery did not converge after {max_rounds} rounds")
    return {
        "converged": False,
        "rounds": max_rounds,
        "knowledge_map": knowledge_map,
        "section_scores": section_scores,
        "conversation": conversation,
        "final_questions": questions,
    }
