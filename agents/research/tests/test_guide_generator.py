import json
import os
import pytest
from unittest.mock import patch, MagicMock, Mock, call

from modules.guide_generator import generate_guide, CRITICAL_SECTIONS


def _mock_tool_use(input_dict):
    """Helper: create a mock message with tool_use content (planner responses)."""
    mock_tool = Mock()
    mock_tool.type = "tool_use"
    mock_tool.input = input_dict
    mock_msg = Mock()
    mock_msg.content = [mock_tool]
    mock_msg.usage = Mock(input_tokens=100, output_tokens=50)
    return mock_msg


def _mock_text(text="Section content here"):
    """Helper: create a mock message with text content (section generation responses)."""
    return MagicMock(
        content=[MagicMock(text=text)],
        usage=MagicMock(input_tokens=100, output_tokens=50),
    )


_SINGLE_SECTION_PLAN = {
    "sections": [
        {"id": "big-picture", "title": "Big Picture", "description": "Overview section.", "finding_ids": [1]},
    ]
}


@patch("modules.guide_generator.anthropic.Anthropic")
def test_generates_markdown_file(mock_anthropic_cls, tmp_path):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    # First call = planner (tool use), subsequent calls = section generators (text)
    mock_client.messages.create.side_effect = [
        _mock_tool_use(_SINGLE_SECTION_PLAN),
        _mock_text("# Test Guide\n\n## Summary\nTest content"),
    ]
    findings = [
        {"title_english": "Finding 1", "summary_english": "Summary 1",
         "source_url": "https://example.com/1", "relevance_score": 9},
        {"title_english": "Finding 2", "summary_english": "Summary 2",
         "source_url": "https://example.com/2", "relevance_score": 7},
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


def test_no_findings_no_guide(tmp_path):
    output_path = str(tmp_path / "empty.md")
    generate_guide(
        topic_title="Test",
        findings=[],
        output_path=output_path,
        api_key="fake-key",
    )
    assert not os.path.exists(output_path)


def test_findings_text_includes_authority_score():
    """Guide generator should include authority_score in the findings text passed to Claude."""
    from modules.guide_generator import _build_findings_text
    findings = [
        {"title_english": "LIBRETTO-431 Phase III", "summary_english": "Phase III",
         "source_url": "https://nejm.org/1", "relevance_score": 9, "authority_score": 5},
        {"title_english": "Blog post", "summary_english": "Some info",
         "source_url": "https://blog.com/1", "relevance_score": 6, "authority_score": 1},
    ]
    text = _build_findings_text(findings)
    assert "Authority: 5/5" in text
    assert "Authority: 1/5" in text


def test_critical_sections_defined():
    """Critical sections list should contain exactly the 4 safety-critical section IDs."""
    assert "treatment-efficacy" in CRITICAL_SECTIONS
    assert "side-effects" in CRITICAL_SECTIONS
    assert "emergency-signs" in CRITICAL_SECTIONS
    assert "resistance" in CRITICAL_SECTIONS
    assert len(CRITICAL_SECTIONS) == 4


@patch("modules.guide_generator.anthropic.Anthropic")
def test_section_planner_uses_tool_call(mock_anthropic_cls, tmp_path):
    """Section planner must use tool_choice to guarantee structured output."""
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.side_effect = [
        _mock_tool_use(_SINGLE_SECTION_PLAN),
        _mock_text(),
    ]
    findings = [
        {"title_english": "F1", "summary_english": "S1",
         "source_url": "https://example.com/1", "relevance_score": 9},
    ]
    generate_guide(
        topic_title="Test",
        findings=findings,
        output_path=str(tmp_path / "out.md"),
        api_key="fake-key",
    )
    # First call is the planner
    planner_kwargs = mock_client.messages.create.call_args_list[0][1]
    assert planner_kwargs["tool_choice"] == {"type": "tool", "name": "submit_section_plan"}


@patch("modules.guide_generator.anthropic.Anthropic")
def test_critical_sections_use_sonnet(mock_anthropic_cls, tmp_path):
    """Critical sections should be generated with the critical_model (Sonnet), others with Haiku."""
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client

    # Track which model is used for each call
    models_used = []
    call_count = [0]

    # Planner returns 2 sections: one non-critical, one critical
    planner_sections = {
        "sections": [
            {"id": "big-picture", "title": "Big Picture", "description": "Overview.", "finding_ids": [1]},
            {"id": "treatment-efficacy", "title": "Treatment Efficacy", "description": "Efficacy data.", "finding_ids": [1]},
        ]
    }

    def track_model(**kwargs):
        models_used.append(kwargs.get("model", "unknown"))
        call_count[0] += 1
        # First call is planner (tool use), rest are section generators (text)
        if call_count[0] == 1:
            return _mock_tool_use(planner_sections)
        return _mock_text("Section content here")

    mock_client.messages.create.side_effect = track_model

    findings = [
        {"title_english": "F1", "summary_english": "S1",
         "source_url": "https://example.com/1", "relevance_score": 9, "authority_score": 5},
    ]
    output_path = str(tmp_path / "split-guide.md")
    generate_guide(
        topic_title="Test Cancer",
        findings=findings,
        output_path=output_path,
        api_key="fake-key",
        model="claude-haiku-4-5-20251001",
        critical_model="claude-sonnet-4-6",
    )

    # First call is the planner (uses base model), then 2 section calls
    # Check that Sonnet was used at least once (for critical sections)
    assert "claude-sonnet-4-6" in models_used, f"Sonnet not used. Models: {models_used}"
    # Check that Haiku was used for non-critical sections
    assert "claude-haiku-4-5-20251001" in models_used, f"Haiku not used. Models: {models_used}"


@patch("modules.guide_generator.anthropic.Anthropic")
def test_cross_verify_report_passed_to_sections(mock_anthropic_cls, tmp_path):
    """Cross-verification report should be included in section generation prompts."""
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client

    # First call = planner (tool use), second call = section generator (text)
    mock_client.messages.create.side_effect = [
        _mock_tool_use(_SINGLE_SECTION_PLAN),
        _mock_text("Section content here"),
    ]

    findings = [
        {"title_english": "F1", "summary_english": "S1",
         "source_url": "https://example.com/1", "relevance_score": 9},
    ]
    output_path = str(tmp_path / "cv-guide.md")
    report = "CONTRADICTED: PFS 24.8mo -> USE Finding 7: PFS 22.0mo"
    generate_guide(
        topic_title="Test",
        findings=findings,
        output_path=output_path,
        api_key="fake-key",
        cross_verify_report=report,
    )

    # Check that the report text appears in at least one of the section generation calls
    found = any("CONTRADICTED" in str(c) for c in mock_client.messages.create.call_args_list)
    assert found, "Cross-verification report not found in any API call"
