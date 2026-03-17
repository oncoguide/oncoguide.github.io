"""Cross-verification: compare discovery knowledge map claims vs real findings.

Haiku receives the knowledge map (with numbers from discovery) and top findings
with authority >= 3. Produces a report: VERIFIED, CONTRADICTED, or UNVERIFIED
for each quantitative claim. The report becomes input for guide generation.
"""

import json
import logging

import anthropic

from .cost_tracker import CostTracker

logger = logging.getLogger(__name__)

CROSS_VERIFY_TOOL = {
    "name": "submit_verification",
    "description": "Submit cross-verification results comparing discovery claims against real findings",
    "input_schema": {
        "type": "object",
        "properties": {
            "verified": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {"type": "string"},
                        "finding_id": {"type": "integer"},
                        "finding_value": {"type": "string"},
                    },
                    "required": ["claim", "finding_id", "finding_value"],
                },
            },
            "contradicted": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {"type": "string"},
                        "discovery_value": {"type": "string"},
                        "finding_id": {"type": "integer"},
                        "finding_value": {"type": "string"},
                        "authority_score": {"type": "integer"},
                    },
                    "required": ["claim", "discovery_value", "finding_id", "finding_value", "authority_score"],
                },
            },
            "unverified": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["claim", "reason"],
                },
            },
        },
        "required": ["verified", "contradicted", "unverified"],
    },
}

SYSTEM_PROMPT = """You are a medical data verification specialist.

You will receive:
1. A Clinical Knowledge Map (from an AI oncologist's parametric knowledge)
2. Real research findings from PubMed, ClinicalTrials.gov, FDA, and other sources

Your job: find EVERY quantitative claim in the knowledge map (percentages, months, doses,
frequencies, counts) and check if the findings support, contradict, or don't address it.

For each claim, classify as:
- VERIFIED: Finding confirms the number (within 5% margin)
- CONTRADICTED: Finding gives a materially different number. Include the finding's number.
  Set "use_finding": true if the finding has higher authority.
- UNVERIFIED: No finding addresses this claim. Note the reason.

Rules:
- Focus on NUMBERS: ORR, PFS, OS, frequency percentages, doses, trial sizes
- Ignore qualitative claims (e.g., "well-tolerated") unless they have a number
- When contradicted, ALWAYS prefer the finding with higher authority score
- Be thorough: check ALL drugs, ALL trials, ALL side effect frequencies

Use the submit_verification tool to submit your results."""


def cross_verify(
    knowledge_map: dict,
    findings: list[dict],
    diagnosis: str,
    api_key: str,
    cost: CostTracker,
    model: str = "claude-haiku-4-5-20251001",
    min_authority: int = 3,
) -> dict:
    """Compare discovery knowledge map claims against real findings.

    Args:
        knowledge_map: Discovery output (structured clinical data)
        findings: Enriched findings from DB (with authority_score)
        diagnosis: Cancer diagnosis string
        api_key: Anthropic API key
        cost: CostTracker instance
        model: Model to use (default Haiku)
        min_authority: Minimum authority score for findings to include

    Returns:
        {"verified": [...], "contradicted": [...], "unverified": [...]}
    """
    empty = {"verified": [], "contradicted": [], "unverified": []}

    if not findings:
        logger.info("Cross-verify: no findings, skipping")
        return empty

    if not api_key:
        logger.warning("Cross-verify: no API key")
        return empty

    # Filter findings by authority
    high_auth = [f for f in findings if f.get("authority_score", 0) >= min_authority]
    if not high_auth:
        logger.info(f"Cross-verify: no findings with authority >= {min_authority}")
        return empty

    # Format findings for prompt
    findings_text = "\n".join(
        f"[{i+1}] Authority: {f.get('authority_score', 0)}/5 | "
        f"Title: {f.get('title_english', 'N/A')} | "
        f"Summary: {f.get('summary_english', 'N/A')}"
        for i, f in enumerate(high_auth)
    )

    knowledge_text = json.dumps(knowledge_map, indent=2, default=str)
    # Truncate if too large
    if len(knowledge_text) > 20000:
        knowledge_text = knowledge_text[:20000] + "\n... (truncated)"

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=6000,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"Diagnosis: {diagnosis}\n\n"
                    f"=== KNOWLEDGE MAP (from AI oncologist) ===\n{knowledge_text}\n\n"
                    f"=== REAL FINDINGS (authority >= {min_authority}) ===\n{findings_text}"
                ),
            }],
            tools=[CROSS_VERIFY_TOOL],
            tool_choice={"type": "tool", "name": "submit_verification"},
        )
        cost.track(model, message.usage.input_tokens, message.usage.output_tokens)

        result = message.content[0].input

        logger.info(
            f"Cross-verify: {len(result['verified'])} verified, "
            f"{len(result['contradicted'])} contradicted, "
            f"{len(result['unverified'])} unverified"
        )
        return result

    except Exception as e:
        logger.error(f"Cross-verification failed: {e}")
        return empty


def format_report(report: dict) -> str:
    """Format cross-verification report as human-readable text for guide generation."""
    verified = report.get("verified", [])
    contradicted = report.get("contradicted", [])
    unverified = report.get("unverified", [])

    if not verified and not contradicted and not unverified:
        return "No claims to verify (empty knowledge map or no findings)."

    lines = ["=== CROSS-VERIFICATION REPORT ===\n"]

    if contradicted:
        lines.append(f"CONTRADICTED ({len(contradicted)} claims):")
        for c in contradicted:
            finding_note = f" -> USE Finding {c.get('finding_id', '?')}: {c.get('finding_value', '?')}" if c.get("use_finding") else ""
            lines.append(f"  - Discovery: {c['claim']} | Finding: {c.get('finding_value', '?')}{finding_note}")
        lines.append("")

    if unverified:
        lines.append(f"UNVERIFIED ({len(unverified)} claims):")
        for u in unverified:
            lines.append(f"  - {u['claim']}: {u.get('reason', 'no matching finding')}")
        lines.append("")

    if verified:
        lines.append(f"VERIFIED ({len(verified)} claims):")
        for v in verified:
            lines.append(f"  - {v['claim']} (Finding {v.get('finding_id', '?')})")
        lines.append("")

    lines.append(f"Summary: {len(verified)} verified, {len(contradicted)} contradicted, {len(unverified)} unverified")
    return "\n".join(lines)
