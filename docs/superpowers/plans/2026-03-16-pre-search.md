# Pre-Search Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pre-search phase (Phase 0) that grounds the discovery loop oncologist with real external data before it generates the knowledge map.

**Architecture:** Template-based queries (20, zero AI) + Haiku complement queries (20, ~$0.01) search all 5 backends, enrich with Haiku, top 50 findings injected as context into oncologist's system prompt. Ephemeral -- no DB writes.

**Tech Stack:** Python 3.11+, anthropic SDK, existing searcher modules, existing enrichment module.

**Spec:** `docs/superpowers/specs/2026-03-16-pre-search-design.md`

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `agents/research/modules/pre_search.py` | Generate template + Haiku queries, execute search, enrich, format as context string |
| `agents/research/tests/test_pre_search.py` | Tests for query generation, formatting, caps, graceful degradation |

### Modified Files
| File | Changes |
|------|---------|
| `agents/research/modules/discovery.py` | Add `pre_search_context` param to `run_discovery`, inject into both oncologist prompts |
| `agents/research/run_research.py` | Add Phase 0 before discovery, pass context, handle dry-run |
| `CLAUDE.md` | Update data flow to include Phase 0 |

---

## Chunk 1: Pre-Search Module (TDD)

### Task 1.1: Template Query Generation

**Files:**
- Create: `agents/research/tests/test_pre_search.py`
- Create: `agents/research/modules/pre_search.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_pre_search.py
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from modules.pre_search import generate_template_queries, generate_haiku_queries, format_findings, pre_search


def test_template_queries_generated():
    queries = generate_template_queries("RET fusion NSCLC")
    assert len(queries) == 20
    # All have diagnosis substituted
    for q in queries:
        assert "RET fusion NSCLC" in q["query_text"]
        assert q["search_engine"] in ("serper", "pubmed", "clinicaltrials", "openfda", "civic")


def test_template_years_dynamic():
    queries = generate_template_queries("RET fusion NSCLC")
    year = str(datetime.now().year)
    year_queries = [q for q in queries if year in q["query_text"]]
    assert len(year_queries) >= 4  # at least 4 templates use {year}


def test_template_no_hardcoded_years():
    queries = generate_template_queries("RET fusion NSCLC")
    all_text = " ".join(q["query_text"] for q in queries)
    # Should not contain hardcoded years from development time
    assert "2024" not in all_text


@patch("modules.pre_search.anthropic.Anthropic")
def test_haiku_queries_complement(mock_cls):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    haiku_queries = [
        {"query_text": "selpercatinib LIBRETTO-431 PFS", "search_engine": "pubmed"},
        {"query_text": "LOXO-260 RET phase I Lilly", "search_engine": "serper"},
    ]
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=json.dumps(haiku_queries))],
        usage=MagicMock(input_tokens=1000, output_tokens=500),
    )

    from modules.cost_tracker import CostTracker
    ct = CostTracker()
    templates = generate_template_queries("RET fusion NSCLC")
    result = generate_haiku_queries("RET fusion NSCLC", templates, "fake-key", ct)
    assert len(result) == 2
    assert result[0]["search_engine"] == "pubmed"


def test_haiku_queries_no_api_key():
    from modules.cost_tracker import CostTracker
    ct = CostTracker()
    templates = generate_template_queries("RET fusion NSCLC")
    result = generate_haiku_queries("RET fusion NSCLC", templates, "", ct)
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents/research && python -m pytest tests/test_pre_search.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement query generation**

```python
# modules/pre_search.py
"""Pre-search: ground discovery loop with real external data.

Generates template queries (mechanical, zero AI) + Haiku complement queries,
searches all backends, enriches with Haiku, returns formatted top findings
as context text for the oncologist's system prompt.
"""

import json
import logging
import time
from datetime import datetime

import anthropic

from .cost_tracker import CostTracker
from .enrichment import enrich_batch
from .searcher_serper import search_serper
from .searcher_pubmed import search_pubmed
from .searcher_clinicaltrials import search_clinicaltrials
from .searcher_openfda import search_openfda
from .searcher_civic import search_civic
from .utils import compute_content_hash

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 15_000

# --- Template definitions ---
# {diagnosis} and {year}/{year_prev} are substituted at runtime.

TEMPLATES = [
    ("{diagnosis} treatment guidelines {year_prev} {year}", "serper"),
    ("{diagnosis} approved drugs", "serper"),
    ("{diagnosis} new drugs approved {year_prev} {year}", "serper"),
    ("{diagnosis} new drugs pipeline development", "serper"),
    ("{diagnosis} clinical trials recruiting", "clinicaltrials"),
    ("{diagnosis} clinical trials phase III", "clinicaltrials"),
    ("{diagnosis} phase III results {year_prev} {year}", "pubmed"),
    ("{diagnosis} targeted therapy efficacy", "pubmed"),
    ("{diagnosis} resistance mechanisms", "pubmed"),
    ("{diagnosis} side effects toxicity incidence", "pubmed"),
    ("{diagnosis} survival outcomes PFS OS", "pubmed"),
    ("{diagnosis} brain metastases intracranial", "pubmed"),
    ("{diagnosis} ESMO NCCN guidelines {year_prev} {year}", "serper"),
    ("{diagnosis} biomarker testing molecular", "pubmed"),
    ("{diagnosis} immunotherapy combination", "pubmed"),
    ("{diagnosis} drug withdrawal market exit", "serper"),
    ("{diagnosis} patient quality of life", "pubmed"),
    ("{diagnosis} European access reimbursement", "serper"),
    ("{diagnosis}", "civic"),
    ("{diagnosis}", "openfda"),
]


def generate_template_queries(diagnosis: str) -> list[dict]:
    """Generate mechanical template queries from diagnosis. Zero AI, zero cost."""
    year = datetime.now().year
    year_prev = year - 1
    queries = []
    for template, engine in TEMPLATES:
        text = template.format(diagnosis=diagnosis, year=year, year_prev=year_prev)
        queries.append({
            "query_text": text,
            "search_engine": engine,
            "language": "en",
        })
    return queries


HAIKU_SYSTEM = """You are a medical research query specialist.

Given a cancer diagnosis and a list of existing template queries, generate 20 COMPLEMENTARY
search queries that the templates CANNOT produce.

Focus on SPECIFIC NAMED ENTITIES:
- Drug names (generic + brand): "selpercatinib", "Retevmo", "pralsetinib"
- Trial names: "LIBRETTO-431", "AcceleRET"
- Gene/biomarker names: "RET M918T", "KIF5B-RET"
- Specific side effects with drug: "selpercatinib hyperglycemia incidence"
- Drug codes for pipeline: "LOXO-260", "BOS172738"
- Manufacturer names for pipeline drugs

For each query, specify the best search backend:
- "pubmed" for clinical data, trial results, side effects
- "serper" for news, approvals, access, patient resources
- "clinicaltrials" for recruiting trials (use condition + drug name)

Return JSON array:
[{"query_text": "...", "search_engine": "pubmed|serper|clinicaltrials"}]

Return ONLY the JSON array. No duplicates with existing templates."""


def generate_haiku_queries(
    diagnosis: str,
    template_queries: list[dict],
    api_key: str,
    cost: CostTracker,
    model: str = "claude-haiku-4-5-20251001",
) -> list[dict]:
    """Generate complementary queries via Haiku. Adds named-entity precision."""
    if not api_key:
        logger.warning("No API key for Haiku query complement")
        return []

    templates_text = "\n".join(f"- [{q['search_engine']}] {q['query_text']}" for q in template_queries)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=3000,
            system=HAIKU_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Diagnosis: {diagnosis}\n\nExisting template queries:\n{templates_text}",
            }],
        )
        cost.track(model, message.usage.input_tokens, message.usage.output_tokens)

        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        queries = json.loads(raw)
        for q in queries:
            q.setdefault("language", "en")
        logger.info(f"Haiku generated {len(queries)} complement queries")
        return queries

    except Exception as e:
        logger.error(f"Haiku query generation failed: {e}")
        return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/research && python -m pytest tests/test_pre_search.py::test_template_queries_generated tests/test_pre_search.py::test_template_years_dynamic tests/test_pre_search.py::test_template_no_hardcoded_years tests/test_pre_search.py::test_haiku_queries_complement tests/test_pre_search.py::test_haiku_queries_no_api_key -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add agents/research/modules/pre_search.py agents/research/tests/test_pre_search.py
git commit -m "feat(research): add pre-search query generation (templates + Haiku complement)"
```

---

### Task 1.2: Search, Enrich, Format

**Files:**
- Modify: `agents/research/tests/test_pre_search.py` (add tests)
- Modify: `agents/research/modules/pre_search.py` (add search + format functions)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_pre_search.py`:

```python
def test_format_findings_as_context():
    findings = [
        {"title": "Study A", "snippet": "ORR 84%", "source": "pubmed", "url": "http://a.com", "relevance_score": 9.5},
        {"title": "Trial B", "snippet": "Phase I recruiting", "source": "clinicaltrials", "url": "http://b.com", "relevance_score": 8.0},
    ]
    result = format_findings(findings)
    assert "=== RECENT RESEARCH FINDINGS" in result
    assert "[pubmed]" in result.lower() or "[PubMed]" in result
    assert "Study A" in result
    assert "Trial B" in result


def test_empty_results_returns_empty_string():
    result = format_findings([])
    assert result == ""


def test_max_findings_cap():
    findings = [
        {"title": f"Study {i}", "snippet": "data", "source": "pubmed", "url": f"http://{i}.com", "relevance_score": 10 - i * 0.1}
        for i in range(100)
    ]
    result = format_findings(findings, max_findings=5)
    assert "Study 0" in result
    assert "Study 4" in result
    assert "Study 5" not in result


def test_context_truncated_at_limit():
    findings = [
        {"title": f"Study {i} " + "x" * 500, "snippet": "data " * 100, "source": "pubmed", "url": f"http://{i}.com", "relevance_score": 9.0}
        for i in range(100)
    ]
    result = format_findings(findings, max_findings=100)
    assert len(result) <= MAX_CONTEXT_CHARS + 200  # small buffer for truncation note


def test_skips_backend_without_api_key():
    """Template queries for openfda should be skipped if no API key."""
    from modules.pre_search import _get_available_searchers
    cfg = {"serper_api_key": "x", "pubmed_email": "x@x.com"}  # no openfda key
    searchers = _get_available_searchers(cfg)
    assert "openfda" not in searchers
    assert "serper" in searchers
    assert "pubmed" in searchers
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents/research && python -m pytest tests/test_pre_search.py::test_format_findings_as_context tests/test_pre_search.py::test_empty_results_returns_empty_string tests/test_pre_search.py::test_max_findings_cap tests/test_pre_search.py::test_context_truncated_at_limit tests/test_pre_search.py::test_skips_backend_without_api_key -v`
Expected: FAIL

- [ ] **Step 3: Implement search, enrich, format**

Add to `modules/pre_search.py`:

```python
# --- Searcher dispatch (no DB dependency) ---

def _get_available_searchers(cfg: dict) -> dict:
    """Return searcher functions for backends with available API keys."""
    searchers = {}
    if cfg.get("serper_api_key"):
        searchers["serper"] = lambda q, cfg, **kw: search_serper(
            q["query_text"], cfg["serper_api_key"], q.get("language", "en"),
            kw.get("date_from"), kw.get("date_to"), cfg.get("max_results_per_query", 10))
    if cfg.get("pubmed_email"):
        searchers["pubmed"] = lambda q, cfg, **kw: search_pubmed(
            q["query_text"], cfg["pubmed_email"],
            kw.get("date_from"), kw.get("date_to"), cfg.get("max_results_per_query", 10))
    # clinicaltrials has no API key requirement
    searchers["clinicaltrials"] = lambda q, cfg, **kw: search_clinicaltrials(
        q["query_text"], cfg.get("max_results_per_query", 10), kw.get("date_from"))
    if cfg.get("openfda_api_key"):
        searchers["openfda"] = lambda q, cfg, **kw: search_openfda(
            q["query_text"], cfg.get("openfda_api_key", ""),
            kw.get("date_from"), kw.get("date_to"), cfg.get("max_results_per_query", 10))
    # civic has no API key requirement
    searchers["civic"] = lambda q, cfg, **kw: search_civic(
        q["query_text"], cfg.get("max_results_per_query", 10))
    return searchers


def format_findings(findings: list[dict], max_findings: int = 50) -> str:
    """Format enriched findings as human-readable context string."""
    if not findings:
        return ""

    # Sort by relevance score descending, take top N
    sorted_findings = sorted(findings, key=lambda f: f.get("relevance_score", 0), reverse=True)
    top = sorted_findings[:max_findings]

    lines = ["=== RECENT RESEARCH FINDINGS (pre-search) ===\n"]
    for f in top:
        source = f.get("source", "unknown")
        title = f.get("title", "Untitled")[:200]
        snippet = f.get("snippet", "")[:300]
        date = f.get("date", "")
        date_str = f" ({date})" if date else ""

        lines.append(f"[{source}] \"{title}\"{date_str}")
        if snippet:
            lines.append(f"  {snippet}")
        lines.append("")

    result = "\n".join(lines)

    # Truncate if over limit
    if len(result) > MAX_CONTEXT_CHARS:
        omitted = len(top) - result[:MAX_CONTEXT_CHARS].count("[")
        result = result[:MAX_CONTEXT_CHARS].rsplit("\n", 1)[0]
        result += f"\n\n... ({omitted} more findings omitted, see logs for full output)"

    return result


def _execute_searches(queries: list[dict], cfg: dict, delay: float = 2.0) -> list[dict]:
    """Execute queries on available backends, return raw results with in-memory dedup."""
    searchers = _get_available_searchers(cfg)
    all_results = []
    seen_hashes = set()

    for i, q in enumerate(queries):
        engine = q.get("search_engine", "serper")
        searcher = searchers.get(engine)
        if not searcher:
            logger.debug(f"Skipping query for unavailable backend: {engine}")
            continue

        try:
            results = searcher(q, cfg)
            for r in results:
                ch = compute_content_hash("pre_search", r.get("title", ""), r.get("url", ""))
                if ch not in seen_hashes:
                    seen_hashes.add(ch)
                    r["_source_engine"] = engine
                    all_results.append(r)
        except Exception as e:
            logger.warning(f"Pre-search query failed [{engine}]: {e}")

        if delay > 0 and i < len(queries) - 1:
            time.sleep(delay)

    logger.info(f"Pre-search: {len(all_results)} unique results from {len(queries)} queries")
    return all_results


# --- Main entry point ---

def pre_search(
    diagnosis: str,
    cfg: dict,
    cost: CostTracker,
    max_findings: int = 50,
    dry_run: bool = False,
) -> str:
    """Run broad pre-search to ground discovery loop with real data.

    Args:
        diagnosis: Cancer diagnosis string
        cfg: Config dict with API keys and settings
        cost: CostTracker instance (tracks Haiku query generation only)
        max_findings: Max findings to include in context (default 50)
        dry_run: If True, generate queries but skip search execution

    Returns:
        Formatted text with top findings, or "" on failure/dry-run.
    """
    # Phase A: Template queries
    templates = generate_template_queries(diagnosis)
    logger.info(f"Pre-search: {len(templates)} template queries")

    # Phase B: Haiku complement
    haiku_queries = generate_haiku_queries(
        diagnosis, templates, cfg.get("anthropic_api_key", ""), cost,
    )
    logger.info(f"Pre-search: {len(haiku_queries)} Haiku complement queries")

    all_queries = templates + haiku_queries

    if dry_run:
        print(f"  {len(templates)} template queries + {len(haiku_queries)} Haiku complement queries")
        for q in all_queries:
            print(f"    [{q['search_engine']}] {q['query_text']}")
        print("  (searches skipped in dry-run mode)")
        return ""

    # Execute searches
    raw_results = _execute_searches(all_queries, cfg, delay=cfg.get("delay_between_searches", 2))
    if not raw_results:
        logger.warning("Pre-search returned no results")
        return ""

    print(f"  {len(raw_results)} unique results, enriching...")

    # Enrich
    enrichments = enrich_batch(
        raw_results, diagnosis, cfg.get("anthropic_api_key", ""),
        cfg.get("enrichment_model", "claude-haiku-4-5-20251001"),
        cfg.get("delay_between_enrichments", 0.3),
    )

    # Merge enrichment scores into results
    relevant = []
    for finding, enrichment in zip(raw_results, enrichments):
        if enrichment.get("relevant"):
            finding["relevance_score"] = enrichment.get("relevance_score", 0)
            finding["source"] = finding.get("_source_engine", finding.get("source", "unknown"))
            relevant.append(finding)

    logger.info(f"Pre-search: {len(relevant)} relevant out of {len(raw_results)} total")
    print(f"  {len(relevant)} relevant findings for discovery context")

    return format_findings(relevant, max_findings=max_findings)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/research && python -m pytest tests/test_pre_search.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add agents/research/modules/pre_search.py agents/research/tests/test_pre_search.py
git commit -m "feat(research): add pre-search execution, enrichment, and formatting"
```

---

## Chunk 2: Discovery Integration + Orchestration

### Task 2.1: Inject pre-search context into discovery prompts

**Files:**
- Modify: `agents/research/modules/discovery.py`
- Modify: `agents/research/tests/test_discovery.py` (add 2 tests)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_discovery.py`:

```python
def test_discovery_with_pre_search_context(mock_cls=None):
    """Test that pre-search context is injected into oncologist prompt."""
    from modules.discovery import _oncologist_system
    from modules.utils import load_skill_context
    import os

    # Load actual skill or use fallback
    skills_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".claude", "skills")
    skill_path = os.path.join(skills_dir, "oncologist.md")
    if os.path.exists(skill_path):
        skill_ctx = load_skill_context(skill_path)
    else:
        skill_ctx = "Test oncologist persona"

    context = "[PubMed] \"LOXO-260 Phase I\" (2025)\n  Next-gen RET inhibitor"
    prompt = _oncologist_system(skill_ctx, pre_search_context=context)
    assert "LOXO-260" in prompt
    assert "REAL-WORLD RESEARCH DATA" in prompt


def test_discovery_without_pre_search_context():
    """Test backward compatibility -- empty context does not break prompt."""
    from modules.discovery import _oncologist_system
    prompt = _oncologist_system("Test persona", pre_search_context="")
    assert "REAL-WORLD RESEARCH DATA" not in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents/research && python -m pytest tests/test_discovery.py::test_discovery_with_pre_search_context tests/test_discovery.py::test_discovery_without_pre_search_context -v`
Expected: FAIL (signature mismatch)

- [ ] **Step 3: Modify discovery.py**

In `modules/discovery.py`, update `_oncologist_system` to accept and inject pre-search context:

```python
def _oncologist_system(skill_context: str, pre_search_context: str = "") -> str:
    pre_search_block = ""
    if pre_search_context:
        pre_search_block = f"""

=== REAL-WORLD RESEARCH DATA ===
The following findings come from PubMed, ClinicalTrials.gov, FDA, and other
authoritative sources. Use this data as your foundation. It may contain drugs,
trials, or data you were not previously aware of -- incorporate ALL of it.

{pre_search_context}

"""

    return f"""{skill_context}
{pre_search_block}
You are participating in a DISCOVERY CONVERSATION about a specific cancer diagnosis.
Your role: provide COMPLETE clinical knowledge for a patient education guide.
... (rest of existing prompt unchanged) ..."""
```

Similarly update `_oncologist_respond_system`:

```python
def _oncologist_respond_system(skill_context: str, pre_search_context: str = "") -> str:
    pre_search_block = ""
    if pre_search_context:
        pre_search_block = f"""

=== REAL-WORLD RESEARCH DATA (reference) ===
{pre_search_context}

"""

    return f"""{skill_context}
{pre_search_block}
You are responding to specific questions from a patient advocate about a cancer diagnosis.
... (rest of existing prompt unchanged) ..."""
```

Update `_oncologist_initial` and `_oncologist_respond` to pass `pre_search_context` through.

Update `run_discovery` signature:

```python
def run_discovery(
    diagnosis: str,
    model: str,
    cost: CostTracker,
    api_key: str = "",
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    pre_search_context: str = "",
) -> dict:
```

Pass `pre_search_context` to `_oncologist_initial` and `_oncologist_respond` calls.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/research && python -m pytest tests/test_discovery.py -v`
Expected: ALL PASS (existing + 2 new)

- [ ] **Step 5: Commit**

```bash
git add agents/research/modules/discovery.py agents/research/tests/test_discovery.py
git commit -m "feat(research): inject pre-search context into discovery oncologist prompts"
```

---

### Task 2.2: Orchestrate Phase 0 in run_research.py

**Files:**
- Modify: `agents/research/run_research.py`

- [ ] **Step 1: Add import**

Add to imports in `run_research.py`:

```python
from modules.pre_search import pre_search
```

- [ ] **Step 2: Add Phase 0 to cmd_topic**

Insert before Phase 1 (discovery loop) in `cmd_topic`:

```python
    # Phase 0: Pre-search (ground discovery with real data)
    print("Phase 0: Pre-search (grounding discovery with real data)...")
    try:
        pre_context = pre_search(diagnosis, cfg, cost, dry_run=dry_run)
        if pre_context:
            print(f"  Pre-search: {len(pre_context)} chars of context from external sources")
        elif not dry_run:
            print("  Pre-search: no relevant findings (discovery will use parametric knowledge only)")
    except Exception as e:
        logger.error(f"Pre-search failed: {e}")
        print(f"  Pre-search failed ({e}), continuing without grounding data")
        pre_context = ""
```

Update the `run_discovery` call to pass `pre_search_context=pre_context`.

- [ ] **Step 3: Update dry-run block**

Move the dry-run exit AFTER Phase 0 + Phase 1 + Phase 2 (as before), but pre_search now handles its own dry-run output internally.

- [ ] **Step 4: Run all tests**

Run: `cd agents/research && python -m pytest tests/ -v`
Expected: ALL PASS (except pre-existing 2 env var failures in test_cli.py)

- [ ] **Step 5: Commit**

```bash
git add agents/research/run_research.py
git commit -m "feat(research): add Phase 0 pre-search to pipeline orchestration"
```

---

### Task 2.3: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update Data Flow section**

Add Phase 0 to the data flow list:

```
0. Pre-search: template queries (20) + Haiku complement (20), search all backends, enrich, top 50 findings as context
1. Discovery loop (Sonnet): oncologist (grounded with pre-search data) <-> advocate iterate until 8.5/10
2-8. (renumber, content unchanged)
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add Phase 0 pre-search to CLAUDE.md data flow"
```

---

## Chunk 3: Final Verification

### Task 3.1: Run full test suite

- [ ] **Step 1: Run all tests**

Run: `cd agents/research && python -m pytest tests/ -v`
Expected: ~70 tests, all pass except 2 pre-existing env var failures in test_cli.py.

- [ ] **Step 2: Verify import works**

Run: `cd agents/research && python -c "from modules.pre_search import pre_search; print('OK')"`
Expected: OK

---

## Testing Summary

| Test File | New Tests | What it covers |
|-----------|-----------|---------------|
| `test_pre_search.py` | 10 | Templates, Haiku complement, formatting, caps, truncation, backend skip, no API key |
| `test_discovery.py` | +2 | Pre-search context injection, backward compatibility |
| **Total new** | **12** | |
| **Existing** | **58** | All v4 modules |
| **Grand total** | **~70** | |
