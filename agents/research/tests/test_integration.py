"""End-to-end integration test with mocked API calls.

Verifies that data flows correctly between ALL pipeline phases:
discovery -> extraction -> search -> enrichment -> gap analysis ->
cross-verification -> guide generation -> validation -> review checklist

All external APIs (Anthropic, Serper, PubMed, etc.) are mocked.
Cost: $0.
"""

import json
import os
import sys

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# --- Realistic mock data for each phase ---

MOCK_DIAGNOSIS = "RET Fusion Non-Small Cell Lung Cancer"
MOCK_TOPIC_ID = "lung-ret-fusion"

MOCK_KNOWLEDGE_MAP = {
    "approved_drugs": [
        {"name": "selpercatinib", "brand": "Retevmo", "status": "FDA/EMA approved"}
    ],
    "pipeline_drugs": [
        {"name": "LOXO-260", "code": "LOXO-260", "phase": "Phase I/II", "mechanism": "next-gen RET"}
    ],
    "landmark_trials": [
        {"name": "LIBRETTO-001", "drug": "selpercatinib", "ORR%": 84, "PFS_months": 24.8}
    ],
    "side_effects": [
        {"effect": "hypertension", "frequency%": 35, "grade": "1-2"}
    ],
}

MOCK_DISCOVERY_RESULT = {
    "converged": True,
    "rounds": 3,
    "knowledge_map": MOCK_KNOWLEDGE_MAP,
    "section_scores": {
        "treatment-efficacy": {"score": 9, "assessment": "Strong"},
        "side-effects": {"score": 8.5, "assessment": "Adequate"},
    },
    "conversation": [
        "Oncologist: RET fusions occur in 1-2% of NSCLC...",
        "Advocate: Score 9/10 for treatment-efficacy...",
    ],
    "final_questions": [],
}

MOCK_QUERIES = [
    {"query_text": "selpercatinib LIBRETTO-001 ORR PFS",
     "search_engine": "serper", "language": "en", "target_section": "treatment-efficacy",
     "rationale": "Verify ORR and PFS from LIBRETTO-001"},
    {"query_text": "selpercatinib adverse events hypertension",
     "search_engine": "pubmed", "language": "en", "target_section": "side-effects",
     "rationale": "Verify hypertension frequency"},
    {"query_text": "RET fusion NSCLC clinical trials",
     "search_engine": "clinicaltrials", "language": "en", "target_section": "pipeline",
     "rationale": "Find active trials"},
]

MOCK_SEARCH_RESULTS = [
    {"title": "LIBRETTO-001: Selpercatinib in RET fusion NSCLC",
     "snippet": "ORR 84%, median PFS 24.8 months",
     "url": "https://nejm.org/libretto001", "source": "serper", "language": "en"},
    {"title": "Selpercatinib safety profile in RET-altered cancers",
     "snippet": "Hypertension in 35% of patients, mostly grade 1-2",
     "url": "https://pubmed.ncbi.nlm.nih.gov/12345", "source": "pubmed", "language": "en"},
    {"title": "LOXO-260 Phase I/II in RET-altered solid tumors",
     "snippet": "Next-generation RET inhibitor, preliminary ORR 75%",
     "url": "https://clinicaltrials.gov/ct2/show/NCT99999", "source": "clinicaltrials", "language": "en"},
]

MOCK_ENRICHMENTS = [
    {"relevant": True, "relevance_score": 9, "authority_score": 5,
     "title_english": "LIBRETTO-001: Selpercatinib in RET fusion NSCLC",
     "summary_english": "Phase III trial showing ORR 84%, median PFS 24.8 months."},
    {"relevant": True, "relevance_score": 8, "authority_score": 4,
     "title_english": "Selpercatinib safety profile",
     "summary_english": "Hypertension in 35% of patients, mostly grade 1-2."},
    {"relevant": True, "relevance_score": 7, "authority_score": 3,
     "title_english": "LOXO-260 Phase I/II",
     "summary_english": "Next-gen RET inhibitor, preliminary ORR 75%."},
]

# Findings as stored in DB (enriched + original merged)
MOCK_DB_FINDINGS = [
    {**MOCK_SEARCH_RESULTS[i], **MOCK_ENRICHMENTS[i],
     "source_url": MOCK_SEARCH_RESULTS[i]["url"],
     "content_hash": f"hash{i}", "topic_id": MOCK_TOPIC_ID}
    for i in range(3)
]

MOCK_CV_REPORT = {
    "verified": [
        {"claim": "ORR 84%", "finding_id": 1, "finding_value": "84%", "status": "VERIFIED"},
        {"claim": "PFS 24.8mo", "finding_id": 1, "finding_value": "24.8mo", "status": "VERIFIED"},
    ],
    "contradicted": [],
    "unverified": [
        {"claim": "OS data", "status": "UNVERIFIED", "reason": "no findings with OS data"},
    ],
}

MOCK_VALIDATION = {
    "passed": True,
    "overall_score": 8.7,
    "accuracy_issues": [],
    "safety_concerns": [],
    "missing_keywords": [],
    "section_scores": {
        "treatment-efficacy": {"score": 9, "assessment": "Strong", "gaps": []},
        "side-effects": {"score": 8.5, "assessment": "Adequate", "gaps": []},
    },
    "learnings": ["LOXO-260 data is preliminary"],
}


# --- Tests ---

def test_discovery_output_valid_for_keyword_extractor():
    """Discovery output (knowledge_map, conversation) is valid input for extract_queries."""
    result = MOCK_DISCOVERY_RESULT

    # extract_queries expects: diagnosis (str), conversation (list[str]), knowledge_map (dict)
    assert isinstance(result["conversation"], list)
    assert len(result["conversation"]) > 0
    assert isinstance(result["knowledge_map"], dict)
    # Knowledge map must have drug/trial data for query generation
    assert "approved_drugs" in result["knowledge_map"]
    assert "landmark_trials" in result["knowledge_map"]


def test_keyword_extractor_output_valid_for_searchers():
    """Extracted queries have all fields needed by searcher dispatch."""
    for q in MOCK_QUERIES:
        assert "query_text" in q and isinstance(q["query_text"], str)
        assert "search_engine" in q and q["search_engine"] in {
            "serper", "pubmed", "clinicaltrials", "openfda", "civic"
        }
        assert "language" in q and isinstance(q["language"], str)


def test_enrichment_output_valid_for_gap_analyzer():
    """Enriched findings have fields needed by gap_analyzer."""
    from modules.guide_generator import GUIDE_SECTIONS

    for f in MOCK_DB_FINDINGS:
        assert "relevance_score" in f
        assert "title_english" in f
        assert "summary_english" in f
        assert "source_url" in f

    # gap_analyzer also needs sections list
    assert len(GUIDE_SECTIONS) == 15
    for s in GUIDE_SECTIONS:
        assert "id" in s
        assert "title" in s
        assert "description" in s


def test_cross_verify_output_valid_for_guide_generator():
    """Cross-verification report can be formatted for guide_generator."""
    from modules.cross_verify import format_report

    report_text = format_report(MOCK_CV_REPORT)
    assert isinstance(report_text, str)
    assert len(report_text) > 0
    # Guide generator checks for these keywords in the report
    assert "VERIFIED" in report_text
    assert "UNVERIFIED" in report_text


@patch("modules.guide_generator.anthropic.Anthropic")
def test_guide_generator_output_valid_for_validation(mock_anthropic_cls, tmp_path):
    """Generated guide markdown is valid input for validate_guide."""
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client

    # Planner returns sections, section generator returns content
    call_count = [0]
    planner_json = json.dumps([
        {"id": "big-picture", "title": "Big Picture", "description": "D", "finding_ids": [1, 2]},
        {"id": "treatment-efficacy", "title": "Treatment", "description": "D", "finding_ids": [1]},
    ])

    def mock_create(**kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            text = planner_json
        else:
            text = "### Section content\n\nORR was 84% [[Finding 1](https://nejm.org/libretto001)]."
        return MagicMock(content=[MagicMock(text=text)])

    mock_client.messages.create.side_effect = mock_create

    from modules.cross_verify import format_report
    from modules.guide_generator import generate_guide

    output_path = str(tmp_path / "test-guide.md")
    generate_guide(
        topic_title=MOCK_DIAGNOSIS,
        findings=MOCK_DB_FINDINGS,
        output_path=output_path,
        api_key="fake",
        cross_verify_report=format_report(MOCK_CV_REPORT),
    )

    assert os.path.exists(output_path)
    guide_text = open(output_path).read()

    # validate_guide expects: guide_text (str), diagnosis (str), knowledge_map (dict)
    assert isinstance(guide_text, str)
    assert len(guide_text) > 100
    assert "# " in guide_text  # Has markdown headers
    assert MOCK_DIAGNOSIS in guide_text


def test_validation_output_valid_for_review_checklist(tmp_path):
    """Validation result generates a valid review checklist."""
    from run_research import _generate_review_checklist
    from modules.cross_verify import format_report

    review_path = str(tmp_path / "review.md")
    cv_text = format_report(MOCK_CV_REPORT)

    _generate_review_checklist(
        review_path, MOCK_TOPIC_ID, MOCK_DIAGNOSIS,
        MOCK_VALIDATION, cv_text,
        findings_count=len(MOCK_DB_FINDINGS),
        cost_report="$2.30",
    )

    assert os.path.exists(review_path)
    content = open(review_path).read()
    assert "Human Review Checklist" in content
    assert MOCK_DIAGNOSIS in content
    assert "change topic status to `drafting`" in content


def test_full_pipeline_data_contract():
    """Verify the full data contract: each phase's output fields match next phase's input needs."""
    from modules.cross_verify import format_report

    # Phase 1 -> Phase 2: discovery -> keyword_extractor
    discovery = MOCK_DISCOVERY_RESULT
    assert "conversation" in discovery  # needed by extract_queries
    assert "knowledge_map" in discovery  # needed by extract_queries

    # Phase 2 -> Phase 3: keyword_extractor -> searchers
    queries = MOCK_QUERIES
    for q in queries:
        assert "query_text" in q  # dispatched to searcher
        assert "search_engine" in q  # selects which searcher

    # Phase 3 -> Phase 4: search results -> enrichment
    for r in MOCK_SEARCH_RESULTS:
        assert "title" in r  # enrichment reads title
        assert "snippet" in r  # enrichment reads snippet
        assert "url" in r  # enrichment reads url

    # Phase 4 -> Phase 5: enriched findings -> gap_analyzer + cross_verify
    for f in MOCK_DB_FINDINGS:
        assert "relevance_score" in f  # gap_analyzer sorts by this
        assert "authority_score" in f  # cross_verify filters by this
        assert "title_english" in f  # guide_generator reads this
        assert "summary_english" in f  # guide_generator reads this
        assert "source_url" in f  # guide_generator cites this

    # Phase 5 -> Phase 6: cross_verify -> guide_generator
    report_text = format_report(MOCK_CV_REPORT)
    assert isinstance(report_text, str)  # guide_generator takes string

    # Phase 7 -> Phase 8: validation -> review checklist
    val = MOCK_VALIDATION
    assert "passed" in val
    assert "overall_score" in val
    assert "safety_concerns" in val
    assert "accuracy_issues" in val
    assert "section_scores" in val


# --- Abort condition tests ---


def test_count_findings_returns_correct_count(tmp_path):
    """Database.count_findings() returns correct finding count for a topic."""
    from modules.database import Database
    db = Database(str(tmp_path / "test.db"))
    db.create_tables()
    run_id = db.start_run("topic", "test-topic")

    assert db.count_findings("test-topic") == 0

    _finding_base = {
        "run_id": run_id, "topic_id": "test-topic",
        "title_original": "T", "snippet_original": "S",
        "source_language": "en", "summary_english": "Summary",
        "authority_score": 4, "source_url": "http://a.com",
        "source_domain": "a.com", "source_platform": "pubmed",
        "date_published": None, "date_found": "2026-01-01",
    }
    # Insert 2 findings
    db.insert_finding({**_finding_base, "content_hash": "h1", "title_english": "T1",
                       "relevance_score": 9.0, "source_url": "http://a.com"})
    db.insert_finding({**_finding_base, "content_hash": "h2", "title_english": "T2",
                       "relevance_score": 8.0, "source_url": "http://b.com"})
    assert db.count_findings("test-topic") == 2

    # Other topic is isolated
    assert db.count_findings("other-topic") == 0
    db.close()


@patch("run_research.pre_search")
@patch("run_research.run_discovery")
@patch("run_research.load_registry")
@patch("run_research.find_topic")
def test_pipeline_aborts_on_empty_knowledge_map(
    mock_find_topic, mock_load_registry, mock_run_discovery, mock_pre_search
):
    """cmd_topic raises RuntimeError if discovery returns empty knowledge_map."""
    import run_research

    mock_load_registry.return_value = [{"id": "test-topic", "title": "Test Diagnosis", "status": "planned"}]
    mock_find_topic.return_value = {"id": "test-topic", "title": "Test Diagnosis", "status": "planned"}
    mock_pre_search.return_value = ""
    mock_run_discovery.return_value = {
        "converged": False,
        "rounds": 1,
        "knowledge_map": {},  # empty -- should trigger abort
        "section_scores": {},
        "conversation": [],
        "final_questions": [],
    }

    with pytest.raises(RuntimeError, match="discovery"):
        run_research.cmd_topic(
            cfg={"anthropic_api_key": "fake", "database_path": ":memory:"},
            topic_id="test-topic",
            registry_path="fake_registry.yaml",
            dry_run=False,
            update_status=False,
        )
