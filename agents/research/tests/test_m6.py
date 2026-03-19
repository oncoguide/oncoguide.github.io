"""Tests for M6 functions: health check, dashboard, checkpoint, generate-from-data."""

import os
import pytest
from unittest.mock import patch, MagicMock

from run_research import (
    _health_check, _print_dashboard, _save_checkpoint, _gate_6,
    PHASE_NAMES, cmd_generate_from_data,
)


# ── Health check ──

def test_health_check_memory_db():
    """Health check passes for in-memory DB with valid topic."""
    with patch("run_research.load_registry") as mock_reg, \
         patch("run_research.find_topic") as mock_find:
        mock_reg.return_value = [{"id": "test-topic"}]
        mock_find.return_value = {"id": "test-topic"}
        result = _health_check(
            cfg={"database_path": ":memory:"},
            topic_id="test-topic",
            registry_path="fake.yaml",
        )
        assert result is True


def test_health_check_missing_topic():
    """Health check fails when topic not in registry."""
    with patch("run_research.load_registry") as mock_reg, \
         patch("run_research.find_topic") as mock_find:
        mock_reg.return_value = []
        mock_find.return_value = None
        result = _health_check(
            cfg={"database_path": ":memory:"},
            topic_id="nonexistent",
            registry_path="fake.yaml",
        )
        assert result is False


def test_health_check_bad_db_dir():
    """Health check fails when DB directory doesn't exist."""
    with patch("run_research.load_registry") as mock_reg, \
         patch("run_research.find_topic") as mock_find:
        mock_reg.return_value = [{"id": "t"}]
        mock_find.return_value = {"id": "t"}
        result = _health_check(
            cfg={"database_path": "/nonexistent/dir/research.db"},
            topic_id="t",
            registry_path="fake.yaml",
        )
        assert result is False


# ── Dashboard ──

def test_print_dashboard(capsys):
    """Dashboard prints without errors."""
    phases = [
        {"phase": 4, "name": "gap-analysis", "duration": 65, "cost": 0.08, "detail": "+34 findings"},
        {"phase": 6, "name": "guide-gen", "duration": 138, "cost": 0.82, "detail": "142KB"},
    ]
    _print_dashboard(
        topic_id="lung-ret-fusion", mode="generate-from-data", duration=300,
        cost_report="$2.35 / $5.00", phases=phases,
        findings_count=323, guide_size_kb=142, section_count=16,
        status="guide_ready",
    )
    captured = capsys.readouterr()
    assert "PIPELINE SUMMARY" in captured.out
    assert "lung-ret-fusion" in captured.out
    assert "guide_ready" in captured.out
    assert "16/16" in captured.out


# ── Checkpoint ──

def test_save_checkpoint():
    """Checkpoint saves to DB via save_pipeline_state."""
    mock_db = MagicMock()
    mock_cost = MagicMock()
    mock_cost.total_cost_usd = 1.23

    import time
    phase_start = time.time() - 10  # 10 seconds ago

    _save_checkpoint(mock_db, "test-topic", 42, 6, "complete", mock_cost, phase_start)

    mock_db.save_pipeline_state.assert_called_once()
    call_kwargs = mock_db.save_pipeline_state.call_args
    assert call_kwargs[1]["topic_id"] == "test-topic"
    assert call_kwargs[1]["phase"] == 6
    assert call_kwargs[1]["phase_name"] == "guide-gen"
    assert call_kwargs[1]["status"] == "complete"


# ── Phase names ──

def test_phase_names_complete():
    """All phases 0-9 have names."""
    for i in range(10):
        assert i in PHASE_NAMES


# ── Gate 6 ──

def test_gate_6_file_not_found():
    ok, reason = _gate_6("/nonexistent/guide.md")
    assert ok is False
    assert "not generated" in reason


def test_gate_6_too_small(tmp_path):
    guide = tmp_path / "small.md"
    guide.write_text("# Too small\n")
    ok, reason = _gate_6(str(guide))
    assert ok is False
    assert "too small" in reason


def test_gate_6_passes(tmp_path):
    guide = tmp_path / "guide.md"
    # Create guide with 16+ sections and executive summary, > 10KB
    content = "# BEFORE ANYTHING ELSE\nExecutive summary.\n\n"
    for i in range(17):
        content += f"\n## Section {i}\n" + "Content. " * 200 + "\n"
    guide.write_text(content)
    ok, reason = _gate_6(str(guide))
    assert ok is True


# ── Generate from data -- dry run ──

@patch("run_research.save_registry")
@patch("run_research.load_registry")
@patch("run_research.find_topic")
def test_generate_from_data_too_few_findings(mock_find, mock_load, mock_save):
    """cmd_generate_from_data exits if < 200 findings."""
    mock_load.return_value = [{"id": "t", "title": "Test", "status": "planned"}]
    mock_find.return_value = {"id": "t", "title": "Test", "status": "planned"}

    from modules.database import Database
    with patch.object(Database, "count_findings", return_value=50), \
         patch.object(Database, "create_tables"), \
         patch.object(Database, "__init__", return_value=None), \
         patch.object(Database, "close"):
        # Mock conn for Database
        mock_db_inst = MagicMock()
        with patch("run_research.Database") as MockDB:
            mock_db_obj = MagicMock()
            mock_db_obj.count_findings.return_value=50
            MockDB.return_value = mock_db_obj
            with pytest.raises(SystemExit):
                cmd_generate_from_data(
                    cfg={"anthropic_api_key": "fake", "database_path": ":memory:",
                         "max_cost_usd": 5.0},
                    topic_id="t",
                    registry_path="fake.yaml",
                    dry_run=True,
                )
