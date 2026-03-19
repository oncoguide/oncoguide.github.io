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


MODEL_CONTEXT_LIMITS = {
    "claude-haiku-4-5-20251001": 200_000,
    "claude-sonnet-4-6": 200_000,
}
DEFAULT_CONTEXT_LIMIT = 200_000


class TokenBudgetExceeded(Exception):
    """Raised when estimated prompt tokens exceed context window."""
    pass


def _get_context_limit(model: str) -> int:
    """Look up context window size for a model, with prefix matching fallback."""
    if model in MODEL_CONTEXT_LIMITS:
        return MODEL_CONTEXT_LIMITS[model]
    for known, limit in MODEL_CONTEXT_LIMITS.items():
        if model.startswith(known.rsplit("-", 1)[0]):
            return limit
    logger.warning(f"Unknown model '{model}', using default {DEFAULT_CONTEXT_LIMIT}")
    return DEFAULT_CONTEXT_LIMIT


def check_prompt_size(messages, system="", max_tokens_output=4000,
                      context_limit=200_000):
    """Estimate input tokens and verify they fit in context window.

    Uses chars // 3 (conservative for medical text with drug names/URLs).
    Returns (ok: bool, estimated_tokens: int).
    """
    total_chars = len(system)
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    total_chars += len(block["text"])
    estimated_input = total_chars // 3
    available = context_limit - max_tokens_output

    if estimated_input > available:
        logger.error(
            f"[SAFETY NET] Prompt too large: ~{estimated_input:,} tokens "
            f"> {available:,} available"
        )
        return False, estimated_input
    if estimated_input > available * 0.90:
        logger.warning(
            f"[SAFETY NET] Prompt near limit: ~{estimated_input:,} tokens "
            f"({estimated_input / available:.0%} of {available:,})"
        )
    return True, estimated_input


def api_call(client, **kwargs):
    """Make an API call using streaming, with token budget check.

    Long Sonnet calls with large prompts can take > 60 seconds before the first
    token arrives. ISP/router idle-TCP timeouts kill the connection at 60s.
    Streaming sends a response header immediately, keeping the connection live.
    """
    model = kwargs.get("model", "")
    context_limit = _get_context_limit(model) if model else DEFAULT_CONTEXT_LIMIT
    ok, est = check_prompt_size(
        kwargs.get("messages", []),
        kwargs.get("system", ""),
        kwargs.get("max_tokens", 4000),
        context_limit=context_limit,
    )
    if not ok:
        raise TokenBudgetExceeded(
            f"Estimated ~{est:,} input tokens exceeds context window"
        )
    with client.messages.stream(**kwargs) as stream:
        return stream.get_final_message()


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
