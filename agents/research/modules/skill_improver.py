# modules/skill_improver.py
"""Write agent learnings back to skill files.

After each research run, the validation phase may produce learnings
(e.g., "for RET fusion, always verify pralsetinib EU withdrawal").
These are appended to the skill's ## Learnings section.
"""

import logging
import os

logger = logging.getLogger(__name__)


def append_learnings(skill_path: str, learnings: list[str]):
    """Append new learnings to a skill file's ## Learnings section.

    Deduplicates against existing learnings (case-insensitive substring match).
    Creates ## Learnings section if it doesn't exist.

    Args:
        skill_path: Absolute path to the skill .md file
        learnings: List of learning strings to append
    """
    if not learnings:
        return

    if not os.path.exists(skill_path):
        logger.warning(f"Skill file not found: {skill_path}")
        return

    with open(skill_path) as f:
        content = f.read()

    # Find existing learnings for dedup
    existing_lower = content.lower()

    new_learnings = []
    for learning in learnings:
        # Check if this learning (or close variant) already exists
        if learning.lower().strip("- ") not in existing_lower:
            new_learnings.append(learning)

    if not new_learnings:
        logger.info("No new learnings to add (all duplicates)")
        return

    # Format new learnings as bullet points
    learnings_text = "\n".join(f"- {l}" for l in new_learnings)

    if "## Learnings" in content:
        # Append after existing learnings
        # Find the end of the Learnings section (next ## or end of file)
        idx = content.index("## Learnings")
        rest = content[idx + len("## Learnings"):]

        # Find next section
        next_section = rest.find("\n## ")
        if next_section == -1:
            # Learnings is last section -- append at end
            content = content.rstrip() + "\n" + learnings_text + "\n"
        else:
            # Insert before next section
            insert_point = idx + len("## Learnings") + next_section
            content = content[:insert_point].rstrip() + "\n" + learnings_text + "\n" + content[insert_point:]
    else:
        # Create Learnings section at end
        content = content.rstrip() + "\n\n## Learnings\n\n" + learnings_text + "\n"

    with open(skill_path, "w") as f:
        f.write(content)

    logger.info(f"Added {len(new_learnings)} learnings to {os.path.basename(skill_path)}")
