import json
import os
import pytest
from unittest.mock import patch, MagicMock, Mock, call

from modules.guide_generator import (
    generate_guide, CRITICAL_SECTIONS, SECTION_BRIEFS, GUIDE_SECTIONS,
    _build_findings_text, _filter_findings_for_section, _get_lifecycle_prefixes,
)


def _mock_text(text="Section content here"):
    """Helper: create a mock message with text content."""
    return MagicMock(
        content=[MagicMock(text=text)],
        usage=MagicMock(input_tokens=100, output_tokens=50),
    )


# ── Lifecycle filtering ──

def test_get_lifecycle_prefixes_simple():
    assert _get_lifecycle_prefixes("Q1") == ["Q1"]
    assert _get_lifecycle_prefixes("Q5") == ["Q5"]


def test_get_lifecycle_prefixes_sub_stage():
    assert _get_lifecycle_prefixes("Q3-dosing") == ["Q3"]
    assert _get_lifecycle_prefixes("Q3-effects") == ["Q3"]


def test_get_lifecycle_prefixes_multi_stage():
    prefixes = _get_lifecycle_prefixes("Q3-access+Q9")
    assert "Q3" in prefixes
    assert "Q9" in prefixes


def test_get_lifecycle_prefixes_derived():
    prefixes = _get_lifecycle_prefixes("Q1-Q8-derived")
    assert len(prefixes) == 9  # Q1 through Q9


def test_filter_findings_for_section():
    findings = [
        {"lifecycle_stage": "Q1", "authority_score": 3, "relevance_score": 8},
        {"lifecycle_stage": "Q2", "authority_score": 5, "relevance_score": 9},
        {"lifecycle_stage": "Q3", "authority_score": 4, "relevance_score": 7},
        {"lifecycle_stage": "Q5", "authority_score": 2, "relevance_score": 6},
    ]
    # Q2 section should only get Q2 findings
    q2_findings = _filter_findings_for_section(findings, "Q2")
    assert len(q2_findings) == 1
    assert q2_findings[0]["lifecycle_stage"] == "Q2"


def test_filter_findings_multi_stage():
    findings = [
        {"lifecycle_stage": "Q3", "authority_score": 3, "relevance_score": 8},
        {"lifecycle_stage": "Q9", "authority_score": 5, "relevance_score": 9},
        {"lifecycle_stage": "Q1", "authority_score": 4, "relevance_score": 7},
    ]
    # Q3-access+Q9 should match Q3 and Q9
    matched = _filter_findings_for_section(findings, "Q3-access+Q9")
    assert len(matched) == 2
    stages = {f["lifecycle_stage"] for f in matched}
    assert stages == {"Q3", "Q9"}


def test_filter_findings_sorted_by_authority():
    findings = [
        {"lifecycle_stage": "Q2", "authority_score": 1, "relevance_score": 9},
        {"lifecycle_stage": "Q2", "authority_score": 5, "relevance_score": 7},
        {"lifecycle_stage": "Q2", "authority_score": 3, "relevance_score": 8},
    ]
    filtered = _filter_findings_for_section(findings, "Q2")
    assert filtered[0]["authority_score"] == 5
    assert filtered[1]["authority_score"] == 3
    assert filtered[2]["authority_score"] == 1


def test_filter_findings_derived_gets_all():
    findings = [
        {"lifecycle_stage": f"Q{i}", "authority_score": 3, "relevance_score": 8}
        for i in range(1, 9)
    ]
    matched = _filter_findings_for_section(findings, "Q1-Q8-derived")
    assert len(matched) == 8


# ── Findings text ──

def test_findings_text_includes_authority_and_lifecycle():
    findings = [
        {"title_english": "LIBRETTO-431 Phase III", "summary_english": "Phase III",
         "source_url": "https://nejm.org/1", "relevance_score": 9, "authority_score": 5,
         "lifecycle_stage": "Q2"},
    ]
    text = _build_findings_text(findings)
    assert "Authority: 5/5" in text
    assert "Stage: Q2" in text


# ── Guide generation ──

@patch("modules.guide_generator.api_call")
def test_generates_markdown_file(mock_api_call, tmp_path):
    # 16 section calls + 1 executive summary = 17 calls (no planner)
    mock_api_call.return_value = _mock_text("Section content here")

    findings = [
        {"title_english": "Finding 1", "summary_english": "Summary 1",
         "source_url": "https://example.com/1", "relevance_score": 9,
         "lifecycle_stage": "Q1", "authority_score": 3},
        {"title_english": "Finding 2", "summary_english": "Summary 2",
         "source_url": "https://example.com/2", "relevance_score": 7,
         "lifecycle_stage": "Q2", "authority_score": 4},
    ]
    output_path = str(tmp_path / "test-guide.md")
    generate_guide(
        topic_title="Cancer Diagnosis",
        findings=findings,
        output_path=output_path,
        api_key="fake-key",
    )
    assert os.path.exists(output_path)
    content = open(output_path).read()
    assert len(content) > 0
    assert "BEFORE ANYTHING ELSE" in content
    # No planner call -- should be 16 sections + 1 exec summary = 17 calls
    # (some sections may have 0 findings, but still generate a placeholder)


def test_no_findings_no_guide(tmp_path):
    output_path = str(tmp_path / "empty.md")
    generate_guide(
        topic_title="Test",
        findings=[],
        output_path=output_path,
        api_key="fake-key",
    )
    assert not os.path.exists(output_path)


def test_critical_sections_defined():
    assert "mistakes" in CRITICAL_SECTIONS
    assert "side-effects" in CRITICAL_SECTIONS
    assert "emergency-signs" in CRITICAL_SECTIONS
    assert "resistance" in CRITICAL_SECTIONS
    assert len(CRITICAL_SECTIONS) == 4


@patch("modules.guide_generator.api_call")
def test_critical_sections_use_sonnet(mock_api_call, tmp_path):
    """Critical sections should use critical_model (Sonnet), others Haiku."""
    models_used = []

    def track_model(client, **kwargs):
        models_used.append(kwargs.get("model", "unknown"))
        return _mock_text("Section content here")

    mock_api_call.side_effect = track_model

    # Provide findings for Q1 (non-critical) and Q7 (critical=mistakes)
    findings = [
        {"title_english": "F1", "summary_english": "S1",
         "source_url": "https://example.com/1", "relevance_score": 9,
         "authority_score": 5, "lifecycle_stage": "Q1"},
        {"title_english": "F2", "summary_english": "S2",
         "source_url": "https://example.com/2", "relevance_score": 8,
         "authority_score": 4, "lifecycle_stage": "Q7"},
        {"title_english": "F3", "summary_english": "S3",
         "source_url": "https://example.com/3", "relevance_score": 7,
         "authority_score": 3, "lifecycle_stage": "Q5"},
        {"title_english": "F4", "summary_english": "S4",
         "source_url": "https://example.com/4", "relevance_score": 7,
         "authority_score": 3, "lifecycle_stage": "Q3"},
    ]
    generate_guide(
        topic_title="Test Cancer",
        findings=findings,
        output_path=str(tmp_path / "split-guide.md"),
        api_key="fake-key",
        model="claude-haiku-4-5-20251001",
        critical_model="claude-sonnet-4-6",
    )

    assert "claude-sonnet-4-6" in models_used, f"Sonnet not used. Models: {models_used}"
    assert "claude-haiku-4-5-20251001" in models_used, f"Haiku not used. Models: {models_used}"


@patch("modules.guide_generator.api_call")
def test_cross_verify_report_passed_to_sections(mock_api_call, tmp_path):
    """Cross-verification report should be included in section generation prompts."""
    mock_api_call.return_value = _mock_text("Section content here")

    findings = [
        {"title_english": "F1", "summary_english": "S1",
         "source_url": "https://example.com/1", "relevance_score": 9,
         "lifecycle_stage": "Q1", "authority_score": 3},
    ]
    report = "CONTRADICTED: PFS 24.8mo -> USE Finding 7: PFS 22.0mo"
    generate_guide(
        topic_title="Test",
        findings=findings,
        output_path=str(tmp_path / "cv-guide.md"),
        api_key="fake-key",
        cross_verify_report=report,
    )

    found = any("CONTRADICTED" in str(c) for c in mock_api_call.call_args_list)
    assert found, "Cross-verification report not found in any API call"


@patch("modules.guide_generator.api_call")
def test_no_planner_call(mock_api_call, tmp_path):
    """v6: No planner call -- no tool_choice in any API call."""
    mock_api_call.return_value = _mock_text("Content")

    findings = [
        {"title_english": "F1", "summary_english": "S1",
         "source_url": "https://example.com/1", "relevance_score": 9,
         "lifecycle_stage": "Q2", "authority_score": 4},
    ]
    generate_guide(
        topic_title="Test",
        findings=findings,
        output_path=str(tmp_path / "out.md"),
        api_key="fake-key",
    )

    # No call should use tool_choice (planner removed)
    for c in mock_api_call.call_args_list:
        kwargs = c[1] if len(c) > 1 else {}
        assert "tool_choice" not in kwargs, f"Unexpected tool_choice in call: {kwargs}"


def test_section_briefs_cover_all_sections():
    for s in GUIDE_SECTIONS:
        assert s["id"] in SECTION_BRIEFS, f"Missing brief for section: {s['id']}"


def test_guide_sections_count_16():
    assert len(GUIDE_SECTIONS) == 16


def test_guide_sections_have_lifecycle():
    for s in GUIDE_SECTIONS:
        assert "lifecycle" in s, f"Missing lifecycle for section: {s['id']}"
