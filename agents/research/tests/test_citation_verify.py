from modules.guide_generator import verify_section_citations


def _make_finding(id, title="Test", summary="Summary"):
    return {"id": id, "title_english": title, "summary_english": summary}


def test_valid_citations():
    """All citations reference real findings, no issues."""
    text = "ORR was 64% [F:1] and PFS was 24.8 months [F:2]."
    findings = [
        _make_finding(1, summary="ORR 64% in treatment-naive"),
        _make_finding(2, summary="PFS 24.8 months in LIBRETTO-431"),
    ]
    issues = verify_section_citations(text, findings)
    assert len([i for i in issues if i["severity"] == "CRITICAL"]) == 0


def test_phantom_citation():
    """Citation to non-existent finding flagged as CRITICAL."""
    text = "ORR was 64% [F:999]."
    findings = [_make_finding(1, summary="ORR 64%")]
    issues = verify_section_citations(text, findings)
    critical = [i for i in issues if i["type"] == "PHANTOM_CITATION"]
    assert len(critical) == 1
    assert "999" in critical[0]["detail"]


def test_ungrounded_number():
    """Number cited but not in the finding's text."""
    text = "ORR was 85% [F:1]."
    findings = [_make_finding(1, summary="ORR was 64% in the trial")]
    issues = verify_section_citations(text, findings)
    major = [i for i in issues if i["type"] == "UNGROUNDED_NUMBER"]
    assert len(major) >= 1


def test_uncited_number():
    """Section with numbers but no citations flagged as WARNING."""
    text = "ORR was 64% and PFS was 24.8 months."
    findings = [_make_finding(1, summary="ORR 64%")]
    issues = verify_section_citations(text, findings)
    warnings = [i for i in issues if i["type"] == "UNCITED_NUMBER"]
    assert len(warnings) >= 1
