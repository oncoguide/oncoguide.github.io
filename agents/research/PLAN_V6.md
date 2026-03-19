# OncoGuide Research Agent v6 -- Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve the research pipeline from v5 (free-form discovery, 15 sections, 2-layer validation) to v6 (lifecycle Q1-Q8 discovery, 16 sections + executive summary, 6-layer validation, monitoring mode, seed data import, auto-learning).

**Architecture:** Modify existing modules in-place where possible; create 4 new modules for monitoring. All changes respect the existing pattern: tool_choice for structured output, CostTracker for budget, streaming api_call from utils.py. The pipeline remains sequential (phases 0-8), with per-section parallelism only in guide generation.

**Tech Stack:** Python 3.13, anthropic SDK, SQLite (WAL mode), PyYAML, pytest. Models: claude-sonnet-4-6 (discovery, validation, critical sections), claude-haiku-4-5-20251001 (everything else).

**Key constraint:** Every decision answers "Does this help the patient?" (VISION.md P1).

**Language rule:** ALL output (plan, guides, code comments, CLI messages) MUST be in English. No Romanian, no other languages. This includes generated guide section titles -- they are English, not Romanian.

---

## Database Strategy

The v6 database is the EXISTING `data/research.db` with schema upgrades (new tables, new columns via ALTER TABLE migration). No new database file is created.

**Seed import for RET Fusion Positive:**
- **Source 1:** onco-blog `data/research.db` already contains 1037 findings for `lung-ret-fusion`. These stay in place; the migration adds `lifecycle_stage`, `is_seeded`, `seed_source` columns with NULL/0/NULL defaults.
- **Source 2:** CNA `ret_findings_v3.db` contains 2689 findings. These are COPIED (read-only) into `data/research.db`. The CNA database is opened in **read-only mode** (`?mode=ro`). Zero writes, zero deletes, zero modifications to CNA.
- **After seed:** ~3454 unique findings in `data/research.db`, all tagged `is_seeded=1` for CNA imports. Existing onco-blog findings are NOT re-tagged (they were created by this pipeline).
- **After reclassify:** Each finding gets a `lifecycle_stage` (Q1-Q9) and `authority_score` (1-5) via Haiku batch classification.

**RET Fusion guide generation approach (data-first):**
Since we already have 3454 findings, we skip discovery + search phases entirely:
1. Seed + reclassify (M1)
2. Implement v6 modules (M2-M5)
3. Dry-run to verify (M6a)
4. Generate guide directly from existing findings: gap analysis -> guide generation -> validation (M6b)
5. Only run full pipeline (including discovery + search) for NEW topics that have no seed data

---

## File Structure -- What Changes

### Untouched (zero changes)
- `modules/searcher_serper.py`
- `modules/searcher_pubmed.py`
- `modules/searcher_clinicaltrials.py`
- `modules/searcher_openfda.py`
- `modules/searcher_civic.py`
- `modules/utils.py`
- `modules/cross_verify.py`
- `modules/query_expander.py` (deprecated, kept)
- `modules/query_debate.py` (deprecated, kept)

### Modified
| File | What changes | Lines affected |
|------|-------------|----------------|
| `modules/database.py` | Add 5 new tables, 3 new columns on findings, migration logic | ~100 lines added |
| `modules/enrichment.py` | Add `lifecycle_stage` to tool schema + output | ~20 lines changed |
| `modules/discovery.py` | New Q1-Q8 tool schemas, new system prompts, advocate scores Q1-Q8 | ~250 lines rewritten |
| `modules/keyword_extractor.py` | Queries per lifecycle stage with minimums, multilingual expansion | ~80 lines changed |
| `modules/guide_generator.py` | 16 sections + INAINTE DE TOATE, new GUIDE_SECTIONS, section briefs | ~150 lines changed |
| `modules/gap_analyzer.py` | Gap analysis per lifecycle stage (not per section) | ~60 lines changed |
| `modules/validation.py` | 6 validation layers (Layer 1 structural QA, 1b brief adherence, 2 language, 3 consistency, 4 medical, 5 advocate) | ~400 lines added |
| `modules/pre_search.py` | Lifecycle-aware template queries | ~30 lines changed |
| `modules/cost_tracker.py` | Add budget prioritization logic (degrade Haiku when near cap) | ~20 lines added |
| `modules/skill_improver.py` | Differentiated [MEDICAL] vs [EXPERIENTA] learning extraction | ~40 lines changed |
| `run_research.py` | Add --seed, --reclassify, --monitor, --force-phase, --rollback, --mock, health check, pipeline dashboard, gates | ~300 lines added |

### New Files
| File | Purpose | Estimated size |
|------|---------|---------------|
| `modules/monitor.py` | Monitoring orchestrator (M0-M6) | ~200 lines |
| `modules/monitor_queries.py` | Query generation for monitoring | ~80 lines |
| `modules/change_detector.py` | Alert classification rules | ~120 lines |
| `modules/living_guide.py` | Entity extraction + guide patching | ~150 lines |

### Skills Modified
| File | Change |
|------|--------|
| `.claude/skills/oncologist.md` | Adapt for Q1-Q8 lifecycle, [MEDICAL] learning prefixes |
| `.claude/skills/patient-advocate.md` | Adapt for 16 sections, [EXPERIENTA] learning prefixes |
| `.claude/skills/research.md` | Full rewrite for v6 pipeline |
| `.claude/skills/monthly-review.md` | DELETE (absorbed into research) |
| `.claude/skills/new-topic.md` | Extend with lifecycle preview |
| `.claude/skills/ux.md` | Extend with guide UX evaluation |

---

## Milestone 1: Seed Data + DB Migration

**Goal:** Import 3454 existing findings from CNA + onco-blog databases, add new schema.

**Files:**
- Modify: `modules/database.py`
- Modify: `run_research.py`
- Test: `tests/test_database.py`

### Task 1.1: Add new columns to findings table

- [ ] **Step 1: Write failing test for migration**

```python
# tests/test_database.py -- add to existing test file
def test_migration_adds_lifecycle_stage_column(tmp_path):
    """After create_tables, findings should have lifecycle_stage, is_seeded, seed_source columns."""
    db = Database(str(tmp_path / "test.db"))
    db.create_tables()
    cols = [row[1] for row in db.execute("PRAGMA table_info(findings)").fetchall()]
    assert "lifecycle_stage" in cols
    assert "is_seeded" in cols
    assert "seed_source" in cols
    db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/research && source .venv/bin/activate && python3 -m pytest tests/test_database.py::test_migration_adds_lifecycle_stage_column -v`
Expected: FAIL -- columns don't exist

- [ ] **Step 3: Add migration in database.py _migrate()**

In `modules/database.py`, extend `_migrate()` to add the 3 new columns:
```python
# In _migrate(), after existing authority_score migration:
if "lifecycle_stage" not in cols:
    self.conn.execute("ALTER TABLE findings ADD COLUMN lifecycle_stage TEXT")
if "is_seeded" not in cols:
    self.conn.execute("ALTER TABLE findings ADD COLUMN is_seeded INTEGER DEFAULT 0")
if "seed_source" not in cols:
    self.conn.execute("ALTER TABLE findings ADD COLUMN seed_source TEXT")
self.conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_database.py::test_migration_adds_lifecycle_stage_column -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add modules/database.py tests/test_database.py
git commit -m "feat(db): add lifecycle_stage, is_seeded, seed_source columns to findings"
```

### Task 1.2: Create new tables (pipeline_state, monitor_runs, alerts, tracked_entities, findings_archive)

- [ ] **Step 1: Write failing test**

```python
def test_new_tables_created(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.create_tables()
    tables = [row[0] for row in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for expected in ["pipeline_state", "monitor_runs", "alerts", "tracked_entities", "findings_archive"]:
        assert expected in tables, f"Missing table: {expected}"
    db.close()
```

- [ ] **Step 2: Run test -- expect FAIL**

- [ ] **Step 3: Add CREATE TABLE statements to create_tables()**

Add the 5 table definitions from SPEC.md 10.10 into `database.py` `create_tables()`.

- [ ] **Step 4: Run test -- expect PASS**

- [ ] **Step 5: Add helper methods for new tables**

Add to `database.py`:
- `save_pipeline_state(topic_id, run_id, phase, phase_name, status, output_ref, cost_usd, duration_seconds, error)`
- `get_last_completed_phase(topic_id) -> int | None`
- `save_alert(monitor_run_id, topic_id, severity, category, title, description, finding_ids)`
- `get_unacknowledged_alerts(topic_id) -> list[dict]`
- `acknowledge_alert(alert_id)`
- `save_tracked_entity(topic_id, entity_type, canonical_name, aliases, guide_sections)`
- `get_tracked_entities(topic_id) -> list[dict]`
- `archive_old_findings(topic_id, max_age_days=180, min_relevance=3)`
- `start_monitor_run(topic_id, since_date) -> int`
- `finish_monitor_run(run_id, stats)`

- [ ] **Step 6: Write tests for each helper method**

- [ ] **Step 7: Run all database tests -- expect PASS**

Run: `python3 -m pytest tests/test_database.py -v`

- [ ] **Step 8: Commit**

```bash
git add modules/database.py tests/test_database.py
git commit -m "feat(db): add pipeline_state, monitor_runs, alerts, tracked_entities, findings_archive tables"
```

### Task 1.2b: Update insert_finding() for new columns

- [ ] **Step 1: Write test**

```python
def test_insert_finding_stores_lifecycle_stage(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.create_tables()
    run_id = db.start_run("test", "test-topic")
    db.insert_finding({
        "content_hash": "abc123", "topic_id": "test-topic",
        "title_original": "Test", "snippet_original": "Snippet",
        "source_language": "en", "title_english": "Test",
        "summary_english": "Summary", "relevance_score": 8,
        "authority_score": 4, "source_url": "http://example.com",
        "source_domain": "example.com", "source_platform": "serper",
        "date_published": "2026-01-01", "date_found": "2026-03-18",
        "run_id": run_id,
        "lifecycle_stage": "Q3", "is_seeded": 0, "seed_source": None,
    })
    row = db.execute("SELECT lifecycle_stage, is_seeded FROM findings WHERE content_hash='abc123'").fetchone()
    assert row["lifecycle_stage"] == "Q3"
    assert row["is_seeded"] == 0
    db.close()
```

- [ ] **Step 2: Update insert_finding() in database.py**

Add `lifecycle_stage`, `is_seeded`, `seed_source` to the INSERT statement with `.get()` defaults.

- [ ] **Step 3: Run test -- expect PASS**

- [ ] **Step 4: Commit**

### Task 1.3: Implement --seed command

- [ ] **Step 1: Write test for seed import from onco-blog DB**

```python
# tests/test_cli.py or tests/test_seed.py
def test_seed_imports_from_onco_blog_db(tmp_path):
    """Seed should import findings from onco-blog research.db."""
    # Create a mock source DB with known findings
    # Run seed logic
    # Verify findings exist in target DB with is_seeded=1, seed_source="onco-blog"
```

- [ ] **Step 2: Implement cmd_seed() in run_research.py**

Logic:
1. Open source onco-blog DB (path from --seed-source or default `data/research.db`)
2. Check if seed already ran for this topic (search_runs with run_type="seed_onco")
3. If already seeded, print message and return
4. Read all findings for topic_id from source
5. Insert into target DB with `is_seeded=1, seed_source="onco-blog"`, lifecycle_stage=NULL
6. Create search_run with run_type="seed_onco"
7. Report: "{N} findings imported"

- [ ] **Step 3: Implement CNA import**

Logic for CNA DB (`/Users/dorins/Documents/cancer-news-agent/data/ret_findings_v3.db`):

**CRITICAL: CNA database is opened READ-ONLY. Zero writes, zero deletes, zero modifications.**
```python
cna_conn = sqlite3.connect(f"file:{cna_path}?mode=ro", uri=True)
```

1. CNA schema mapping `section` -> `lifecycle_stage`:
   ```python
   CNA_SECTION_MAP = {
       "my_treatment": "Q2",       # includes Q3 -- reclassify later
       "resistance": "Q5",
       "daily_life": "Q3",
       "alerts_safety": "Q3",
       "patient_community": "Q8",
       "research_pipeline": "Q6",
   }
   ```
2. CNA has no `topic_id` column -- import ALL findings with topic_id from --topic arg
3. CNA has no `authority_score` -- set to 0 (reclassify fills it)
4. Content hash recalculation: `SHA256(f"{topic_id}|{title.lower().strip()}|{url.lower().strip()}")` (SPEC 10.14)
5. Dedup by content_hash and source_url against existing onco-blog findings
6. Mark `is_seeded=1, seed_source="cna"`
7. Close CNA connection immediately after SELECT completes

- [ ] **Step 4: Add --seed CLI argument**

```python
parser.add_argument("--seed", action="store_true", help="Import seed data from existing DBs")
parser.add_argument("--seed-cna-path", type=str,
    default="/Users/dorins/Documents/cancer-news-agent/data/ret_findings_v3.db",
    help="Path to CNA database for seed import")
```

- [ ] **Step 5: Run test -- expect PASS**

- [ ] **Step 6: Commit**

### Task 1.4: Implement --reclassify command

- [ ] **Step 1: Write test for reclassify**

```python
def test_reclassify_sets_lifecycle_stage(mock_anthropic):
    """Reclassify should set lifecycle_stage and authority_score for findings with NULL values."""
```

- [ ] **Step 2: Implement cmd_reclassify() in run_research.py**

Logic:
1. Get all findings where lifecycle_stage IS NULL OR authority_score = 0
2. Batch in groups of 5
3. For each batch, call Haiku with enrichment-like prompt asking for lifecycle_stage (Q1-Q9) + authority_score (1-5)
4. Update findings in DB
5. Report per-stage distribution

- [ ] **Step 3: Add --reclassify CLI argument**

- [ ] **Step 4: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: All 121+ existing tests still pass

- [ ] **Step 5: Commit**

### Task 1.5: Verify M1

- [ ] **Verification: Run seed + reclassify on real data**

```bash
cd agents/research && source .venv/bin/activate
python3 run_research.py --seed --topic "lung-ret-fusion"
python3 run_research.py --reclassify --topic "lung-ret-fusion"
```

Then verify:
```sql
SELECT lifecycle_stage, COUNT(*) FROM findings WHERE topic_id='lung-ret-fusion' GROUP BY lifecycle_stage;
```
Expected: Distribution across Q1-Q9 (Q3 should be largest).

- [ ] **Commit milestone marker**

```bash
git commit --allow-empty -m "milestone: M1 seed data + DB migration complete"
```

---

## Milestone 2: Discovery Restructured (Q1-Q8)

**Goal:** Oncologist responds with Q1-Q8 structured knowledge; advocate scores per Q1-Q8.

**ORDERING NOTE:** SPEC Section 9 recommends defining guide template (GUIDE_SECTIONS) FIRST. Since `discovery.py` imports `GUIDE_SECTIONS` from `guide_generator.py`, Task 2.0 MUST update GUIDE_SECTIONS before changing discovery. This prevents the import mismatch.

**Files:**
- Modify: `modules/guide_generator.py` (GUIDE_SECTIONS only -- Task 2.0)
- Modify: `modules/discovery.py`
- Test: `tests/test_discovery.py`

### Task 2.0: Redefine GUIDE_SECTIONS first (per SPEC Section 9)

- [ ] **Step 1: Replace GUIDE_SECTIONS in guide_generator.py with v6 16-section list**

This is the same list detailed in M4 Task 4.1, but done HERE first so discovery.py does not break. Update CRITICAL_SECTIONS to `{"mistakes", "side-effects", "emergency-signs", "resistance"}`.

- [ ] **Step 2: Update all existing tests that reference old section IDs**

- [ ] **Step 3: Run tests -- expect PASS**

- [ ] **Step 4: Commit**

### Task 2.1: Define new tool schemas

- [ ] **Step 1: Write test for Q1-Q8 tool schema structure**

```python
def test_lifecycle_knowledge_tool_has_q1_q8():
    """The oncologist tool schema must have Q1-Q8 keys."""
    from modules.discovery import ONCOLOGIST_LIFECYCLE_TOOL
    props = ONCOLOGIST_LIFECYCLE_TOOL["input_schema"]["properties"]
    for q in ["Q1_diagnostic", "Q2_treatment", "Q3_living", "Q4_metastases",
              "Q5_resistance", "Q6_pipeline", "Q7_mistakes", "Q8_community"]:
        assert q in props, f"Missing {q} in tool schema"
```

- [ ] **Step 2: Implement ONCOLOGIST_LIFECYCLE_TOOL**

Replace `ONCOLOGIST_INITIAL_TOOL` with the Q1-Q8 structured schema from SPEC.md 10.3. Each Q has typed sub-fields (arrays of objects with specific properties).

- [ ] **Step 3: Implement ADVOCATE_LIFECYCLE_TOOL**

Replace `ADVOCATE_EVAL_TOOL` with schema that scores per Q1-Q8 (not per 15 sections).

- [ ] **Step 4: Run test -- expect PASS**

- [ ] **Step 5: Commit**

### Task 2.2: Update system prompts for Q1-Q8

- [ ] **Step 1: Rewrite _oncologist_system()**

The oncologist system prompt now instructs to fill Q1-Q8 with specific data types per question. References lifecycle framework from SPEC section 4.

- [ ] **Step 2: Rewrite _advocate_system()**

Advocate evaluates per Q1-Q8 instead of per 15 guide sections. Threshold remains 8.5. Include the 4-question first-read test.

- [ ] **Step 3: Update _oncologist_respond_system()**

Respond prompt references Q1-Q8 structure.

- [ ] **Step 4: Commit**

### Task 2.3: Update loop logic

- [ ] **Step 1: Update _oncologist_initial() to use new tool**

- [ ] **Step 2: Update _advocate_evaluate() to use new tool**

- [ ] **Step 3: Update _merge_knowledge() for Q1-Q8 structure**

The merge logic needs to handle nested Q1-Q8 objects instead of flat knowledge map keys.

- [ ] **Step 4: Update convergence check**

Check all Q1-Q8 scores >= 8.5 instead of section scores.

- [ ] **Step 5: Update run_discovery() return value**

The `knowledge_map` return key now contains Q1-Q8 structured data. `section_scores` becomes `lifecycle_scores`.

- [ ] **Step 6: Run discovery tests**

Run: `python3 -m pytest tests/test_discovery.py -v`
Expected: Update mocks to match new schemas, all tests pass.

- [ ] **Step 7: Commit**

### Task 2.4: Update downstream consumers of knowledge_map

- [ ] **Step 1: Update run_research.py to handle Q1-Q8 knowledge_map**

The `discovery["knowledge_map"]` is now Q1-Q8 structured. Update the abort check (min Q2 has 1 drug, etc.).

- [ ] **Step 2: Update validation.py oncologist review**

The knowledge_map passed to validation now has Q1-Q8 keys. Update the review system prompt.

- [ ] **Step 3: Update cross_verify.py compatibility**

cross_verify receives knowledge_map -- ensure it can handle Q1-Q8 structure (extract claims from nested fields).

- [ ] **Step 4: Run full test suite**

Run: `python3 -m pytest tests/ -v`

- [ ] **Step 5: Commit**

### Task 2.5: Verify M2

- [ ] **Verification: Dry-run on lung-ret-fusion**

```bash
python3 run_research.py --topic "lung-ret-fusion" --dry-run
```

Expected: Output shows Q1-Q8 structured discovery with scores per lifecycle stage. Cost ~$0.50.

- [ ] **Commit milestone marker**

---

## Milestone 3: Query Generation + Search (Lifecycle)

**Goal:** Queries generated per lifecycle stage with minimum counts per Q1-Q8.

**Files:**
- Modify: `modules/keyword_extractor.py`
- Modify: `modules/pre_search.py`
- Modify: `modules/enrichment.py`
- Test: `tests/test_keyword_extractor.py`, `tests/test_enrichment.py`

### Task 3.1: Update keyword_extractor for lifecycle stages

- [ ] **Step 1: Write test for lifecycle-tagged queries**

```python
def test_queries_have_lifecycle_stage(mock_anthropic_queries):
    """Each query should have a lifecycle_stage tag (Q1-Q9)."""
    queries = extract_queries(...)
    stages = {q.get("lifecycle_stage") for q in queries}
    assert stages.issuperset({"Q1", "Q2", "Q3", "Q5", "Q6"})
```

- [ ] **Step 2: Update tool schema**

Add `lifecycle_stage` field (enum Q1-Q9) to KEYWORD_TOOL. Replace `target_section` with `lifecycle_stage`.

- [ ] **Step 3: Update system prompt**

Include SPEC minimum counts per stage (Q1:5, Q2:10, Q3:20, Q4:8, Q5:10, Q6:12, Q7:5, Q8:4, Q9:5). Add multilingual expansion rules (SPEC 10.7).

- [ ] **Step 4: Update extract_queries() to accept Q1-Q8 knowledge_map**

- [ ] **Step 5: Run tests -- expect PASS**

- [ ] **Step 6: Commit**

### Task 3.2: Update pre_search templates for lifecycle

- [ ] **Step 1: Add lifecycle-specific template queries**

Add templates for Q4 (metastases), Q7 (mistakes), Q8 (community), Q9 (geographic access) that are currently missing.

- [ ] **Step 2: Run pre_search tests**

- [ ] **Step 3: Commit**

### Task 3.3: Update enrichment to output lifecycle_stage

- [ ] **Step 1: Write test for lifecycle_stage in enrichment output**

```python
def test_enrichment_returns_lifecycle_stage(mock_anthropic):
    result = enrich_finding(finding, topic, api_key)
    assert "lifecycle_stage" in result
    assert result["lifecycle_stage"] in ["Q1","Q2","Q3","Q4","Q5","Q6","Q7","Q8","Q9"]
```

- [ ] **Step 2: Update ENRICHMENT_TOOL schema**

Add `lifecycle_stage` field with enum values Q1-Q9.

- [ ] **Step 3: Update SYSTEM_PROMPT to instruct lifecycle classification**

- [ ] **Step 4: Update run_research.py to store lifecycle_stage**

In `_search_and_enrich()`, pass lifecycle_stage from enrichment to `db.insert_finding()`.

- [ ] **Step 5: Run all tests**

- [ ] **Step 6: Commit**

### Task 3.4: Verify M3

- [ ] **Verification: Dry-run shows lifecycle-tagged queries**

```bash
python3 run_research.py --topic "lung-ret-fusion" --dry-run
```

Expected: >= 100 queries, each tagged with lifecycle_stage. Each Q1-Q8 meets minimum count. Cost: $0 (dry-run).

- [ ] **Commit milestone marker**

### Task 3.5: Update gap_analyzer.py for lifecycle stages

**Files:**
- Modify: `modules/gap_analyzer.py`
- Test: `tests/test_gap_analyzer.py`

- [ ] **Step 1: Write test for lifecycle-based gap analysis**

```python
def test_gap_analysis_uses_lifecycle_stages(mock_anthropic):
    """Gap analysis should check findings per Q1-Q8, not per section ID."""
    findings = [{"lifecycle_stage": "Q2", "relevance_score": 9, "title_english": "..."}] * 20
    # Q3 has 0 findings -- should generate gap queries for Q3
    gap_queries = analyze_gaps(...)
    assert any(q.get("lifecycle_stage") == "Q3" for q in gap_queries)
```

- [ ] **Step 2: Replace section-based mapping with lifecycle-stage counting**

Use `lifecycle_stage` field from findings (populated by enrichment) instead of calling Haiku to map findings to sections. Count findings per Q1-Q8, compare against thresholds from SPEC Faza 4:

```python
LIFECYCLE_THRESHOLDS = {
    "Q1": 5, "Q2": 15, "Q3": 20, "Q4": 5,  # per site
    "Q5": 10, "Q6": 8, "Q7": 5, "Q8": 3,
}
```

- [ ] **Step 3: Update gap query generation to tag with lifecycle_stage**

- [ ] **Step 4: Run tests -- expect PASS**

- [ ] **Step 5: Commit**

### Task 3.6: Add budget prioritization to cost_tracker.py

- [ ] **Step 1: Add prioritized_budget_check() method**

When budget approaches cap ($5), prioritize: 1) Validation Sonnet, 2) Critical sections Sonnet, 3) Discovery Sonnet. Others degrade to Haiku.

```python
def get_recommended_model(self, purpose: str, default: str, fallback: str) -> str:
    """Return default model if budget allows, fallback if tight."""
    PRIORITY = {"validation": 1, "critical_section": 2, "discovery": 3}
    priority = PRIORITY.get(purpose, 99)
    remaining = self.max_cost_usd - self.total_cost_usd
    if remaining < 1.0 and priority > 2:
        return fallback
    if remaining < 0.5 and priority > 1:
        return fallback
    return default
```

- [ ] **Step 2: Write test**

- [ ] **Step 3: Commit**

### Task 3.7: Implement pipeline gates

- [ ] **Step 1: Add gate functions to run_research.py**

Each gate is a simple function returning (pass, reason):

```python
def _gate_0(pre_search_findings_count: int) -> tuple[bool, str]:
    """GATE 0: Min 20 findings from pre-search."""
    if pre_search_findings_count < 20:
        return False, f"Only {pre_search_findings_count} pre-search findings (min 20)"
    return True, ""

def _gate_1(knowledge_map: dict) -> tuple[bool, str]:
    """GATE 1: Discovery has minimum entities."""
    drugs = knowledge_map.get("Q2_treatment", {}).get("approved_drugs", [])
    resistance = knowledge_map.get("Q5_resistance", {}).get("mechanisms", [])
    pipeline = knowledge_map.get("Q6_pipeline", {}).get("drugs", [])
    if not drugs: return False, "No approved drugs in Q2"
    if not resistance: return False, "No resistance mechanisms in Q5"
    if not pipeline: return False, "No pipeline drugs in Q6"
    return True, ""

def _gate_2(queries: list, lifecycle_mins: dict) -> tuple[bool, str]:
    """GATE 2: Total >= 80 queries, per-stage minimums met."""
    ...

def _gate_3(findings_count: int) -> tuple[bool, str]:
    """GATE 3: Min 100 findings (hard stop at < 20)."""
    ...

def _gate_6(guide_path: str) -> tuple[bool, str]:
    """GATE 6: Guide >= 10KB, 16 sections + INAINTE DE TOATE present."""
    ...
```

- [ ] **Step 2: Insert gate checks after each phase in cmd_topic()**

Gates 0, 2 are warnings (continue with log). Gate 1 minimum entity check is a soft abort. Gate 3 < 20 is a hard abort. Gate 6 is a hard abort. Gate 7 is validation pass/fail (already in M5).

- [ ] **Step 3: Write tests for each gate function**

- [ ] **Step 4: Commit**

---

## Milestone 4: Guide Generation (16 Sections)

**Goal:** Generate guide with 16 lifecycle sections + INAINTE DE TOATE executive summary.

**Files:**
- Modify: `modules/guide_generator.py`
- Test: `tests/test_guide_generator.py`

### Task 4.1: Redefine GUIDE_SECTIONS for 16 lifecycle sections

- [ ] **Step 1: Write test for 16 sections**

```python
def test_guide_sections_count():
    from modules.guide_generator import GUIDE_SECTIONS
    assert len(GUIDE_SECTIONS) == 16
    ids = [s["id"] for s in GUIDE_SECTIONS]
    assert "mistakes" in ids  # Section 3 (Q7)
    assert "metastases" in ids  # Section 9 (Q4)
```

- [ ] **Step 2: Replace GUIDE_SECTIONS with v6 template**

Map from SPEC section 6 template:
```
1. understanding-diagnosis [Q1]
2. best-treatment [Q2]
3. mistakes [Q7] << CRITICAL (Sonnet)
4. how-to-take [Q3-dosing]
5. side-effects [Q3-effects] << CRITICAL (Sonnet)
6. interactions [Q3-interactions]
7. monitoring [Q3-monitoring]
8. emergency-signs [Q3-emergency] << CRITICAL (Sonnet)
9. metastases [Q4]
10. resistance [Q5] << CRITICAL (Sonnet)
11. pipeline [Q6]
12. daily-life [Q3-daily]
13. treatment-access [Q3-access + Q9]
14. community [Q8]
15. questions-for-doctor [Q1-Q8 derived]
16. international-guidelines [Q2-guidelines]
```

- [ ] **Step 3: Update CRITICAL_SECTIONS**

Change from `{"treatment-efficacy", "side-effects", "emergency-signs", "resistance"}` to `{"mistakes", "side-effects", "emergency-signs", "resistance"}` (sections 3, 5, 8, 10).

- [ ] **Step 4: Run test -- expect PASS**

- [ ] **Step 5: Commit**

### Task 4.2: Implement INAINTE DE TOATE generation

- [ ] **Step 1: Write test**

```python
def test_guide_contains_executive_summary(mock_anthropic):
    """Guide should contain '## INAINTE DE TOATE' section."""
    # Generate guide with mock, verify output contains the section
```

- [ ] **Step 2: Add _generate_executive_summary() function**

After all 16 sections are generated, call Haiku with sections 1-3 as input to produce the executive summary answering: Ce am? Exista tratament? Cat de serios? Ce fac ACUM? Max 200 words.

- [ ] **Step 3: Insert executive summary after guide header, before Section 1**

- [ ] **Step 4: Run test -- expect PASS**

- [ ] **Step 5: Commit**

### Task 4.3: Update section generation prompts

- [ ] **Step 1: Update SECTION_SYSTEM prompt**

Add section briefs from SPEC (what each section MUST contain). Include format requirements (tables, checkboxes for Section 8, GRESEALA/DE CE/IN SCHIMB format for Section 3).

- [ ] **Step 2: Update PLANNER_SYSTEM for 16 sections**

- [ ] **Step 3: Run guide generator tests**

- [ ] **Step 4: Commit**

### Task 4.4: Verify M4

- [ ] **Verification: Generate guide on lung-ret-fusion**

```bash
python3 run_research.py --topic "lung-ret-fusion"
# (will run full pipeline with seeded data -- should skip to gap analysis)
```

Verify: All 16 sections present in `data/guides/lung-ret-fusion.md`, INAINTE DE TOATE present. Cost: ~$1.00.

- [ ] **Commit milestone marker**

---

## Milestone 5: Validation (6 Layers)

**Goal:** Implement 6-layer validation pipeline: structural QA -> brief adherence -> language -> consistency -> medical -> advocate.

**Files:**
- Modify: `modules/validation.py`
- Test: `tests/test_validation.py`

### Task 5.1: Implement Layer 1 -- Structural QA (zero cost)

- [ ] **Step 1: Write test for structural checks**

```python
def test_structural_qa_detects_missing_section():
    guide = "## 1. CE AI\nContent\n## 2. TRATAMENT\nContent"  # only 2 of 16 sections
    result = structural_qa(guide)
    assert result["blocks"]  # has blocking issues
    assert any("section" in b.lower() for b in result["blocks"])

def test_structural_qa_detects_short_critical_section():
    # Critical sections (3,5,8,10) must be >= 500 words
    ...

def test_structural_qa_detects_missing_table():
    # Sections 2,5,6,7,11 must have tables
    ...

def test_structural_qa_detects_emojis():
    guide = "## 1. Section\nThis is great! 🎉"
    result = structural_qa(guide)
    assert any("emoji" in b.lower() for b in result["blocks"])
```

- [ ] **Step 2: Implement structural_qa() function**

Pure Python, zero API cost. Check:
- All 16 sections + INAINTE DE TOATE present
- Critical sections >= 500 words, others >= 200 words
- Required tables (sections 2, 5, 6, 7, 11)
- Section 8 has >= 5 checkboxes
- No emojis, no curly quotes, no em-dashes
- No paragraph > 5 lines
- Deduplicated sentences check

Returns: `{"blocks": [...], "warnings": [...]}`

- [ ] **Step 3: Run tests -- expect PASS**

- [ ] **Step 4: Commit**

### Task 5.2: Implement Layer 1b -- Section Brief Adherence (Haiku)

- [ ] **Step 1: Write test**

- [ ] **Step 2: Implement section_brief_check() function**

Haiku receives each section + its brief from SPEC. Returns per-section adherence score and fix suggestions. Score < 6 = BLOCK (regenerate section).

- [ ] **Step 3: Commit**

### Task 5.3: Implement Layer 2 -- Language & Tone (Haiku)

- [ ] **Step 1: Extend existing _check_language()**

Current implementation only checks for non-English text. Extend to also check:
- Direct address (tu/your, not "pacientul")
- Medical terms explained at first use
- Tone: no condescension, no false hope
- Jargon list

- [ ] **Step 2: Write tests**

- [ ] **Step 3: Commit**

### Task 5.4: Implement Layer 3 -- Consistency Check (Haiku)

- [ ] **Step 1: Implement consistency_check() function**

Haiku checks for:
- Same number appearing with different values across sections
- Duplicate information (move to primary section + reference)
- Side effects in Section 5 must have emergency-signs counterpart in Section 8
- Pipeline drugs in Section 10 (Plan B) must appear in Section 11

- [ ] **Step 2: Write tests**

- [ ] **Step 3: Commit**

### Task 5.5: Update Layer 4 (Medical Review) and Layer 5 (Advocate Review)

- [ ] **Step 1: Update oncologist review for Q1-Q8 knowledge map**

- [ ] **Step 2: Update advocate review for 16 sections + global tests**

Add: first-read test, scare test, actionability test, progression test. Per SPEC section 5b.

- [ ] **Step 3: Update advocate scoring to reference 16 section IDs**

- [ ] **Step 4: Commit**

### Task 5.6: Integrate all layers in refine_guide()

- [ ] **Step 1: Rewrite refine_guide() orchestrator**

```python
def refine_guide(...) -> dict:
    for round_num in range(1, max_rounds + 1):
        # Layer 1: Structural QA (zero cost)
        sq = structural_qa(guide_text)
        if sq["blocks"]:
            guide_text = _auto_fix_structural(guide_text, sq["blocks"], ...)

        # Layer 1b: Brief adherence (Haiku)
        ba = section_brief_check(guide_text, ...)
        if any(s["score"] < 6 for s in ba):
            guide_text = _regenerate_weak_sections(guide_text, ba, ...)

        # Layer 2: Language & Tone (Haiku)
        lang = language_tone_check(guide_text, ...)
        guide_text = _apply_patches(guide_text, lang["patches"])

        # Layer 3: Consistency (Haiku)
        cons = consistency_check(guide_text, ...)
        guide_text = _apply_patches(guide_text, cons["patches"])

        # Layer 4: Medical review (Sonnet)
        med = validate_medical(guide_text, ...)
        if med["accuracy_issues"]:
            guide_text = _apply_medical_corrections(guide_text, med, ...)

        # Layer 5: Advocate review (Sonnet)
        adv = validate_advocate(guide_text, ...)

        if all_pass(sq, ba, lang, cons, med, adv):
            break

    return combined_result
```

- [ ] **Step 2: Run all validation tests**

- [ ] **Step 3: Commit**

### Task 5.7: Verify M5

- [ ] **Verification: Run validation on existing v5 guide**

```bash
# Read existing guide and run validation layers
python3 -c "
from modules.validation import refine_guide
guide = open('data/guides/lung-ret-fusion.md').read()
# ... run with mock knowledge_map
"
```

Expected: Report scores per section, identify issues from each layer. Cost: ~$0.74.

- [ ] **Commit milestone marker**

---

## Milestone 6: RET Fusion Guide Generation (Data-First)

**Goal:** Generate RET Fusion v6 guide using existing 3454 seeded findings. No discovery, no search -- data already exists. Two phases: dry-run verification, then actual generation.

**Files:**
- Modify: `run_research.py` (add --generate-from-data mode, checkpoint/resume, dashboard, health check)
- Test: Manual end-to-end

### Task 6.1: Add pipeline checkpoint/resume

- [ ] **Step 1: Save pipeline_state after each phase**

In `cmd_topic()`, after each phase completes, call `db.save_pipeline_state(...)`.

- [ ] **Step 2: Add resume logic**

At the start of `cmd_topic()`, check `db.get_last_completed_phase(topic_id)`. If found, skip to next phase. Print: `"Resuming from Phase {N+1} (last completed: Phase {N})"`

- [ ] **Step 3: Add --force-phase flag**

`--force-phase N` ignores checkpoint for phase N.

- [ ] **Step 4: Commit**

### Task 6.2: Add pipeline dashboard

- [ ] **Step 1: Implement _print_dashboard() function**

Print formatted summary at end of run per SPEC format: phase-by-phase timing, cost, findings, guide size, alerts.

- [ ] **Step 2: Call from cmd_topic() end**

- [ ] **Step 3: Commit**

### Task 6.3: Add health check

- [ ] **Step 1: Implement _health_check() function**

Verify: API keys present, DB accessible, topic exists, disk space > 100MB, checkpoint status.

- [ ] **Step 2: Call at start of cmd_topic()**

- [ ] **Step 3: Commit**

### Task 6.4: Add --generate-from-data mode

- [ ] **Step 1: Implement cmd_generate_from_data()**

For topics with enough seeded findings (>= 200), skip phases 0-3 (pre-search, discovery, query gen, search) and go directly to:
1. Gap analysis on existing findings (Phase 4)
2. Optional: small targeted search to fill critical gaps only
3. Cross-verification (Phase 5) -- skip if no discovery knowledge_map
4. Guide generation (Phase 6) -- 16 sections from existing findings
5. Validation (Phase 7) -- all 6 layers
6. Review checklist (Phase 8)

```python
parser.add_argument("--generate-from-data", action="store_true",
    help="Generate guide from existing DB findings (skip discovery/search)")
```

- [ ] **Step 2: Commit**

### Task 6.5: Dry-run verification

- [ ] **Step 1: Run dry-run to verify everything works**

```bash
python3 run_research.py --topic "lung-ret-fusion" --generate-from-data --dry-run
```

Expected output:
- Confirms 3454 findings available in DB
- Shows lifecycle_stage distribution (Q1: N, Q2: N, ... Q9: N)
- Identifies gaps per lifecycle stage (if any)
- Lists which sections would use Sonnet vs Haiku
- Shows estimated cost
- Does NOT call any API

- [ ] **Step 2: Review dry-run output**

Verify: No errors, all lifecycle stages have findings, gap analysis makes sense.

- [ ] **Step 3: Commit**

### Task 6.6: Generate RET Fusion v6 guide

- [ ] **Step 1: Execute guide generation from existing data**

```bash
python3 run_research.py --topic "lung-ret-fusion" --generate-from-data
```

Pipeline:
1. Load 3454 findings from DB (already reclassified with lifecycle_stage)
2. Gap analysis identifies weak lifecycle stages
3. Generate 16-section guide + INAINTE DE TOATE executive summary
4. Run 6-layer validation
5. Auto-correct issues (language, medical, structural)
6. Generate review checklist

- [ ] **Step 2: Verify metrics (SPEC section 8)**

- [ ] Advocate score >= 8.5 on ALL 16 sections
- [ ] 0 safety concerns
- [ ] Min 200 relevant findings used
- [ ] Cost < $5
- [ ] All 16 sections present and non-trivial
- [ ] Executive summary ("BEFORE ANYTHING ELSE") answers 4 immediate questions
- [ ] No hidden data contradictions

- [ ] **Step 3: Compare v6 guide with v5 guide**

Diff `data/guides/lung-ret-fusion.md` (v6) vs backup. Document: what's new, what's better, what's missing.

- [ ] **Step 4: Commit milestone marker**

**Note:** The full pipeline (with discovery + search) will be used for NEW topics that have no seed data. For RET Fusion, we already have the data -- the value is in the improved guide structure and validation.

---

## Milestone 7: Monitoring Mode

**Goal:** Implement incremental monitoring (M0-M6): detect changes, generate alerts, patch guide.

**Files:**
- Create: `modules/monitor.py`
- Create: `modules/monitor_queries.py`
- Create: `modules/change_detector.py`
- Create: `modules/living_guide.py`
- Modify: `run_research.py`
- Test: `tests/test_monitor.py`

### Task 7.1: Create monitor_queries.py

- [ ] **Step 1: Implement generate_monitor_queries()**

Generate 30-50 queries from: diagnosis + named entities extracted from existing guide.

- [ ] **Step 2: Write tests**

- [ ] **Step 3: Commit**

### Task 7.2: Create change_detector.py

- [ ] **Step 1: Implement classify_change()**

Apply 8 classification rules from SPEC 10.9. Returns: category (safety/approval/trial/resistance/guideline/info), severity (critical/major/minor).

- [ ] **Step 2: Write tests with example findings**

- [ ] **Step 3: Commit**

### Task 7.3: Create living_guide.py

- [ ] **Step 1: Implement extract_entities()**

Haiku extracts drugs, mutations, trials, metastasis_sites from generated guide. Saves to tracked_entities table.

- [ ] **Step 2: Implement patch_guide()**

For each alert, identify target section, find end of section, insert dated update with finding reference.

- [ ] **Step 3: Write tests**

- [ ] **Step 4: Commit**

### Task 7.4: Create monitor.py orchestrator

- [ ] **Step 1: Implement run_monitor()**

Orchestrate M0-M6: query generation -> search -> enrichment -> change detection -> technology tracking -> report -> guide patching.

- [ ] **Step 2: Write integration test with mock**

- [ ] **Step 3: Commit**

### Task 7.5: Add --monitor CLI

- [ ] **Step 1: Add --monitor and --monitor-all flags**

- [ ] **Step 2: Add --list-alerts and --ack-alert flags**

- [ ] **Step 3: Commit**

### Task 7.6: Verify M7

- [ ] **Verification:**

```bash
python3 run_research.py --monitor --topic "lung-ret-fusion" --since 7d
```

Expected: Monitoring report generated, at least 1 new finding detected, guide patching works. Cost: ~$0.30.

- [ ] **Commit milestone marker**

---

## Milestone 8: Skills + Auto-Learning

**Goal:** Update skill files for v6, implement differentiated learnings, context bootstrap.

**Files:**
- Modify: `.claude/skills/oncologist.md`
- Modify: `.claude/skills/patient-advocate.md`
- Rewrite: `.claude/skills/research.md`
- Delete: `.claude/skills/monthly-review.md`
- Modify: `.claude/skills/new-topic.md`
- Modify: `.claude/skills/ux.md`
- Modify: `modules/skill_improver.py`

### Task 8.1: Update oncologist.md for Q1-Q8

- [ ] **Step 1: Restructure Actions section per Q1-Q8**

- [ ] **Step 2: Add [TOPIC] and [GENERAL] prefix convention to Learnings**

- [ ] **Step 3: Preserve all 22 existing learnings (re-prefix them)**

- [ ] **Step 4: Commit**

### Task 8.2: Update patient-advocate.md for 16 sections

- [ ] **Step 1: Update Patient Journey Completeness for 16 sections**

- [ ] **Step 2: Add section briefs reference**

- [ ] **Step 3: Add [EXPERIENTA] prefix convention**

- [ ] **Step 4: Commit**

### Task 8.3: Rewrite research.md for v6

- [ ] **Step 1: Document full v6 pipeline (phases 0-8 + monitoring)**

- [ ] **Step 2: Add CLI quick reference with all flags**

- [ ] **Step 3: Add troubleshooting section**

- [ ] **Step 4: Commit**

### Task 8.4: Delete monthly-review.md, update other skills

- [ ] **Step 1: Delete monthly-review.md**

- [ ] **Step 2: Extend new-topic.md with lifecycle preview**

- [ ] **Step 3: Extend ux.md with guide UX evaluation**

- [ ] **Step 4: Update CLAUDE.md skills section and dependency map**

- [ ] **Step 5: Commit**

### Task 8.5: Implement differentiated learning extraction

- [ ] **Step 1: Update skill_improver.py to separate [MEDICAL] vs [EXPERIENTA] learnings**

- [ ] **Step 2: Implement context bootstrap in run_research.py**

At pipeline start, generate 500-word context brief with: diagnosis, finding count, last run info, top 5 learnings, unacked alerts.

- [ ] **Step 3: Commit**

### Task 8.6: Verify M8

- [ ] **Verification: After a run, check skills files for new prefixed learnings**

- [ ] **Commit milestone marker**

---

## Milestone 9: Observability + Polish

**Goal:** Progress reporting, mock mode, rollback, final test suite.

**Files:**
- Modify: `run_research.py`
- Test: `tests/test_integration.py`

### Task 9.1: Progress reporting

- [ ] **Step 1: Add in-place progress bars for long operations**

Format: `[Module] progress | metric | cost | elapsed`

- [ ] **Step 2: Commit**

### Task 9.2: Implement --mock and --save-fixtures

- [ ] **Step 1: Implement fixture save after successful run**

After each API call, optionally save request/response to `tests/fixtures/{topic_id}/`.

- [ ] **Step 2: Implement mock mode that loads fixtures**

- [ ] **Step 3: Commit**

### Task 9.3: Implement --rollback

- [ ] **Step 1: Implement guide rollback from backup**

`--rollback --topic X` copies latest backup to current guide path.

- [ ] **Step 2: Commit**

### Task 9.4: Run full test suite + add integration test

- [ ] **Step 1: Add end-to-end mock integration test**

Test that runs full pipeline in mock mode, verifies all phases complete.

- [ ] **Step 2: Run ALL tests**

```bash
python3 -m pytest tests/ -v
```

Expected: All existing (121) + new tests pass.

- [ ] **Step 3: Final consistency check**

Verify all CLI flags work:
- `--topic`, `--dry-run`, `--seed`, `--reclassify`, `--monitor`, `--monitor-all`
- `--force-phase`, `--rollback`, `--mock`, `--save-fixtures`
- `--list-topics`, `--list-alerts`, `--ack-alert`
- `--init`

- [ ] **Step 4: Commit milestone marker**

---

## Post-Implementation

### 1. Final Report

- [ ] Document: what was implemented, what works, what doesn't, what remains

### 2. Compare RET Fusion v6 vs v5

- [ ] Concrete differences between guides

### 3. Update decisions/log.yaml

- [ ] Record all implementation decisions

### 4. Update CLAUDE.md

- [ ] Update Data Flow section for v6
- [ ] Update CLI Commands
- [ ] Update Dependency Map
- [ ] Update Structure section

---

## Dependencies Between Milestones

```
M1 (DB + Seed)
  |
  v
M2 (Discovery Q1-Q8)  -----> M3 (Query Gen + Enrichment)
  |                             |
  v                             v
M4 (Guide Generation 16 sections)
  |
  v
M5 (Validation 6 layers)
  |
  v
M6 (End-to-End Test) -----> M8 (Skills + Learning)
  |
  v
M7 (Monitoring)
  |
  v
M9 (Polish)
```

**Critical path:** M1 -> M2 -> M3 -> M4 -> M5 -> M6
**Can run after M6:** M7, M8 (parallel)
**Must be last:** M9

## Estimated Costs

| Milestone | API Cost | Notes |
|-----------|----------|-------|
| M1 | ~$0.30 | Reclassify 3500 findings with Haiku |
| M2 | ~$0.50 | Discovery dry-run verification |
| M3 | $0.00 | Dry-run only |
| M4 | ~$1.00 | Guide generation (Haiku + Sonnet critical) |
| M5 | ~$0.74 | 2 validation rounds |
| M6 | ~$2.00 | Data-first: gap analysis + guide gen + validation (no discovery/search) |
| M7 | ~$0.30 | Monitoring test run |
| M8 | $0.00 | Skill file updates only |
| M9 | $0.00 | Mock mode, no API |
| **Total** | **~$4.84** | Across all milestones |

**Note:** M6 is cheaper than a full pipeline run because it skips discovery ($0.50) and search ($0) -- data already exists. Full pipeline runs (with discovery + search) are for NEW topics only.

---

## SPEC Coverage Notes

### Covered per-task but not called out explicitly

These SPEC requirements are handled INSIDE existing tasks (implementing agent: check SPEC for details):

| SPEC | Where handled | Detail |
|------|--------------|--------|
| 10.5 Section 3 special case | M5 Task 5.6 | If oncologist finds factual error in Section 3 (Greseli), REGENERATE fully with Sonnet (not patch). If still wrong, guide fails entirely. |
| 10.6 Multiple drugs | M2 Task 2.2 | When discovery produces >4 first-line drugs, oncologist prompt must ask for explicit prioritization. Guide sections 4-8 deep-dive top 2-4 only. |
| 10.7 Multilingual exclusions | M3 Task 3.1 | Only Q2/Q3/Q5 get translated (max 2/stage/language). Q1/Q7/Q8 do NOT get translated. ~48 multilingual queries added. |
| 10.12 Model IDs from config | All tasks | Never hardcode model IDs. Use `cfg.get("discovery_model", "claude-sonnet-4-6")` pattern (already in v5). |
| 10.13 Haiku parallelism | M4 Task 4.3 | Max 4 Haiku sections generated in parallel. Sonnet sections sequential. |
| 10.15 Section 15 model | M4 Task 4.1 | Section 15 (Ce sa intrebi medicul) uses Haiku -- NOT in CRITICAL_SECTIONS. |
| 10.16 Monitoring report | M7 Task 7.4 | Output to `data/monitors/{topic_id}-{date}.md` using template from SPEC 10.16. Create `data/monitors/` directory. |
| 10.17 --monitor-all ordering | M7 Task 7.5 | Process topics by `priority` field from registry.yaml. Only guide_ready/published topics. |
| 10.18 Flexible Section 3 minimum | M5 Task 5.2 | Layer 1b default "min 8 greseli" adjusts to max(4, count from Q7 discovery). Absolute minimum: 4. |
| 10.19 Q7 thresholds | M3 Task 3.5 | Q7 minimum queries: 5. Q7 minimum findings (relevance >= 7): 5. |
| 10.20 Section gen order | M4 Task 4.2 | Sections 1-16 in order, INAINTE DE TOATE generated LAST. |
| 6b Contradiction range rule | M4 Task 4.3 | When sources disagree on numbers: present range with both sources, e.g., "ORR 83-85% (Source A: 85%, Source B: 83%)". Never pick one. |

### Deferred to post-v6 (acknowledged, not in scope)

These SPEC features are intentionally deferred to avoid scope creep:

| Feature | SPEC section | Why deferred |
|---------|-------------|--------------|
| Pruning learnings after 5 runs | 5b | No topic has 5 runs yet |
| Cross-topic learning sharing | 5b | Only 1 topic researched |
| Human correction diff extraction | 5b | Requires manual guide editing first |
| Feedback loop (Haiku post-run analysis) | 5b | Nice-to-have, not blocking |
| Link rot detection (10% URL check) | 5 Data hygiene | Monitoring mode covers freshness |
| Retracted paper detection | 5 Data hygiene | PubMed re-search catches this |
| Guide size cap (>250KB auto-regen) | 5 Data hygiene | No guide has exceeded 200KB |
| Publication pipeline (6c) | 6c | Existing manual workflow works |

### SPEC inconsistency noted

SPEC uses both `tracked_technologies` (prose, section 7 and 10.8) and `tracked_entities` (DDL, section 10.10). This plan uses `tracked_entities` (matching the DDL). SPEC should be corrected.
