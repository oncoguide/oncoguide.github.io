"""Tests for seed import (--seed) and reclassify (--reclassify) commands."""

import sqlite3
import pytest
from modules.database import Database


def _make_cna_db(path):
    """Create a minimal CNA-style database for testing."""
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_hash TEXT,
            title_original TEXT,
            snippet_original TEXT,
            source_language TEXT,
            title_english TEXT,
            summary_english TEXT,
            section TEXT,
            relevance_score INTEGER,
            source_url TEXT,
            source_domain TEXT,
            source_platform TEXT,
            date_published TEXT,
            date_found TEXT
        )
    """)
    # Insert test findings
    for i in range(5):
        section = ["my_treatment", "resistance", "daily_life", "alerts_safety", "research_pipeline"][i]
        conn.execute(
            """INSERT INTO findings
            (content_hash, title_original, snippet_original, source_language,
             title_english, summary_english, section, relevance_score,
             source_url, source_domain, source_platform, date_published, date_found)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (f"cna-hash-{i}", f"CNA Title {i}", f"CNA snippet {i}", "en",
             f"CNA English {i}", f"CNA summary {i}", section, 7,
             f"https://example.com/cna/{i}", "example.com", "serper",
             "2026-01-01", "2026-03-01"),
        )
    conn.commit()
    conn.close()


def test_seed_imports_cna_findings(tmp_path):
    """Seed should import CNA findings with correct lifecycle_stage mapping."""
    import sys
    sys.path.insert(0, str(tmp_path.parent.parent))

    from run_research import cmd_seed, CNA_SECTION_MAP

    # Create target DB
    db_path = str(tmp_path / "target.db")
    cna_path = str(tmp_path / "cna.db")
    _make_cna_db(cna_path)

    cfg = {"database_path": db_path}
    cmd_seed(cfg, "lung-ret-fusion", cna_path, "fake-registry.yaml")

    # Verify
    db = Database(db_path)
    db.create_tables()
    total = db.count_findings("lung-ret-fusion")
    assert total == 5

    # Check lifecycle mapping
    rows = db.execute(
        "SELECT lifecycle_stage, COUNT(*) as cnt FROM findings WHERE topic_id='lung-ret-fusion' GROUP BY lifecycle_stage"
    ).fetchall()
    stages = {r["lifecycle_stage"]: r["cnt"] for r in rows}
    assert stages.get("Q2", 0) >= 1  # my_treatment -> Q2
    assert stages.get("Q5", 0) >= 1  # resistance -> Q5
    assert stages.get("Q3", 0) >= 2  # daily_life + alerts_safety -> Q3

    # All should be seeded
    seeded = db.execute(
        "SELECT COUNT(*) FROM findings WHERE is_seeded=1 AND seed_source='cna'"
    ).fetchone()[0]
    assert seeded == 5
    db.close()


def test_seed_deduplicates(tmp_path):
    """Running seed twice should not create duplicates."""
    from run_research import cmd_seed

    db_path = str(tmp_path / "target.db")
    cna_path = str(tmp_path / "cna.db")
    _make_cna_db(cna_path)

    cfg = {"database_path": db_path}
    cmd_seed(cfg, "lung-ret-fusion", cna_path, "fake-registry.yaml")

    db = Database(db_path)
    count1 = db.count_findings("lung-ret-fusion")
    db.close()

    # Second run should skip
    cmd_seed(cfg, "lung-ret-fusion", cna_path, "fake-registry.yaml")

    db = Database(db_path)
    count2 = db.count_findings("lung-ret-fusion")
    db.close()

    assert count1 == count2


def test_seed_missing_cna_db(tmp_path, capsys):
    """Seed should handle missing CNA DB gracefully."""
    from run_research import cmd_seed

    db_path = str(tmp_path / "target.db")
    cfg = {"database_path": db_path}
    cmd_seed(cfg, "lung-ret-fusion", "/nonexistent/path.db", "fake-registry.yaml")

    captured = capsys.readouterr()
    assert "not found" in captured.out


def test_reclassify_updates_lifecycle_stage(tmp_path, monkeypatch):
    """Reclassify should update lifecycle_stage and authority_score via Haiku."""
    from run_research import cmd_reclassify

    # Setup DB with findings that have NULL lifecycle_stage
    db_path = str(tmp_path / "test.db")
    db = Database(db_path)
    db.create_tables()
    run_id = db.start_run("test", "test-topic")
    for i in range(3):
        db.insert_finding({
            "content_hash": f"rc-{i}",
            "topic_id": "test-topic",
            "title_original": f"Finding {i}",
            "snippet_original": "",
            "source_language": "en",
            "title_english": f"Finding {i}",
            "summary_english": f"Summary about treatment {i}",
            "relevance_score": 8,
            "authority_score": 0,
            "source_url": f"http://example.com/{i}",
            "source_domain": "example.com",
            "source_platform": "pubmed",
            "date_published": None,
            "date_found": "2026-03-18",
            "run_id": run_id,
            "lifecycle_stage": None,
        })
    db.close()

    # Mock anthropic client
    class MockContent:
        def __init__(self):
            self.type = "tool_use"
            self.input = {
                "classifications": [
                    {"finding_id": 1, "lifecycle_stage": "Q2", "authority_score": 4},
                    {"finding_id": 2, "lifecycle_stage": "Q3", "authority_score": 3},
                    {"finding_id": 3, "lifecycle_stage": "Q5", "authority_score": 2},
                ],
            }

    class MockUsage:
        input_tokens = 100
        output_tokens = 50

    class MockMessage:
        content = [MockContent()]
        usage = MockUsage()

    class MockMessages:
        def create(self, **kwargs):
            return MockMessage()

    class MockClient:
        messages = MockMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: MockClient())

    cfg = {
        "database_path": db_path,
        "anthropic_api_key": "test-key",
        "enrichment_model": "claude-haiku-4-5-20251001",
        "max_cost_usd": 5.0,
    }
    cmd_reclassify(cfg, "test-topic")

    # Verify
    db = Database(db_path)
    db.create_tables()
    rows = db.execute(
        "SELECT id, lifecycle_stage, authority_score FROM findings ORDER BY id"
    ).fetchall()
    assert rows[0]["lifecycle_stage"] == "Q2"
    assert rows[0]["authority_score"] == 4
    assert rows[1]["lifecycle_stage"] == "Q3"
    assert rows[2]["lifecycle_stage"] == "Q5"
    db.close()
