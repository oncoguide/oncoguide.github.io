# Pre-Search: Ground Discovery Loop with Real Data

**Date:** 2026-03-16
**Status:** Draft
**Problem:** Discovery loop oncologist relies 100% on Claude's parametric knowledge. Drugs, trials, or data post-training-cutoff are invisible to the entire pipeline.
**Solution:** Add a pre-search phase before discovery that feeds real external findings to the oncologist as context.

---

## Architecture

### New Module: `agents/research/modules/pre_search.py`

**Responsibility:** Given a diagnosis string, generate mechanical + Claude queries, execute search across all backends, enrich with Haiku, return formatted top findings as context text.

**Interface:**

```python
def pre_search(
    diagnosis: str,
    cfg: dict,
    cost: CostTracker,
    max_findings: int = 50,
) -> str:
    """Run broad pre-search to ground discovery loop with real data.

    Returns formatted text with top findings, ready to inject into
    the oncologist's system prompt. Returns empty string on failure.
    """
```

**Returns:** A formatted string (not dict/list) ready for system prompt injection:

```
=== RECENT RESEARCH FINDINGS (pre-search) ===

[PubMed] "Selpercatinib vs chemotherapy-based treatment in RET fusion NSCLC:
LIBRETTO-431 phase III" (2025-03)
  ORR 84% vs 65%, PFS 24.8 vs 11.2 months. First-line approval basis.

[ClinicalTrials] "LOXO-260 Phase I in RET-altered solid tumors" (NCT05241834, recruiting)
  Sponsor: Eli Lilly. Next-gen RET inhibitor. Estimated completion 2026.

[Serper] "EMA approves selpercatinib for first-line RET fusion NSCLC" (2025-01)
  Extended indication covers treatment-naive patients.

(... up to 50 findings, max 15,000 chars ...)
```

### What pre_search does NOT do

- Does NOT write to the SQLite database (findings are ephemeral context)
- Does NOT deduplicate against existing DB findings
- Does NOT replace phases 3-5 (precision search still happens after discovery)

### Pipeline Integration

Current v4 pipeline:

```
1. Discovery loop (Sonnet)
2. Keyword extraction (Sonnet)
3. Search round 1 + enrichment (Haiku)
4. Gap analysis + search round 2 (Haiku)
5. Guide generation (Haiku)
6. Validation (Sonnet)
7. Skill self-improvement
```

Becomes:

```
0. Pre-search (NEW) -- template + Haiku queries, search all backends, enrich
1. Discovery loop (Sonnet) -- oncologist receives pre-search findings as context
2. Keyword extraction (Sonnet) -- unchanged
3-7. Unchanged
```

---

## Query Generation

### Phase A: Mechanical Templates (~20 queries, zero Claude, zero cost)

Templates use `{diagnosis}` and `{year}` (current year, computed at runtime via `datetime.now().year`) substitution only. No AI involvement -- this is the anchor that catches what Claude does not know.

| # | Template | Backend | Purpose |
|---|----------|---------|---------|
| 1 | `{diagnosis} treatment guidelines {year-1} {year}` | serper | Current protocols |
| 2 | `{diagnosis} approved drugs` | serper | All approved drugs |
| 3 | `{diagnosis} new drugs approved {year-1} {year}` | serper | Recently approved |
| 4 | `{diagnosis} new drugs pipeline development` | serper | Pipeline drugs |
| 5 | `{diagnosis} clinical trials recruiting` | clinicaltrials | Active trials |
| 6 | `{diagnosis} clinical trials phase III` | clinicaltrials | Late-stage trials |
| 7 | `{diagnosis} phase III results {year-1} {year}` | pubmed | Recent trial results |
| 8 | `{diagnosis} targeted therapy efficacy` | pubmed | Efficacy data |
| 9 | `{diagnosis} resistance mechanisms` | pubmed | Resistance |
| 10 | `{diagnosis} side effects toxicity incidence` | pubmed | Adverse events |
| 11 | `{diagnosis} survival outcomes PFS OS` | pubmed | Survival data |
| 12 | `{diagnosis} brain metastases intracranial` | pubmed | CNS disease |
| 13 | `{diagnosis} ESMO NCCN guidelines {year-1} {year}` | serper | Guidelines |
| 14 | `{diagnosis} biomarker testing molecular` | pubmed | Testing |
| 15 | `{diagnosis} immunotherapy combination` | pubmed | Combinations |
| 16 | `{diagnosis} drug withdrawal market exit` | serper | Withdrawals |
| 17 | `{diagnosis} patient quality of life` | pubmed | QoL |
| 18 | `{diagnosis} European access reimbursement` | serper | EU access |
| 19 | `{diagnosis}` | civic | Genomic variants |
| 20 | `{diagnosis}` | openfda | FDA safety data |

`{year}` = `datetime.now().year`, `{year-1}` = `datetime.now().year - 1`. Never hardcoded.

### Phase B: Claude Haiku Complement (~20 queries, ~$0.01)

Haiku receives:
- The diagnosis
- The list of template queries (so it does not duplicate them)
- Instruction: "Generate 20 complementary search queries using SPECIFIC terms: drug names, gene names, trial names, biomarker names. Focus on what the templates cannot catch -- named entities."

Haiku adds precision where templates are generic: "selpercatinib LIBRETTO-431 PFS", "pralsetinib EU withdrawal 2024", "LOXO-260 RET phase I Lilly".

### Total: ~40 queries across 5 backends

---

## Search + Enrichment

`pre_search.py` calls individual searcher functions and `enrich_batch` directly -- it does NOT use `_search_and_enrich` from `run_research.py` (which requires a DB). Instead:

1. Import searcher functions directly: `search_serper`, `search_pubmed`, `search_clinicaltrials`, `search_openfda`, `search_civic`
2. Execute all ~40 queries, skipping backends whose API keys are missing in `cfg` (graceful degradation -- e.g., skip OpenFDA if `openfda_api_key` is empty)
3. Deduplicate results in-memory by content hash (using `compute_content_hash` from utils)
4. Enrich with Haiku via `enrich_batch` from `enrichment.py`: relevant/irrelevant + score 1-10
5. Sort by relevance score descending
6. Take top `max_findings` (default 50 -- see Context Size section)
7. Format as human-readable text string

**Key difference from main search:** Results are NOT stored in DB. Deduplication is in-memory only. They exist only as context text for the discovery loop.

**Note on enrichment cost tracking:** The existing `enrichment.py` tracks tokens via its own internal counter (`get_token_usage`), not via `CostTracker`. Pre-search enrichment cost is therefore not covered by the $5 budget cap. After pre-search completes, `run_research.py` should estimate enrichment cost from `get_token_usage()` and log it. This is an existing pipeline limitation (enrichment has always been outside CostTracker) -- a future improvement could pass `CostTracker` into `enrich_batch`.

---

## Discovery Integration

### Modified: `modules/discovery.py`

`run_discovery()` gets a new parameter:

```python
def run_discovery(
    diagnosis: str,
    model: str,
    cost: CostTracker,
    api_key: str = "",
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    pre_search_context: str = "",   # NEW
) -> dict:
```

The `pre_search_context` string is injected into BOTH oncologist prompts:

1. `_oncologist_system()` -- initial knowledge map generation
2. `_oncologist_respond_system()` -- follow-up rounds (so the oncologist retains access to grounding data when answering advocate's questions)

```
{skill_context}

You are participating in a DISCOVERY CONVERSATION about a specific cancer diagnosis.

=== REAL-WORLD RESEARCH DATA ===
The following findings come from PubMed, ClinicalTrials.gov, FDA, and other
authoritative sources. Use this data as your foundation. It may contain drugs,
trials, or data you were not previously aware of -- incorporate ALL of it.

{pre_search_context}

=== YOUR TASK ===
Your role: provide COMPLETE clinical knowledge for a patient education guide.
(... rest of existing prompt ...)
```

The advocate's prompt is NOT modified -- the advocate evaluates completeness against the guide sections, regardless of data source.

### Context Size Limit

With `max_findings=50` (default), the context string is typically 8,000-15,000 characters. This is injected into the system prompt for every oncologist call (initial + follow-up rounds). To keep costs manageable:

- Default `max_findings` is **50** (not 100)
- Each finding is formatted as 2-3 lines max (title + key data point)
- If context exceeds 15,000 chars, truncate with a note: "... ({N} more findings omitted, see full pre-search output in logs)"

### Modified: `run_research.py`

```python
# Phase 0: Pre-search (NEW)
print("Phase 0: Pre-search (grounding discovery with real data)...")
try:
    pre_context = pre_search(diagnosis, cfg, cost)
    print(f"  Pre-search: {len(pre_context)} chars of context from external sources")
except Exception as e:
    logger.error(f"Pre-search failed: {e}")
    print(f"  Pre-search failed ({e}), continuing without grounding data")
    pre_context = ""

# Phase 1: Discovery loop (existing, modified call)
discovery = run_discovery(
    diagnosis=diagnosis,
    model=discovery_model,
    cost=cost,
    api_key=cfg["anthropic_api_key"],
    max_rounds=cfg.get("max_discovery_rounds", 5),
    pre_search_context=pre_context,   # NEW
)
```

**Graceful degradation:** If pre-search fails entirely (network error, all backends down, Haiku API error), the pipeline continues with `pre_context=""`. Discovery falls back to parametric knowledge only -- same as current v4 behavior. No data is lost.

---

## Dry-Run Behavior

`--dry-run` means "no external search API calls" (consistent with existing CLI semantics). Pre-search generates and displays queries but does NOT execute them:

```
Phase 0: Pre-search (dry-run)...
  20 template queries:
    [serper] "RET fusion NSCLC treatment guidelines 2025 2026"
    [pubmed] "RET fusion NSCLC phase III results 2025 2026"
    ...
  + 18 Haiku complement queries:
    [pubmed] "selpercatinib LIBRETTO-431 progression-free survival"
    [serper] "LOXO-260 RET inhibitor phase I Lilly"
    ...
  (searches skipped in dry-run mode)

Phase 1: Discovery loop (no pre-search context in dry-run)...
Phase 2: Keyword extraction...
  72 precision queries extracted

--- DRY RUN ---
(queries listed)
Cost so far: $0.25
```

Pre-search Haiku query generation still runs (costs ~$0.01) so the user can see the full query plan. Discovery runs without pre-search context in dry-run mode.

---

## Cost Estimate

| Component | Model | Estimated Cost |
|-----------|-------|---------------|
| Template queries (20) | none | $0.00 |
| Haiku query generation | Haiku | ~$0.01 |
| Enrichment (~150 raw results) | Haiku | ~$0.05-0.10 |
| **Pre-search total** | | **~$0.06-0.11** |
| Discovery loop (now better-informed) | Sonnet | ~$0.30-0.80 |
| Rest of pipeline | mixed | ~$0.50-1.20 |
| **Pipeline total** | | **~$1.20-2.60** |

Budget cap remains $5. Pre-search adds <5% to total cost.

---

## Files Changed

| File | Change |
|------|--------|
| `agents/research/modules/pre_search.py` | **NEW** -- template queries, Haiku complement, search, enrich, format |
| `agents/research/tests/test_pre_search.py` | **NEW** -- tests for template generation, formatting, integration |
| `agents/research/modules/discovery.py` | Add `pre_search_context` parameter, inject into oncologist prompt |
| `agents/research/run_research.py` | Add Phase 0 call before discovery |
| `CLAUDE.md` | Update data flow documentation |

No changes to: keyword_extractor, gap_analyzer, guide_generator, validation, skill_improver, database, searchers, cost_tracker.

---

## Testing Strategy

| Test | What it verifies |
|------|-----------------|
| `test_template_queries_generated` | All ~20 templates produced with diagnosis substituted |
| `test_haiku_queries_complement` | Haiku generates queries, no duplicates with templates |
| `test_format_findings_as_context` | Output is readable text with source tags |
| `test_empty_results_returns_empty_string` | Graceful handling of no results |
| `test_max_findings_cap` | Respects max_findings limit |
| `test_pre_search_no_api_key` | Returns empty string gracefully |
| `test_discovery_with_pre_search_context` | Oncologist prompt includes findings |
| `test_discovery_without_pre_search_context` | Backward compatible (empty string default) |
| `test_template_years_dynamic` | Years use current year, not hardcoded |
| `test_skips_backend_without_api_key` | Skips OpenFDA queries when key missing |
| `test_context_truncated_at_limit` | Output truncated at 15,000 chars with note |
| `test_pre_search_failure_returns_empty` | Returns "" on exception, does not crash |

---

## What This Does NOT Solve

- **Post-cutoff data that is not indexed by any search engine yet** -- nothing can find unpublished data
- **Rare diagnoses with very few search results** -- pre-search may return little, but the pipeline still works (discovery falls back to parametric knowledge)
- **Cross-topic learning** -- discussed and deferred; each topic runs its own full pipeline
