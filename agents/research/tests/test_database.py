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


def test_authority_score_column_exists(db):
    """DB schema should include authority_score column in findings."""
    run_id = db.start_run("topic", "test-topic")
    finding = {
        "content_hash": "auth-test-1",
        "topic_id": "test-topic",
        "title_original": "NEJM Study",
        "snippet_original": "",
        "source_language": "en",
        "title_english": "NEJM Study",
        "summary_english": "Phase III results",
        "relevance_score": 9,
        "authority_score": 5,
        "source_url": "https://nejm.org/1",
        "source_domain": "nejm.org",
        "source_platform": "pubmed",
        "date_published": "2025-03",
        "date_found": "2026-03-16",
        "run_id": run_id,
    }
    fid = db.insert_finding(finding)
    assert fid is not None

    # Retrieve and verify authority_score is stored
    row = db.execute("SELECT authority_score FROM findings WHERE id = ?", (fid,)).fetchone()
    assert row["authority_score"] == 5


# ── v6 migration tests ──────────────────────────────────────────────


def test_migration_adds_lifecycle_columns(tmp_path):
    """After create_tables, findings should have lifecycle_stage, is_seeded, seed_source columns."""
    d = Database(str(tmp_path / "test.db"))
    d.create_tables()
    cols = [row[1] for row in d.execute("PRAGMA table_info(findings)").fetchall()]
    assert "lifecycle_stage" in cols
    assert "is_seeded" in cols
    assert "seed_source" in cols
    d.close()


def test_new_tables_created(tmp_path):
    """v6 tables should exist after create_tables."""
    d = Database(str(tmp_path / "test.db"))
    d.create_tables()
    tables = [row[0] for row in d.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for expected in ["pipeline_state", "monitor_runs", "alerts",
                     "tracked_entities", "findings_archive"]:
        assert expected in tables, f"Missing table: {expected}"
    d.close()


def test_insert_finding_stores_lifecycle_stage(tmp_path):
    """insert_finding should store lifecycle_stage, is_seeded, seed_source."""
    d = Database(str(tmp_path / "test.db"))
    d.create_tables()
    run_id = d.start_run("test", "test-topic")
    d.insert_finding({
        "content_hash": "lc-test-1",
        "topic_id": "test-topic",
        "title_original": "Test",
        "snippet_original": "Snippet",
        "source_language": "en",
        "title_english": "Test",
        "summary_english": "Summary",
        "relevance_score": 8,
        "authority_score": 4,
        "source_url": "http://example.com",
        "source_domain": "example.com",
        "source_platform": "serper",
        "date_published": "2026-01-01",
        "date_found": "2026-03-18",
        "run_id": run_id,
        "lifecycle_stage": "Q3",
        "is_seeded": 0,
        "seed_source": None,
    })
    row = d.execute(
        "SELECT lifecycle_stage, is_seeded, seed_source FROM findings WHERE content_hash='lc-test-1'"
    ).fetchone()
    assert row["lifecycle_stage"] == "Q3"
    assert row["is_seeded"] == 0
    assert row["seed_source"] is None
    d.close()


def test_insert_finding_defaults_lifecycle_fields(tmp_path):
    """insert_finding without lifecycle fields should default gracefully."""
    d = Database(str(tmp_path / "test.db"))
    d.create_tables()
    run_id = d.start_run("test", "test-topic")
    d.insert_finding({
        "content_hash": "default-test-1",
        "topic_id": "test-topic",
        "title_original": "Test",
        "snippet_original": "",
        "source_language": "en",
        "title_english": "Test",
        "summary_english": "",
        "relevance_score": 5,
        "source_url": "http://example.com/2",
        "source_domain": "example.com",
        "source_platform": "serper",
        "date_published": None,
        "date_found": "2026-03-18",
        "run_id": run_id,
    })
    row = d.execute(
        "SELECT lifecycle_stage, is_seeded, seed_source FROM findings WHERE content_hash='default-test-1'"
    ).fetchone()
    assert row["lifecycle_stage"] is None
    assert row["is_seeded"] == 0
    assert row["seed_source"] is None
    d.close()


def test_save_and_get_pipeline_state(db):
    """pipeline_state CRUD."""
    run_id = db.start_run("research", "lung-ret-fusion")
    db.save_pipeline_state(
        topic_id="lung-ret-fusion", run_id=run_id, phase=0,
        phase_name="pre_search", status="complete",
        output_ref="data/pre_search.json", cost_usd=0.02,
        duration_seconds=32.0, error=None,
    )
    db.save_pipeline_state(
        topic_id="lung-ret-fusion", run_id=run_id, phase=1,
        phase_name="discovery", status="complete",
        output_ref=None, cost_usd=0.45,
        duration_seconds=252.0, error=None,
    )
    last = db.get_last_completed_phase("lung-ret-fusion")
    assert last == 1


def test_get_last_completed_phase_none(db):
    """No pipeline state returns None."""
    assert db.get_last_completed_phase("nonexistent") is None


def test_save_and_get_alerts(db):
    """Alert CRUD + acknowledge."""
    mr_id = db.start_monitor_run("lung-ret-fusion", "2026-03-11")
    db.save_alert(
        monitor_run_id=mr_id, topic_id="lung-ret-fusion",
        severity="critical", category="safety",
        title="Drug withdrawal", description="Pralsetinib withdrawn from EU",
        finding_ids="[101, 102]",
    )
    alerts = db.get_unacknowledged_alerts("lung-ret-fusion")
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "critical"

    db.acknowledge_alert(alerts[0]["id"])
    alerts2 = db.get_unacknowledged_alerts("lung-ret-fusion")
    assert len(alerts2) == 0


def test_tracked_entities(db):
    """Tracked entities CRUD."""
    db.save_tracked_entity(
        topic_id="lung-ret-fusion", entity_type="drug",
        canonical_name="selpercatinib",
        aliases='["Retevmo", "LOXO-292"]',
        guide_sections="[2, 4, 5, 6]",
    )
    entities = db.get_tracked_entities("lung-ret-fusion")
    assert len(entities) == 1
    assert entities[0]["canonical_name"] == "selpercatinib"

    # Upsert same entity
    db.save_tracked_entity(
        topic_id="lung-ret-fusion", entity_type="drug",
        canonical_name="selpercatinib",
        aliases='["Retevmo", "LOXO-292", "LY3527723"]',
        guide_sections="[2, 4, 5, 6]",
    )
    entities2 = db.get_tracked_entities("lung-ret-fusion")
    assert len(entities2) == 1  # no duplicate


def test_archive_old_findings(db):
    """archive_old_findings moves low-relevance old findings."""
    run_id = db.start_run("topic", "test-topic")
    # Insert an old, low-relevance finding
    db.insert_finding({
        "content_hash": "old-1",
        "topic_id": "test-topic",
        "title_original": "Old finding",
        "snippet_original": "",
        "source_language": "en",
        "title_english": "Old finding",
        "summary_english": "",
        "relevance_score": 2,
        "source_url": "http://example.com/old",
        "source_domain": "example.com",
        "source_platform": "serper",
        "date_published": None,
        "date_found": "2025-01-01",
        "run_id": run_id,
    })
    archived = db.archive_old_findings("test-topic", max_age_days=30, min_relevance=3)
    assert archived >= 1
    # Finding should be in archive
    row = db.execute(
        "SELECT * FROM findings_archive WHERE content_hash='old-1'"
    ).fetchone()
    assert row is not None
    # Finding should be gone from findings
    row2 = db.execute(
        "SELECT * FROM findings WHERE content_hash='old-1'"
    ).fetchone()
    assert row2 is None


def test_monitor_run_lifecycle(db):
    """start_monitor_run and finish_monitor_run."""
    mr_id = db.start_monitor_run("lung-ret-fusion", "2026-03-11")
    assert mr_id > 0
    db.finish_monitor_run(mr_id, {
        "findings_scanned": 100,
        "new_findings": 5,
        "alerts_generated": 2,
        "cost_usd": 0.25,
    })
    row = db.execute("SELECT * FROM monitor_runs WHERE id = ?", (mr_id,)).fetchone()
    assert row["new_findings"] == 5
