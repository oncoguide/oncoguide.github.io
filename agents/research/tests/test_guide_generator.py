import os
import pytest
from unittest.mock import patch, MagicMock

from modules.guide_generator import generate_guide


@patch("modules.guide_generator.anthropic.Anthropic")
def test_generates_markdown_file(mock_anthropic_cls, tmp_path):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# Test Guide\n\n## Summary\nTest content")],
        usage=MagicMock(input_tokens=500, output_tokens=200),
    )
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
