import pytest
from modules.utils import compute_content_hash, sanitize_text, extract_domain, parse_date


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
