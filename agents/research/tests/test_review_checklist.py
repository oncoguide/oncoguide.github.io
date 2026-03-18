import os
import pytest


def test_review_checklist_generated(tmp_path):
    """Review checklist markdown should be generated with all required sections."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from run_research import _generate_review_checklist

    review_path = str(tmp_path / "test-review.md")
    val_result = {
        "passed": True,
        "overall_score": 8.5,
        "safety_concerns": ["Drug X interaction not mentioned"],
        "accuracy_issues": ["PFS number differs from Phase III data"],
        "section_scores": {
            "best-treatment": {"score": 9, "notes": "Good"},
            "side-effects": {"score": 7, "notes": "Missing grade 1-2"},
        },
        "learnings": [],
    }
    cv_report = (
        "VERIFIED: ORR 71% confirmed by Finding 3\n"
        "CONTRADICTED: PFS 24.8mo -> Finding 7 shows PFS 22.0mo\n"
        "UNVERIFIED: OS data not found in any finding\n"
    )

    _generate_review_checklist(
        review_path, "lung-ret-fusion", "RET Fusion NSCLC",
        val_result, cv_report, findings_count=150, cost_report="$2.30",
    )

    assert os.path.exists(review_path)
    content = open(review_path).read()

    # Check all required sections
    assert "# Human Review Checklist" in content
    assert "Safety Concerns" in content
    assert "Drug X interaction not mentioned" in content
    assert "Accuracy Issues" in content
    assert "PFS number differs" in content
    assert "Cross-Verification" in content
    assert "CONTRADICTED" in content
    assert "UNVERIFIED" in content
    assert "Section Scores" in content
    assert "best-treatment" in content
    assert "Human Review Questions" in content
    assert "recently approved drugs" in content
    assert "Pipeline Summary" in content
    assert "$2.30" in content
    assert "change topic status to `drafting`" in content


def test_review_checklist_empty_validation(tmp_path):
    """Review checklist should handle empty validation gracefully."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from run_research import _generate_review_checklist

    review_path = str(tmp_path / "empty-review.md")
    val_result = {
        "passed": False,
        "overall_score": 0,
        "safety_concerns": [],
        "accuracy_issues": [],
        "section_scores": {},
        "learnings": [],
    }

    _generate_review_checklist(
        review_path, "test-topic", "Test Cancer",
        val_result, "", findings_count=0,
    )

    assert os.path.exists(review_path)
    content = open(review_path).read()
    assert "No safety concerns" in content
    assert "No accuracy issues" in content
    assert "not run or produced no report" in content
    assert "No per-section scores" in content
