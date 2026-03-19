import json
import os
import pytest
from unittest.mock import patch, MagicMock, Mock, call

from collections import defaultdict

from modules.guide_generator import (
    generate_guide, CRITICAL_SECTIONS, SECTION_BRIEFS, GUIDE_SECTIONS,
    _build_findings_text, _filter_findings_for_section, _get_lifecycle_prefixes,
    _format_grouped_findings, _group_findings_by_topic, _route_q3_findings,
    _assign_findings_to_sections, GROUP_FINDINGS_TOOL, ROUTE_Q3_TOOL,
    ROUTE_TO_SECTION, GUIDELINES_KEYWORDS, _identify_guidelines_groups,
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
        {"id": 1, "title_english": "Finding 1", "summary_english": "Summary 1",
         "source_url": "https://example.com/1", "relevance_score": 9,
         "lifecycle_stage": "Q1", "authority_score": 3, "content_hash": "h1"},
        {"id": 2, "title_english": "Finding 2", "summary_english": "Summary 2",
         "source_url": "https://example.com/2", "relevance_score": 7,
         "lifecycle_stage": "Q2", "authority_score": 4, "content_hash": "h2"},
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
        {"id": 1, "title_english": "F1", "summary_english": "S1",
         "source_url": "https://example.com/1", "relevance_score": 9,
         "authority_score": 5, "lifecycle_stage": "Q1", "content_hash": "h1"},
        {"id": 2, "title_english": "F2", "summary_english": "S2",
         "source_url": "https://example.com/2", "relevance_score": 8,
         "authority_score": 4, "lifecycle_stage": "Q7", "content_hash": "h2"},
        {"id": 3, "title_english": "F3", "summary_english": "S3",
         "source_url": "https://example.com/3", "relevance_score": 7,
         "authority_score": 3, "lifecycle_stage": "Q5", "content_hash": "h3"},
        {"id": 4, "title_english": "F4", "summary_english": "S4",
         "source_url": "https://example.com/4", "relevance_score": 7,
         "authority_score": 3, "lifecycle_stage": "Q3", "content_hash": "h4"},
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
        {"id": 1, "title_english": "F1", "summary_english": "S1",
         "source_url": "https://example.com/1", "relevance_score": 9,
         "lifecycle_stage": "Q1", "authority_score": 3, "content_hash": "h1"},
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
    """v6: No planner call. tool_choice only used by grouping/routing, not section generation."""
    mock_api_call.return_value = _mock_text("Content")

    findings = [
        {"id": 1, "title_english": "F1", "summary_english": "S1",
         "source_url": "https://example.com/1", "relevance_score": 9,
         "lifecycle_stage": "Q2", "authority_score": 4, "content_hash": "h1"},
    ]
    generate_guide(
        topic_title="Test",
        findings=findings,
        output_path=str(tmp_path / "out.md"),
        api_key="fake-key",
    )

    # Section generation calls should NOT use tool_choice (planner removed).
    # Only grouping/Q3 routing calls may use tool_choice.
    for c in mock_api_call.call_args_list:
        kwargs = c[1] if len(c) > 1 else {}
        if "tool_choice" in kwargs:
            # Must be a grouping or routing call, not a section generation call
            tool_name = kwargs["tool_choice"].get("name", "")
            assert tool_name in ("group_findings", "route_q3_findings"), \
                f"Unexpected tool_choice in section call: {kwargs}"


def test_section_briefs_cover_all_sections():
    for s in GUIDE_SECTIONS:
        assert s["id"] in SECTION_BRIEFS, f"Missing brief for section: {s['id']}"


def test_guide_sections_count_16():
    assert len(GUIDE_SECTIONS) == 16


def test_guide_sections_have_lifecycle():
    for s in GUIDE_SECTIONS:
        assert "lifecycle" in s, f"Missing lifecycle for section: {s['id']}"


# ── Tiered formatting ──

def _make_finding(id, authority=3, relevance=7, title="Test", summary="Summary text", url="http://example.com"):
    return {
        "id": id, "authority_score": authority, "relevance_score": relevance,
        "title_english": title, "summary_english": summary,
        "source_url": url, "content_hash": f"hash_{id:04d}",
    }


def test_format_single_group_small():
    """Small group: all findings become Tier 1 (full detail)."""
    findings = [_make_finding(i, authority=5) for i in range(10)]
    groups = [{"name": "Test Group", "findings": findings}]
    text, meta = _format_grouped_findings(groups)
    assert "HIGH-DETAIL" in text
    assert meta["tier1_count"] == 10
    assert "[F:0]" in text
    assert "Authority:5" in text
    assert "http://example.com" in text


def test_format_single_group_large():
    """Large group: top 20 Tier 1, rest Tier 2 with summaries."""
    findings = [_make_finding(i, authority=5 - i // 100, relevance=9 - i // 200) for i in range(200)]
    groups = [{"name": "Large Group", "findings": findings}]
    text, meta = _format_grouped_findings(groups)
    assert meta["tier1_count"] == 20
    assert "ADDITIONAL FINDINGS" in text
    # Tier 2 should have summaries, not just titles
    assert "Summary text" in text.split("ADDITIONAL FINDINGS")[1]


def test_format_respects_token_budget():
    """Truncates Tier 2 when budget exceeded."""
    findings = [_make_finding(i, authority=3, summary="A" * 50) for i in range(100)]
    groups = [{"name": "Budget Test", "findings": findings}]
    text, meta = _format_grouped_findings(groups, token_budget=1000)
    assert meta["tokens_used"] <= 1100  # Tier 1 exempt, but Tier 2 truncated
    assert "plus" in text.lower() and "more findings" in text.lower()


def test_format_tier1_budget_exempt():
    """Tier 1 is never truncated even with tight budget."""
    findings = [_make_finding(i, authority=5, summary="A" * 300) for i in range(20)]
    groups = [{"name": "Tier1 Test", "findings": findings}]
    text, meta = _format_grouped_findings(groups, token_budget=500)
    tier1_count = meta["tier1_count"]
    assert tier1_count >= 15  # min(20, max(15, 20//5))
    # Tier 1 exceeds budget -- that's by design
    assert meta["tokens_used"] > 500


def test_format_deterministic_ordering():
    """Same input produces same output."""
    findings = [_make_finding(i, authority=3, relevance=7) for i in range(50)]
    groups = [{"name": "Determinism", "findings": findings}]
    text1, _ = _format_grouped_findings(groups)
    text2, _ = _format_grouped_findings(groups)
    assert text1 == text2


def test_format_patient_source_priority():
    """prefer_patient_sources reverses sort order."""
    f_clinical = _make_finding(1, authority=5, relevance=7, title="Clinical trial")
    f_patient = _make_finding(2, authority=2, relevance=9, title="Patient experience")
    groups = [{"name": "Priority", "findings": [f_clinical, f_patient]}]
    text_default, _ = _format_grouped_findings(groups)
    text_patient, _ = _format_grouped_findings(groups, prefer_patient_sources=True)
    default_clinical_first = text_default.index("Clinical trial") < text_default.index("Patient experience")
    patient_patient_first = text_patient.index("Patient experience") < text_patient.index("Clinical trial")
    assert default_clinical_first
    assert patient_patient_first


def test_format_multiple_groups():
    """Multiple groups each get their own header and tiering."""
    g1 = [_make_finding(i, authority=5) for i in range(30)]
    g2 = [_make_finding(i + 100, authority=4) for i in range(25)]
    groups = [{"name": "Group A", "findings": g1}, {"name": "Group B", "findings": g2}]
    text, meta = _format_grouped_findings(groups)
    assert "GROUP A" in text
    assert "GROUP B" in text
    assert meta["total_findings"] == 55


# ── Smart Grouping ──

def test_group_findings_small_set_no_grouping():
    """< 500 findings: returns single 'all' group, no AI call."""
    findings = [_make_finding(i) for i in range(100)]
    groups = _group_findings_by_topic(findings, "test-key", "dummy-topic")
    assert len(groups) == 1
    assert groups[0]["name"] == "all"
    assert len(groups[0]["findings"]) == 100


def test_group_findings_assigns_all_ids():
    """Every finding ID appears in at least one group after AI grouping."""
    findings = [_make_finding(i) for i in range(600)]
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].input = {
        "groups": [
            {"name": "Group A", "finding_ids": list(range(0, 300))},
            {"name": "Group B", "finding_ids": list(range(200, 600))},  # overlap OK
        ]
    }
    with patch("modules.guide_generator.api_call", return_value=mock_response):
        groups = _group_findings_by_topic(findings, "test-key", "dummy-topic",
                                           api_key="test", model="test")
    all_ids_in_groups = set()
    for g in groups:
        all_ids_in_groups.update(f["id"] for f in g["findings"])
    assert all_ids_in_groups == set(range(600))


def test_group_findings_fallback_on_error():
    """If AI grouping fails, falls back to authority-tier grouping."""
    findings = [_make_finding(i, authority=(i % 5) + 1) for i in range(600)]
    with patch("modules.guide_generator.api_call", side_effect=Exception("API Error")):
        groups = _group_findings_by_topic(findings, "test-key", "dummy-topic",
                                           api_key="test", model="test")
    # Should have authority-tier groups instead of single "all"
    assert len(groups) >= 2
    # All findings accounted for
    all_ids = set()
    for g in groups:
        all_ids.update(f["id"] for f in g["findings"])
    assert all_ids == set(range(600))


def test_group_findings_orphans_collected():
    """Findings not assigned by AI are collected into 'Other Findings'."""
    findings = [_make_finding(i) for i in range(600)]
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    # Only assign 500 of 600 -- 100 orphans
    mock_response.content[0].input = {
        "groups": [
            {"name": "Group A", "finding_ids": list(range(0, 250))},
            {"name": "Group B", "finding_ids": list(range(250, 500))},
        ]
    }
    with patch("modules.guide_generator.api_call", return_value=mock_response):
        groups = _group_findings_by_topic(findings, "test-key", "dummy-topic",
                                           api_key="test", model="test")
    orphan_group = [g for g in groups if g["name"] == "Other Findings"]
    assert len(orphan_group) == 1
    assert len(orphan_group[0]["findings"]) == 100


def test_group_findings_tool_definition():
    """GROUP_FINDINGS_TOOL has correct schema shape."""
    assert GROUP_FINDINGS_TOOL["name"] == "group_findings"
    schema = GROUP_FINDINGS_TOOL["input_schema"]
    assert "groups" in schema["properties"]
    assert schema["properties"]["groups"]["type"] == "array"


# ── Q3 Routing ──

def test_route_q3_multi_category():
    """Q3 finding can be assigned to multiple sections."""
    findings = [_make_finding(0, title="Selpercatinib dose adjustment for QTc")]
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].input = {
        "routes": [
            {"finding_id": 0, "categories": ["dosing", "side-effects", "monitoring"]}
        ]
    }
    with patch("modules.guide_generator.api_call", return_value=mock_response):
        routes = _route_q3_findings(findings, "test", "test", "dummy-topic")
    assert 0 in routes["dosing"]
    assert 0 in routes["side-effects"]
    assert 0 in routes["monitoring"]


def test_route_q3_orphans_default_daily_life():
    """Unrouted Q3 findings default to daily-life."""
    findings = [_make_finding(0), _make_finding(1)]
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    # Only route finding 0, finding 1 is orphan
    mock_response.content[0].input = {
        "routes": [
            {"finding_id": 0, "categories": ["dosing"]}
        ]
    }
    with patch("modules.guide_generator.api_call", return_value=mock_response):
        routes = _route_q3_findings(findings, "test", "test", "dummy-topic")
    assert 1 in routes["daily-life"]


def test_route_q3_fallback_on_error():
    """If routing fails, all findings go to all sections."""
    findings = [_make_finding(0), _make_finding(1)]
    with patch("modules.guide_generator.api_call", side_effect=Exception("fail")):
        routes = _route_q3_findings(findings, "test", "test", "dummy-topic")
    # All categories should have all finding IDs
    for cat in ["dosing", "side-effects", "interactions", "monitoring",
                "emergency", "daily-life", "access"]:
        assert {0, 1} == routes[cat]


def test_route_q3_tool_definition():
    """ROUTE_Q3_TOOL has correct schema."""
    assert ROUTE_Q3_TOOL["name"] == "route_q3_findings"
    schema = ROUTE_Q3_TOOL["input_schema"]
    assert "routes" in schema["properties"]


# ── Section Assignment ──

def test_assign_findings_to_sections_basic():
    """Non-Q3 findings assigned by lifecycle prefix."""
    findings = [
        {**_make_finding(1), "lifecycle_stage": "Q1"},
        {**_make_finding(2), "lifecycle_stage": "Q2"},
        {**_make_finding(3), "lifecycle_stage": "Q7"},
    ]
    with patch("modules.guide_generator._route_q3_findings", return_value={}):
        section_findings = _assign_findings_to_sections(findings, "k", "m", "topic")
    assert any(f["id"] == 1 for f in section_findings.get("understanding-diagnosis", []))
    assert any(f["id"] == 2 for f in section_findings.get("best-treatment", []))
    assert any(f["id"] == 3 for f in section_findings.get("mistakes", []))


def test_assign_findings_q3_routed():
    """Q3 findings are routed via AI to specific sections."""
    findings = [
        {**_make_finding(10), "lifecycle_stage": "Q3"},
        {**_make_finding(11), "lifecycle_stage": "Q3"},
    ]
    mock_routes = defaultdict(set)
    mock_routes["dosing"] = {10}
    mock_routes["side-effects"] = {10, 11}
    mock_routes["monitoring"] = {11}

    with patch("modules.guide_generator._route_q3_findings", return_value=mock_routes):
        section_findings = _assign_findings_to_sections(findings, "k", "m", "topic")
    assert any(f["id"] == 10 for f in section_findings.get("how-to-take", []))
    assert any(f["id"] == 10 for f in section_findings.get("side-effects", []))
    assert any(f["id"] == 11 for f in section_findings.get("side-effects", []))
    assert any(f["id"] == 11 for f in section_findings.get("monitoring", []))


def test_assign_findings_q9_to_guidelines():
    """Q9 findings go to international-guidelines section."""
    findings = [
        {**_make_finding(50), "lifecycle_stage": "Q9"},
    ]
    with patch("modules.guide_generator._route_q3_findings", return_value={}):
        section_findings = _assign_findings_to_sections(findings, "k", "m", "topic")
    assert any(f["id"] == 50 for f in section_findings.get("international-guidelines", []))


def test_assign_findings_section15_excluded():
    """questions-for-doctor gets no findings (it uses prior section text)."""
    findings = [
        {**_make_finding(i), "lifecycle_stage": f"Q{(i % 8) + 1}"}
        for i in range(20)
    ]
    with patch("modules.guide_generator._route_q3_findings", return_value={}):
        section_findings = _assign_findings_to_sections(findings, "k", "m", "topic")
    # questions-for-doctor should not be populated by _assign_findings
    assert "questions-for-doctor" not in section_findings or len(section_findings["questions-for-doctor"]) == 0


# ── Guidelines group identification ──

def test_identify_guidelines_groups():
    """Groups with guidelines keywords are identified."""
    groups = [
        {"name": "ESMO Treatment Recommendations", "findings": [_make_finding(1)]},
        {"name": "Selpercatinib Efficacy Data", "findings": [_make_finding(2)]},
        {"name": "FDA Approval Timeline", "findings": [_make_finding(3)]},
    ]
    matched = _identify_guidelines_groups(groups)
    names = [g["name"] for g in matched]
    assert "ESMO Treatment Recommendations" in names
    assert "FDA Approval Timeline" in names
    assert "Selpercatinib Efficacy Data" not in names


def test_route_to_section_mapping():
    """ROUTE_TO_SECTION covers all Q3 routing categories."""
    expected = {"dosing", "side-effects", "interactions", "monitoring",
                "emergency", "daily-life", "access"}
    assert set(ROUTE_TO_SECTION.keys()) == expected
