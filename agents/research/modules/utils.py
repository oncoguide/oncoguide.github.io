"""Utility functions for the research agent."""

import hashlib
import logging
import os
import re
from datetime import datetime
from urllib.parse import urlparse

from dateutil import parser as dateutil_parser

logger = logging.getLogger(__name__)


def compute_content_hash(topic_id: str, title: str, url: str) -> str:
    """SHA-256 hash for deduplication. Includes topic_id so same finding
    can appear under multiple topics."""
    raw = f"{topic_id}|{title.lower().strip()}|{url.lower().strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def setup_logging(log_file: str = "logs/research.log", level: str = "INFO"):
    """Configure logging to file and console."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )


def sanitize_text(text: str | None) -> str:
    """Strip and normalize whitespace."""
    if not text:
        return ""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return re.sub(r"\s+", " ", text.strip())


def extract_domain(url: str) -> str:
    """Extract domain from URL, stripping www. prefix."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or "unknown"
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return "unknown"


def parse_date(date_str: str | None) -> str | None:
    """Parse a date string into ISO format (YYYY-MM-DD). Returns None if unparseable."""
    if not date_str:
        return None
    try:
        dt = dateutil_parser.parse(date_str, fuzzy=True)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def now_iso() -> str:
    """Current datetime as ISO string."""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def load_skill_context(skill_path: str) -> str:
    """Load a skill file and extract persona, key principles, and learnings.

    Strips YAML frontmatter and section headers. Returns plain text
    suitable for use as part of a system prompt.
    """
    if not os.path.exists(skill_path):
        logger.warning(f"Skill file not found: {skill_path}")
        return ""

    with open(skill_path) as f:
        content = f.read()

    # Strip YAML frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].strip()

    # Extract relevant sections: Persona, Context, Learnings
    lines = content.split("\n")
    result_lines = []
    in_relevant_section = False

    for line in lines:
        if line.startswith("## "):
            section_name = line[3:].strip().lower()
            in_relevant_section = section_name in ("persona", "context", "learnings")
            if in_relevant_section:
                if section_name == "learnings":
                    result_lines.append("\nLEARNINGS FROM PREVIOUS RUNS:")
                continue
        if in_relevant_section:
            result_lines.append(line)

    return "\n".join(result_lines).strip()
