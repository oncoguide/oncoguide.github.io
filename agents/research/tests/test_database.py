import os
import pytest
from modules.database import Database


@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "test.db")
    d = Database(db_path)
    d.create_tables()
    return d


def test_create_tables(db):
    """Tables exist after init."""
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    names = {t[0] for t in tables}
    assert "findings" in names
    assert "search_runs" in names
    assert "search_log" in names


def test_start_and_finish_run(db):
    run_id = db.start_run("topic", "test-topic")
    assert run_id > 0
    db.finish_run(run_id, {"queries_total": 5, "raw_results": 20})
    run = db.execute("SELECT * FROM search_runs WHERE id = ?", (run_id,)).fetchone()
    assert run is not None


def test_insert_finding(db):
    run_id = db.start_run("topic", "test-topic")
    finding = {
        "content_hash": "abc123",
        "topic_id": "test-topic",
        "title_original": "Test Title",
        "snippet_original": "Test snippet",
        "source_language": "en",
        "title_english": "Test Title",
        "summary_english": "Test summary",
        "relevance_score": 8,
        "source_url": "https://example.com/article",
        "source_domain": "example.com",
        "source_platform": "serper",
        "date_published": "2026-03-15",
        "date_found": "2026-03-15",
        "run_id": run_id,
    }
    fid = db.insert_finding(finding)
    assert fid > 0


def test_duplicate_finding_rejected(db):
    run_id = db.start_run("topic", "test-topic")
    finding = {
        "content_hash": "abc123",
        "topic_id": "test-topic",
        "title_original": "Test",
        "snippet_original": "",
        "source_language": "en",
        "title_english": "Test",
        "summary_english": "",
        "relevance_score": 5,
        "source_url": "https://example.com",
        "source_domain": "example.com",
        "source_platform": "serper",
        "date_published": None,
        "date_found": "2026-03-15",
        "run_id": run_id,
    }
    fid1 = db.insert_finding(finding)
    fid2 = db.insert_finding(finding)
    assert fid1 > 0
    assert fid2 is None  # duplicate rejected


def test_get_findings_by_topic(db):
    run_id = db.start_run("topic", "topic-a")
    for i in range(3):
        db.insert_finding({
            "content_hash": f"hash-{i}",
            "topic_id": "topic-a",
            "title_original": f"Title {i}",
            "snippet_original": "",
            "source_language": "en",
            "title_english": f"Title {i}",
            "summary_english": f"Summary {i}",
            "relevance_score": 10 - i,
            "source_url": f"https://example.com/{i}",
            "source_domain": "example.com",
            "source_platform": "serper",
            "date_published": None,
            "date_found": "2026-03-15",
            "run_id": run_id,
        })
    findings = db.get_findings_by_topic("topic-a", limit=2)
    assert len(findings) == 2
    assert findings[0]["relevance_score"] >= findings[1]["relevance_score"]


def test_log_search(db):
    run_id = db.start_run("topic", "test-topic")
    db.log_search(run_id, "cancer diagnosis", "serper", "en", 10, 3, "success")
    logs = db.execute("SELECT * FROM search_log WHERE run_id = ?", (run_id,)).fetchall()
    assert len(logs) == 1


def test_backup(db, tmp_path):
    backup_dir = str(tmp_path / "backups")
    db.backup(backup_dir, max_backups=3)
    backups = os.listdir(backup_dir)
    assert len(backups) == 1
    assert backups[0].startswith("research_")
