import os
import logging
import pytest
from modules.utils import (
    compute_content_hash, sanitize_text, extract_domain, parse_date,
    load_skill_context, check_prompt_size, TokenBudgetExceeded,
)


def test_compute_content_hash_deterministic():
    h1 = compute_content_hash("topic-a", "Test Title", "https://example.com")
    h2 = compute_content_hash("topic-a", "Test Title", "https://example.com")
    assert h1 == h2


def test_compute_content_hash_case_insensitive():
    h1 = compute_content_hash("topic-a", "TEST TITLE", "HTTPS://EXAMPLE.COM")
    h2 = compute_content_hash("topic-a", "test title", "https://example.com")
    assert h1 == h2


def test_compute_content_hash_different_topics():
    h1 = compute_content_hash("topic-a", "Title", "https://example.com")
    h2 = compute_content_hash("topic-b", "Title", "https://example.com")
    assert h1 != h2


def test_sanitize_text_strips_whitespace():
    assert sanitize_text("  hello  world  ") == "hello world"


def test_sanitize_text_none():
    assert sanitize_text(None) == ""


def test_extract_domain():
    assert extract_domain("https://www.ncbi.nlm.nih.gov/pubmed/123") == "ncbi.nlm.nih.gov"


def test_extract_domain_invalid():
    assert extract_domain("not-a-url") == "unknown"


def test_parse_date_valid():
    assert parse_date("2026-03-15") == "2026-03-15"


def test_parse_date_none():
    assert parse_date(None) is None


def test_load_skill_context_extracts_persona(tmp_path):
    skill_file = tmp_path / "test-skill.md"
    skill_file.write_text(
        "---\nname: test\ndescription: test skill\n---\n\n"
        "## Persona\n\nExperienced doctor.\n\n"
        "## Actions\n\n1. Do things\n"
    )
    context = load_skill_context(str(skill_file))
    assert "Experienced doctor" in context
    assert "## Persona" not in context  # heading stripped


def test_load_skill_context_includes_learnings(tmp_path):
    skill_file = tmp_path / "test-skill.md"
    skill_file.write_text(
        "---\nname: test\ndescription: test\n---\n\n"
        "## Persona\n\nDoctor.\n\n"
        "## Learnings\n\n- Always check withdrawal status\n"
    )
    context = load_skill_context(str(skill_file))
    assert "Always check withdrawal status" in context


def test_load_skill_context_missing_file():
    context = load_skill_context("/nonexistent/path.md")
    assert context == ""


# --- check_prompt_size tests ---

def test_check_prompt_size_ok():
    ok, est = check_prompt_size(
        messages=[{"role": "user", "content": "Hello"}],
        system="You are helpful.",
        max_tokens_output=4000,
        context_limit=200_000,
    )
    assert ok is True
    assert est < 100


def test_check_prompt_size_over_limit():
    big_content = "x" * 600_000  # 600K chars / 3 = 200K tokens
    ok, est = check_prompt_size(
        messages=[{"role": "user", "content": big_content}],
        max_tokens_output=4000,
        context_limit=200_000,
    )
    assert ok is False
    assert est > 190_000


def test_check_prompt_size_near_limit_warns(caplog):
    content = "x" * 534_000  # ~91% of available budget
    with caplog.at_level(logging.WARNING):
        ok, est = check_prompt_size(
            messages=[{"role": "user", "content": content}],
            max_tokens_output=4000,
            context_limit=200_000,
        )
    assert ok is True
    assert "SAFETY NET" in caplog.text


def test_check_prompt_size_multimodal():
    ok, est = check_prompt_size(
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "Hello world"}
        ]}],
    )
    assert ok is True
