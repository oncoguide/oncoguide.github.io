# tests/test_skill_improver.py
import os
import pytest
from modules.skill_improver import append_learnings


def test_append_learnings_to_skill(tmp_path):
    skill_file = tmp_path / "test-skill.md"
    skill_file.write_text(
        "---\nname: test\n---\n\n## Persona\n\nDoctor.\n\n"
        "## Learnings\n\n<!-- Auto-updated -->\n"
    )
    append_learnings(str(skill_file), [
        "For RET fusion, always verify pralsetinib EU withdrawal status",
        "Hyperglycemia frequency is 53% -- verify in every RET guide",
    ])
    content = skill_file.read_text()
    assert "pralsetinib EU withdrawal" in content
    assert "Hyperglycemia frequency is 53%" in content


def test_append_learnings_no_duplicates(tmp_path):
    skill_file = tmp_path / "test-skill.md"
    skill_file.write_text(
        "---\nname: test\n---\n\n## Learnings\n\n"
        "- For RET, check withdrawal status\n"
    )
    append_learnings(str(skill_file), [
        "For RET, check withdrawal status",  # duplicate
        "New learning about EGFR",
    ])
    content = skill_file.read_text()
    assert content.count("withdrawal status") == 1
    assert "EGFR" in content


def test_append_learnings_no_section_creates_it(tmp_path):
    skill_file = tmp_path / "test-skill.md"
    skill_file.write_text("---\nname: test\n---\n\n## Persona\n\nDoctor.\n")
    append_learnings(str(skill_file), ["New learning"])
    content = skill_file.read_text()
    assert "## Learnings" in content
    assert "New learning" in content


def test_append_learnings_empty_list(tmp_path):
    skill_file = tmp_path / "test-skill.md"
    original = "---\nname: test\n---\n\n## Learnings\n\n"
    skill_file.write_text(original)
    append_learnings(str(skill_file), [])
    assert skill_file.read_text() == original
