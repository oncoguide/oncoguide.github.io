#!/usr/bin/env python3
"""OncoGuide Research Agent -- CLI entry point.

Usage:
    python run_research.py --init
    python run_research.py --topic "topic-id"
    python run_research.py --topic "topic-id" --dry-run
    python run_research.py --update-all --since 30d
    python run_research.py --list-topics
"""

import argparse
import json
import logging
import os
import re
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timedelta

import yaml

# Add parent to path for module imports
sys.path.insert(0, os.path.dirname(__file__))

from modules.cost_tracker import CostTracker
from modules.database import Database
from modules.discovery import run_discovery
from modules.enrichment import enrich_batch, get_token_usage, reset_token_usage
from modules.pre_search import pre_search
from modules.cross_verify import cross_verify, format_report
from modules.gap_analyzer import analyze_gaps
from modules.guide_generator import generate_guide, GUIDE_SECTIONS
from modules.keyword_extractor import extract_queries
from modules.searcher_serper import search_serper
from modules.searcher_pubmed import search_pubmed
from modules.searcher_clinicaltrials import search_clinicaltrials
from modules.searcher_openfda import search_openfda
from modules.searcher_civic import search_civic
from modules.skill_improver import append_learnings
from modules.utils import compute_content_hash, extract_domain, now_iso, setup_logging
from modules.validation import validate_guide, refine_guide

logger = logging.getLogger(__name__)

# Searcher dispatch map
SEARCHERS = {
    "serper": lambda q, cfg, **kw: search_serper(
        q["query_text"], cfg["serper_api_key"], q.get("language", "en"),
        kw.get("date_from"), kw.get("date_to"), cfg.get("max_results_per_query", 10)),
    "pubmed": lambda q, cfg, **kw: search_pubmed(
        q["query_text"], cfg["pubmed_email"],
        kw.get("date_from"), kw.get("date_to"), cfg.get("max_results_per_query", 10)),
    "clinicaltrials": lambda q, cfg, **kw: search_clinicaltrials(
        q["query_text"], cfg.get("max_results_per_query", 10), kw.get("date_from")),
    "openfda": lambda q, cfg, **kw: search_openfda(
        q["query_text"], cfg.get("openfda_api_key", ""),
        kw.get("date_from"), kw.get("date_to"), cfg.get("max_results_per_query", 10)),
    "civic": lambda q, cfg, **kw: search_civic(
        q["query_text"], cfg.get("max_results_per_query", 10)),
}


def load_config(path: str = "config.json") -> dict:
    """Load config from file, then override with env variables.
    Config file is optional -- env variables are sufficient."""
    cfg = {}
    if os.path.exists(path):
        with open(path) as f:
            cfg = json.load(f)

    # Env variables override config file values
    env_map = {
        "ANTHROPIC_API_KEY": "anthropic_api_key",
        "SERPER_API_KEY": "serper_api_key",
        "PUBMED_EMAIL": "pubmed_email",
        "OPENFDA_API_KEY": "openfda_api_key",
    }
    for env_var, cfg_key in env_map.items():
        val = os.environ.get(env_var)
        if val:
            cfg[cfg_key] = val

    # Defaults for non-secret settings
    defaults = {
        "enrichment_model": "claude-haiku-4-5-20251001",
        "guide_model": "claude-haiku-4-5-20251001",
        "query_expansion_model": "claude-haiku-4-5-20251001",
        "discovery_model": "claude-sonnet-4-6",
        "validation_model": "claude-sonnet-4-6",
        "max_discovery_rounds": 5,
        "max_validation_rounds": 2,
        "max_cost_usd": 5.0,
        "database_path": "data/research.db",
        "guides_dir": "data/guides",
        "backup_dir": "data/backups",
        "max_backups": 10,
        "max_results_per_query": 10,
        "delay_between_searches": 3,
        "delay_between_enrichments": 0.3,
        "log_file": "logs/research.log",
        "log_level": "INFO",
    }
    for key, default in defaults.items():
        cfg.setdefault(key, default)

    # Validate required keys
    missing = []
    if not cfg.get("anthropic_api_key"):
        missing.append("ANTHROPIC_API_KEY")
    if not cfg.get("serper_api_key"):
        missing.append("SERPER_API_KEY")
    if not cfg.get("pubmed_email"):
        missing.append("PUBMED_EMAIL")
    if missing:
        print(f"ERROR: Missing required config. Set env variables: {', '.join(missing)}")
        print("  export ANTHROPIC_API_KEY='sk-ant-...'")
        print("  export SERPER_API_KEY='...'")
        print("  export PUBMED_EMAIL='your@email.com'")  # nosec
        sys.exit(1)

    return cfg


def load_registry(path: str = "../../topics/registry.yaml") -> list[dict]:
    if not os.path.exists(path):
        print(f"ERROR: {path} not found.")
        sys.exit(1)
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("topics", [])


def save_registry(topics: list[dict], path: str = "../../topics/registry.yaml"):
    with open(path, "w") as f:
        f.write("# OncoGuide Topic Registry\n")
        f.write("# Status: planned -> researching -> guide_ready (human review) -> drafting -> review -> published\n\n")
        yaml.dump({"topics": topics}, f, default_flow_style=False, allow_unicode=True,
                   sort_keys=False)


def find_topic(topics: list[dict], topic_id: str) -> dict | None:
    for t in topics:
        if t["id"] == topic_id:
            return t
    return None


def parse_since(since_str: str) -> str:
    """Parse '30d' into ISO date string."""
    match = re.match(r"(\d+)d", since_str)
    if not match:
        print(f"ERROR: Invalid --since format: {since_str}. Use Nd (e.g., 30d)")
        sys.exit(1)
    days = int(match.group(1))
    dt = datetime.now() - timedelta(days=days)
    return dt.strftime("%Y-%m-%d")


def cmd_init(cfg: dict):
    """Initialize database."""
    db = Database(cfg["database_path"])
    db.create_tables()
    db.close()
    print(f"Database initialized at {cfg['database_path']}")


def cmd_list_topics(registry_path: str):
    """List all topics."""
    topics = load_registry(registry_path)
    if not topics:
        print("No topics in registry.")
        return
    print(f"\n{'ID':<35} {'Status':<15} {'Last Researched'}")
    print("-" * 70)
    for t in topics:
        print(f"{t['id']:<35} {t['status']:<15} {t.get('last_researched', 'never')}")


def _search_and_enrich(queries, topic_id, topic_title, cfg, db, run_id,
                       date_from=None, date_to=None, label="", cost=None):
    """Execute search + enrichment for a batch of queries. Returns stats dict."""
    stats = {"queries_total": 0, "raw_results": 0, "after_dedup": 0,
             "after_enrichment": 0, "discarded": 0}
    all_results = []
    delay = cfg.get("delay_between_searches", 3)

    for i, q in enumerate(queries):
        engine = q.get("search_engine", "serper")
        searcher = SEARCHERS.get(engine)
        if not searcher:
            logger.warning(f"Unknown search engine: {engine}, skipping")
            continue

        try:
            results = searcher(q, cfg, date_from=date_from, date_to=date_to)
            stats["queries_total"] += 1
            stats["raw_results"] += len(results)

            # Dedup: check both content_hash and URL before enrichment
            new = 0
            for r in results:
                ch = compute_content_hash(topic_id, r.get("title", ""), r.get("url", ""))
                if not db.has_finding(topic_id, content_hash=ch, url=r.get("url", "")):
                    r["_content_hash"] = ch
                    all_results.append(r)
                    new += 1

            db.log_search(run_id, q["query_text"], engine, q.get("language", "en"),
                         len(results), new, "success")
            print(f"  [{engine}] '{q['query_text'][:50]}' -> {len(results)} results, {new} new")

        except Exception as e:
            logger.error(f"Search failed: {engine} '{q['query_text']}': {e}")
            print(f"  [ERROR] Search failed [{engine}] '{q['query_text'][:50]}': {e}")
            db.log_search(run_id, q["query_text"], engine, q.get("language", "en"),
                         0, 0, "error", str(e))

        if delay > 0 and i < len(queries) - 1:
            time.sleep(delay)

    stats["after_dedup"] = len(all_results)
    print(f"\n  {label}Total: {stats['raw_results']} raw -> {stats['after_dedup']} after dedup")

    # Enrich
    if all_results:
        print(f"\n  Enriching {len(all_results)} findings...")
        enrichments = enrich_batch(
            all_results, topic_title, cfg["anthropic_api_key"],
            cfg.get("enrichment_model", "claude-haiku-4-5-20251001"),
            cfg.get("delay_between_enrichments", 0.3),
            progress_callback=lambda cur, tot: print(f"  {cur}/{tot}", end="\r"),
            cost=cost,
        )
        print()

        # Store relevant findings
        for finding, enrichment in zip(all_results, enrichments):
            if enrichment.get("relevant"):
                db.insert_finding({
                    "content_hash": finding["_content_hash"],
                    "topic_id": topic_id,
                    "title_original": finding.get("title", ""),
                    "snippet_original": finding.get("snippet", ""),
                    "source_language": finding.get("language", "en"),
                    "title_english": enrichment.get("title_english", ""),
                    "summary_english": enrichment.get("summary_english", ""),
                    "relevance_score": enrichment.get("relevance_score", 0),
                    "authority_score": enrichment.get("authority_score", 0),
                    "source_url": finding.get("url", ""),
                    "source_domain": extract_domain(finding.get("url", "")),
                    "source_platform": finding.get("source", "unknown"),
                    "date_published": finding.get("date"),
                    "date_found": now_iso(),
                    "run_id": run_id,
                    "lifecycle_stage": enrichment.get("lifecycle_stage"),
                })
                stats["after_enrichment"] += 1
            else:
                stats["discarded"] += 1

        print(f"  Relevant: {stats['after_enrichment']}, Discarded: {stats['discarded']}")

    return stats


def _generate_review_checklist(
    review_path: str,
    topic_id: str,
    diagnosis: str,
    val_result: dict,
    cv_report_text: str,
    findings_count: int = 0,
    cost_report: str = "",
):
    """Generate human review checklist markdown after pipeline completes."""
    os.makedirs(os.path.dirname(review_path) or ".", exist_ok=True)

    lines = [
        f"# Human Review Checklist -- {diagnosis}",
        f"",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Topic:** {topic_id}",
        f"**Findings analyzed:** {findings_count}",
        f"**Validation score:** {val_result.get('overall_score', '?')}/10",
        f"**Validation passed:** {val_result.get('passed', False)}",
        f"",
        f"---",
        f"",
        f"## 1. Safety Concerns",
        f"",
    ]

    safety = val_result.get("safety_concerns", [])
    if safety:
        for concern in safety:
            lines.append(f"- [ ] **SAFETY:** {concern}")
    else:
        lines.append("No safety concerns flagged by validation.")
    lines.append("")

    lines.append("## 2. Accuracy Issues")
    lines.append("")
    accuracy = val_result.get("accuracy_issues", [])
    if accuracy:
        for issue in accuracy:
            lines.append(f"- [ ] {issue}")
    else:
        lines.append("No accuracy issues flagged by validation.")
    lines.append("")

    lines.append("## 3. Cross-Verification Discrepancies")
    lines.append("")
    if cv_report_text:
        # Extract CONTRADICTED lines
        contradictions = [
            line for line in cv_report_text.split("\n")
            if "CONTRADICTED" in line
        ]
        if contradictions:
            lines.append("The following discovery claims were contradicted by real findings:")
            lines.append("")
            for c in contradictions:
                lines.append(f"- [ ] {c.strip()}")
        else:
            lines.append("No contradictions found -- all verified claims match real findings.")
        # Also show unverified
        unverified = [
            line for line in cv_report_text.split("\n")
            if "UNVERIFIED" in line
        ]
        if unverified:
            lines.append("")
            lines.append("Unverified claims (no supporting finding found):")
            lines.append("")
            for u in unverified:
                lines.append(f"- [ ] {u.strip()}")
    else:
        lines.append("Cross-verification was not run or produced no report.")
    lines.append("")

    lines.append("## 4. Section Scores")
    lines.append("")
    section_scores = val_result.get("section_scores", {})
    if section_scores:
        lines.append("| Section | Score | Notes |")
        lines.append("|---------|-------|-------|")
        for sec_id, info in section_scores.items():
            if isinstance(info, dict):
                score = info.get("score", "?")
                notes = info.get("notes", "")
            else:
                score = info
                notes = ""
            lines.append(f"| {sec_id} | {score}/10 | {notes} |")
    else:
        lines.append("No per-section scores available.")
    lines.append("")

    lines.append("## 5. Human Review Questions")
    lines.append("")
    lines.append("- [ ] Are there recently approved drugs for this diagnosis that are missing from the guide?")
    lines.append("- [ ] Do the side effects listed match what patients actually experience (including grade 1-2 daily effects)?")
    lines.append("- [ ] Are the emergency signs complete -- would a patient know when to go to the ER?")
    lines.append("- [ ] Is the European access information current (EMA approvals, reimbursement)?")
    lines.append("- [ ] Would a newly diagnosed patient find this guide helpful and not overwhelming?")
    lines.append("")

    lines.append("## 6. Pipeline Summary")
    lines.append("")
    if cost_report:
        lines.append(f"**Cost:** {cost_report}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("**Next step:** If all items above are checked/resolved, change topic status to `drafting` in `topics/registry.yaml`.")

    with open(review_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    logger.info(f"Review checklist generated: {review_path}")


def _abort(phase: str, reason: str) -> None:
    """Print clear error and exit pipeline."""
    print(f"\n  [ABORT] Phase '{phase}' failed: {reason}")
    print(f"  Fix the issue and re-run. No money wasted on downstream phases.")
    raise RuntimeError(f"Pipeline aborted at phase '{phase}': {reason}")


# ── v6: Pipeline gates ──────────────────────────────────────────────

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
    issues = []
    if not drugs:
        issues.append("No approved drugs in Q2")
    if not resistance:
        issues.append("No resistance mechanisms in Q5")
    if not pipeline:
        issues.append("No pipeline drugs in Q6")
    if issues:
        return False, "; ".join(issues)
    return True, ""


def _gate_2(queries: list, lifecycle_mins: dict = None) -> tuple[bool, str]:
    """GATE 2: Total >= 80 queries, per-stage minimums."""
    if len(queries) < 80:
        return False, f"Only {len(queries)} queries (min 80)"
    if lifecycle_mins:
        stage_counts = {}
        for q in queries:
            ls = q.get("lifecycle_stage", "?")
            stage_counts[ls] = stage_counts.get(ls, 0) + 1
        below = [f"{s}:{stage_counts.get(s,0)}/{m}" for s, m in lifecycle_mins.items()
                 if stage_counts.get(s, 0) < m]
        if below:
            return False, f"Stages below minimum: {', '.join(below)}"
    return True, ""


def _gate_3(findings_count: int) -> tuple[bool, str]:
    """GATE 3: Min 100 findings. < 20 = hard stop, < 100 = warning (passes)."""
    if findings_count < 20:
        return False, f"Only {findings_count} findings -- too few, pipeline cannot continue"
    if findings_count < 100:
        # Pass with warning per SPEC: "< 100 se logheaza warning"
        return True, f"Only {findings_count} findings (min 100 recommended)"
    return True, ""


def _gate_6(guide_path: str) -> tuple[bool, str]:
    """GATE 6: Guide >= 10KB, 16 sections present."""
    import os
    if not os.path.exists(guide_path):
        return False, "Guide file not generated"
    size = os.path.getsize(guide_path)
    if size < 10240:
        return False, f"Guide too small: {size} bytes (min 10KB)"
    with open(guide_path) as f:
        content = f.read()
    section_count = content.count("\n## ")
    if section_count < 16:
        return False, f"Only {section_count} sections found (need 16)"
    if "BEFORE ANYTHING ELSE" not in content and "INAINTE DE TOATE" not in content:
        return False, "Executive summary (BEFORE ANYTHING ELSE) not found"
    return True, ""


def cmd_topic(cfg: dict, topic_id: str, registry_path: str, dry_run: bool = False,
              date_from: str = None, date_to: str = None, update_status: bool = True):
    """Research a specific topic -- full v4 pipeline."""
    topics = load_registry(registry_path)
    topic = find_topic(topics, topic_id)
    if not topic:
        print(f"ERROR: Topic '{topic_id}' not found in registry.")
        sys.exit(1)

    start_time = time.time()
    cost = CostTracker(max_cost_usd=cfg.get("max_cost_usd", 5.0))

    diagnosis = topic["title"]
    reset_token_usage()  # Reset enrichment module's internal token counter
    print(f"\n=== Researching: {diagnosis} ===\n")

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

    # Phase 1: Discovery loop (Sonnet)
    discovery_model = cfg.get("discovery_model", "claude-sonnet-4-6")
    print(f"Phase 1: Discovery loop (max {cfg.get('max_discovery_rounds', 5)} rounds)...")
    t0 = time.time()
    discovery = run_discovery(
        diagnosis=diagnosis,
        model=discovery_model,
        cost=cost,
        api_key=cfg["anthropic_api_key"],
        max_rounds=cfg.get("max_discovery_rounds", 5),
        pre_search_context=pre_context,
    )
    print(f"  Discovery: {discovery['rounds']} rounds, converged={discovery['converged']} ({time.time()-t0:.0f}s)")
    km = discovery.get("knowledge_map", {})
    if not km or len(km) < 3:
        _abort("discovery", f"knowledge_map empty or too small: {list(km.keys())}")
    # GATE 1: minimum entities
    g1_ok, g1_reason = _gate_1(km)
    if not g1_ok:
        logger.warning(f"GATE 1: {g1_reason} -- continuing but guide may be incomplete")
        print(f"  [GATE 1 WARNING] {g1_reason}")
    if discovery.get("lifecycle_scores"):
        low = [f"{k}: {v.get('score', '?')}" for k, v in discovery["lifecycle_scores"].items()
               if isinstance(v, dict) and v.get("score", 10) < 8.5]
        if low:
            print(f"  Low lifecycle scores: {', '.join(low)}")

    # Phase 2: Keyword extraction (Sonnet)
    print("Phase 2: Extracting search queries from discovery...")
    t0 = time.time()
    queries = extract_queries(
        diagnosis=diagnosis,
        conversation=discovery["conversation"],
        knowledge_map=discovery["knowledge_map"],
        api_key=cfg["anthropic_api_key"],
        model=discovery_model,
        cost=cost,
    )
    print(f"  Extracted {len(queries)} precision queries ({time.time()-t0:.0f}s)")
    if len(queries) < 10:
        _abort("keyword_extraction", f"only {len(queries)} queries extracted, expected >= 10")
    # GATE 2: query count + per-stage minimums
    from modules.keyword_extractor import LIFECYCLE_MINIMUMS
    g2_ok, g2_reason = _gate_2(queries, LIFECYCLE_MINIMUMS)
    if not g2_ok:
        logger.warning(f"GATE 2: {g2_reason}")
        print(f"  [GATE 2 WARNING] {g2_reason}")

    if dry_run:
        print("\n--- DRY RUN ---")
        for q in queries:
            sec = q.get("target_section", "general")
            print(f"  [{q['search_engine']}] [{q.get('language', 'en')}] ({sec}) {q['query_text']}")
        print(f"\nDiscovery rounds: {discovery['rounds']}")
        print(f"Cost so far:\n  {cost.report()}")
        return

    # Phase 3: Initialize DB, search round 1
    db = Database(cfg["database_path"])
    db.create_tables()
    db.backup(cfg.get("backup_dir", "data/backups"), cfg.get("max_backups", 10))
    run_id = db.start_run("topic", topic_id)

    if update_status:
        topic["status"] = "researching"
        save_registry(topics, registry_path)

    print("Phase 3: Search round 1...")
    t0 = time.time()
    stats_r1 = _search_and_enrich(
        queries, topic_id, diagnosis, cfg, db, run_id,
        date_from=date_from, date_to=date_to, label="Round 1 -- ", cost=cost,
    )
    print(f"  Round 1 done ({time.time()-t0:.0f}s)")
    total_findings = db.count_findings(topic_id)
    # GATE 3: minimum findings
    g3_ok, g3_reason = _gate_3(total_findings)
    if not g3_ok:
        _abort("search_round_1", f"{g3_reason}. Check API keys and search backends.")
    elif g3_reason:
        logger.warning(f"GATE 3: {g3_reason}")
        print(f"  [GATE 3 WARNING] {g3_reason}")

    # Phase 4: Gap analysis + search round 2
    findings_so_far = db.get_findings_by_topic(topic_id, limit=500)
    stats_r2 = {"queries_total": 0, "raw_results": 0, "after_dedup": 0,
                "after_enrichment": 0, "discarded": 0}
    if findings_so_far and len(findings_so_far) >= 10:
        print(f"\nPhase 4: Gap analysis ({len(findings_so_far)} findings)...")
        gap_queries = analyze_gaps(
            diagnosis, findings_so_far, GUIDE_SECTIONS,
            cfg["anthropic_api_key"],
            cfg.get("query_expansion_model", "claude-haiku-4-5-20251001"),
            cost=cost,
        )
        if gap_queries:
            print(f"  {len(gap_queries)} gap-filling queries for round 2")
            stats_r2 = _search_and_enrich(
                gap_queries, topic_id, diagnosis, cfg, db, run_id,
                date_from=date_from, date_to=date_to, label="Round 2 -- ", cost=cost,
            )

    # Phase 5: Cross-verification (Haiku)
    findings = db.get_findings_by_topic(topic_id, limit=500)
    cv_report_text = ""
    if findings and discovery.get("knowledge_map"):
        print(f"\nPhase 5: Cross-verification ({len(findings)} findings vs discovery claims)...")
        try:
            cv_report = cross_verify(
                knowledge_map=discovery["knowledge_map"],
                findings=findings,
                diagnosis=diagnosis,
                api_key=cfg["anthropic_api_key"],
                cost=cost,
            )
            cv_report_text = format_report(cv_report)
            v = len(cv_report.get("verified", []))
            c = len(cv_report.get("contradicted", []))
            u = len(cv_report.get("unverified", []))
            print(f"  {v} verified, {c} contradicted, {u} unverified")
        except Exception as e:
            logger.error(f"Cross-verification failed: {e}")
            print(f"  Cross-verification failed ({e}), continuing without")

    # Phase 6: Guide generation (Haiku + Sonnet for critical sections)
    guides_dir = cfg.get("guides_dir", "data/guides")
    output_path = os.path.join(guides_dir, f"{topic_id}.md")
    critical_model = cfg.get("critical_guide_model", cfg.get("discovery_model", "claude-sonnet-4-6"))
    if findings:
        print(f"\nPhase 6: Generating guide ({len(findings)} findings, critical sections with Sonnet)...")
        generate_guide(
            diagnosis, findings, output_path,
            cfg["anthropic_api_key"], cfg.get("guide_model", "claude-haiku-4-5-20251001"),
            critical_model=critical_model,
            cross_verify_report=cv_report_text,
        )
        if not os.path.exists(output_path):
            _abort("guide_generation", "guide file not created")
        guide_size_kb = os.path.getsize(output_path) / 1024
        if guide_size_kb < 10:
            _abort("guide_generation", f"guide too small: {guide_size_kb:.1f}KB (expected >= 10KB)")
        print(f"  Guide saved: {output_path}")

        # Backup
        guide_backup_dir = os.path.join(cfg.get("backup_dir", "data/backups"), "guides")
        os.makedirs(guide_backup_dir, exist_ok=True)
        shutil.copy2(output_path, os.path.join(guide_backup_dir, f"{topic_id}.md"))

    # Phase 7: Validation + refinement (Sonnet + Haiku)
    validation_model = cfg.get("validation_model", "claude-sonnet-4-6")
    haiku_model = cfg.get("guide_model", "claude-haiku-4-5-20251001")
    max_val_rounds = cfg.get("max_validation_rounds", 2)
    val_result = {"passed": False, "learnings": []}
    if os.path.exists(output_path) and cost.has_budget(reserve_usd=1.00):
        guide_text = open(output_path).read()

        print(f"\nPhase 7: Validation + auto-correction (language check + medical accuracy)...")
        val_result = refine_guide(
            guide_text=guide_text,
            diagnosis=diagnosis,
            knowledge_map=discovery["knowledge_map"],
            api_key=cfg["anthropic_api_key"],
            sonnet_model=validation_model,
            haiku_model=haiku_model,
            cost=cost,
            max_rounds=max_val_rounds,
        )
        refined_text = val_result.get("guide_text", guide_text)
        patches = val_result.get("patches_applied", [])
        lang_count = val_result.get("language_issues_found", 0)
        med_count = val_result.get("medical_corrections_applied", 0)

        print(f"  Score: {val_result.get('overall_score', '?')}/10, Passed: {val_result['passed']}")
        print(f"  Language issues fixed: {lang_count}, Medical corrections: {med_count}")
        if patches:
            print(f"  Patches applied: {len(patches)}")
            for p in patches[:5]:
                print(f"    {p}")

        # Save corrected guide if patches were applied
        if patches and refined_text != guide_text:
            with open(output_path, "w") as f:
                f.write(refined_text)
            guide_text = refined_text
            shutil.copy2(output_path, os.path.join(guide_backup_dir, f"{topic_id}.md"))
            logger.info(f"Saved corrected guide to {output_path}")

        # Targeted search for missing keywords if still not passing
        if not val_result["passed"]:
            missing = val_result.get("missing_keywords", [])
            for val_round in range(1, max_val_rounds + 1):
                if not missing or not cost.has_budget(reserve_usd=0.30):
                    break
                print(f"\nPhase 7: Targeted search round {val_round} ({len(missing)} keywords)...")
                targeted_queries = [
                    {"query_text": kw, "search_engine": "serper", "language": "en",
                     "target_section": "general"}
                    for kw in missing[:20]  # cap at 20 queries
                ]
                _search_and_enrich(
                    targeted_queries, topic_id, diagnosis, cfg, db, run_id,
                    date_from=date_from, date_to=date_to, label=f"Validation R{val_round} -- ",
                    cost=cost,
                )

                # Regenerate + re-refine guide with new findings
                findings = db.get_findings_by_topic(topic_id, limit=500)
                print(f"  Regenerating guide ({len(findings)} findings)...")
                generate_guide(
                    diagnosis, findings, output_path,
                    cfg["anthropic_api_key"], cfg.get("guide_model", "claude-haiku-4-5-20251001"),
                )
                guide_text = open(output_path).read()

                val_result = refine_guide(
                    guide_text=guide_text,
                    diagnosis=diagnosis,
                    knowledge_map=discovery["knowledge_map"],
                    api_key=cfg["anthropic_api_key"],
                    sonnet_model=validation_model,
                    haiku_model=haiku_model,
                    cost=cost,
                    max_rounds=1,
                )
                refined_text = val_result.get("guide_text", guide_text)
                if val_result.get("patches_applied") and refined_text != guide_text:
                    with open(output_path, "w") as f:
                        f.write(refined_text)
                    guide_text = refined_text
                shutil.copy2(output_path, os.path.join(guide_backup_dir, f"{topic_id}.md"))
                print(f"  Score: {val_result.get('overall_score', '?')}/10, Passed: {val_result['passed']}")
                if val_result["passed"]:
                    break
                missing = val_result.get("missing_keywords", [])

    # Phase 8: Generate human review checklist
    review_path = os.path.join(guides_dir, f"{topic_id}-review.md")
    _generate_review_checklist(
        review_path, topic_id, diagnosis, val_result, cv_report_text,
        findings_count=len(findings) if findings else 0,
        cost_report=cost.report(),
    )
    print(f"  Review checklist: {review_path}")

    # Phase 9: Skill self-improvement
    learnings = val_result.get("learnings", [])
    if learnings:
        print(f"\nPhase 9: Updating skills with {len(learnings)} learnings...")
        skills_dir = os.path.join(os.path.dirname(__file__), "..", "..", ".claude", "skills")
        skills_dir = os.path.abspath(skills_dir)
        append_learnings(os.path.join(skills_dir, "oncologist.md"), learnings)
        append_learnings(os.path.join(skills_dir, "patient-advocate.md"), learnings)

    # Finish
    duration = time.time() - start_time
    stats = {}
    for key in stats_r1:
        stats[key] = stats_r1[key] + stats_r2.get(key, 0)
    stats["duration_seconds"] = round(duration, 1)
    db.finish_run(run_id, stats)
    db.close()

    # Update registry
    if update_status:
        topic["status"] = "guide_ready"
    topic["last_researched"] = datetime.now().strftime("%Y-%m-%d")
    save_registry(topics, registry_path)

    # Report (CostTracker covers discovery/extraction/validation;
    # enrichment tokens tracked separately via get_token_usage())
    enrich_tokens = get_token_usage()
    print(f"\n=== Done in {duration:.0f}s ===")
    print(f"  Discovery: {discovery['rounds']} rounds, converged={discovery['converged']}")
    print(f"  Queries: {stats.get('queries_total', 0)}")
    print(f"  Findings: {stats.get('raw_results', 0)} raw -> {stats.get('after_enrichment', 0)} relevant")
    print(f"  Cost (Sonnet+Haiku discovery/validation):\n  {cost.report()}")
    print(f"  Enrichment tokens: {enrich_tokens['input']} in, {enrich_tokens['output']} out")


# ── v6: Seed import ──────────────────────────────────────────────────

# CNA section -> lifecycle stage mapping
CNA_SECTION_MAP = {
    "my_treatment": "Q2",
    "resistance": "Q5",
    "daily_life": "Q3",
    "alerts_safety": "Q3",
    "patient_community": "Q8",
    "research_pipeline": "Q6",
}


def cmd_seed(cfg: dict, topic_id: str, cna_path: str, registry_path: str):
    """Import seed data from onco-blog DB (in-place) + CNA DB (read-only copy)."""
    db = Database(cfg["database_path"])
    db.create_tables()

    # Check if already seeded
    existing_seed = db.execute(
        "SELECT COUNT(*) FROM search_runs WHERE run_type LIKE 'seed%' AND topic_id = ?",
        (topic_id,),
    ).fetchone()[0]
    if existing_seed > 0:
        print(f"Seed already imported for '{topic_id}' ({existing_seed} seed runs found). Skipping.")
        db.close()
        return

    # Step 1: Tag existing onco-blog findings (they're already in the DB)
    onco_count = db.execute(
        "SELECT COUNT(*) FROM findings WHERE topic_id = ?", (topic_id,),
    ).fetchone()[0]
    if onco_count > 0:
        db.execute(
            "UPDATE findings SET is_seeded = 0 WHERE topic_id = ? AND is_seeded IS NULL",
            (topic_id,),
        )
        db.conn.commit()
        print(f"  onco-blog: {onco_count} existing findings tagged (is_seeded=0, native)")

    # Step 2: Import from CNA (read-only)
    cna_imported = 0
    if os.path.exists(cna_path):
        cna_conn = sqlite3.connect(f"file:{cna_path}?mode=ro", uri=True)
        cna_conn.row_factory = sqlite3.Row
        cna_rows = cna_conn.execute("SELECT * FROM findings").fetchall()

        run_id = db.start_run("seed_cna", topic_id)

        for row in cna_rows:
            d = dict(row)
            # Title fallback: use title_english if title_original is empty
            title = d.get("title_original") or d.get("title_english", "") or ""
            # Compute content hash per SPEC 10.14
            ch = compute_content_hash(
                topic_id,
                title,
                d.get("source_url", "") or "",
            )
            # Dedup against existing
            if db.has_finding(topic_id, content_hash=ch, url=d.get("source_url")):
                continue

            lifecycle = CNA_SECTION_MAP.get(d.get("section"), None)
            db.insert_finding({
                "content_hash": ch,
                "topic_id": topic_id,
                "title_original": title,
                "snippet_original": d.get("snippet_original", ""),
                "source_language": d.get("source_language", "en"),
                "title_english": d.get("title_english", ""),
                "summary_english": d.get("summary_english", ""),
                "relevance_score": d.get("relevance_score", 5),
                "authority_score": 0,  # reclassify fills this
                "source_url": d.get("source_url", ""),
                "source_domain": d.get("source_domain", ""),
                "source_platform": d.get("source_platform", ""),
                "date_published": d.get("date_published"),
                "date_found": d.get("date_found") or now_iso(),
                "run_id": run_id,
                "lifecycle_stage": lifecycle,
                "is_seeded": 1,
                "seed_source": "cna",
            })
            cna_imported += 1

        cna_conn.close()
        db.finish_run(run_id, {"after_enrichment": cna_imported})
        print(f"  CNA: {cna_imported} findings imported (of {len(cna_rows)} total, rest were duplicates)")
    else:
        print(f"  CNA database not found at {cna_path}, skipping CNA import")

    total = db.count_findings(topic_id)
    print(f"\n  Total findings for '{topic_id}': {total}")
    db.close()


def cmd_reclassify(cfg: dict, topic_id: str):
    """Batch classify findings with NULL lifecycle_stage using Haiku."""
    import anthropic

    db = Database(cfg["database_path"])
    db.create_tables()

    # Get findings needing classification
    rows = db.execute(
        """SELECT id, title_english, summary_english, source_platform
        FROM findings WHERE topic_id = ?
          AND (lifecycle_stage IS NULL OR authority_score = 0)""",
        (topic_id,),
    ).fetchall()

    if not rows:
        print(f"No findings to reclassify for '{topic_id}'.")
        db.close()
        return

    print(f"Reclassifying {len(rows)} findings for '{topic_id}'...")

    RECLASSIFY_TOOL = {
        "name": "submit_classifications",
        "description": "Submit lifecycle stage and authority classifications for findings",
        "input_schema": {
            "type": "object",
            "properties": {
                "classifications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "finding_id": {"type": "integer"},
                            "lifecycle_stage": {
                                "type": "string",
                                "enum": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9"],
                            },
                            "authority_score": {"type": "integer", "minimum": 1, "maximum": 5},
                        },
                        "required": ["finding_id", "lifecycle_stage", "authority_score"],
                    },
                },
            },
            "required": ["classifications"],
        },
    }

    RECLASSIFY_SYSTEM = """You classify oncology research findings into lifecycle stages.

Lifecycle stages:
  Q1 = Diagnosis confirmation (molecular tests, staging, subtypes)
  Q2 = Treatment standard (approved drugs, guidelines, efficacy data)
  Q3 = Living with treatment (dosing, side effects, interactions, monitoring, emergency signs, daily life, access)
  Q4 = Metastases (common sites, detection, local treatment)
  Q5 = Resistance and progression (mechanisms, next-line options, rebiopsy)
  Q6 = Pipeline (drugs in development, clinical trials, novel modalities)
  Q7 = Mistakes (dangerous interactions, contraindicated supplements, myths)
  Q8 = Community (patient groups, caregiver support, organizations)
  Q9 = Geographic access (country-specific access, legal mechanisms, reimbursement)

Authority scores:
  5 = Trial in top journal (NEJM, Lancet, JCO), ESMO/NCCN guideline
  4 = Agency decision (FDA, EMA), systematic review
  3 = Peer-reviewed review/meta-analysis, clinical registry
  2 = Press release, medical news
  1 = Blog, forum, unknown

Classify each finding based on its title and summary."""

    client = anthropic.Anthropic(api_key=cfg["anthropic_api_key"])
    cost = CostTracker(cfg.get("max_cost_usd", 5.0))
    batch_size = 5
    classified = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        findings_text = "\n".join(
            f"ID:{r['id']} | TITLE: {r['title_english'] or '(none)'} | "
            f"SUMMARY: {(r['summary_english'] or '')[:200]} | PLATFORM: {r['source_platform']}"
            for r in batch
        )

        try:
            message = client.messages.create(
                model=cfg.get("enrichment_model", "claude-haiku-4-5-20251001"),
                max_tokens=1000,
                system=RECLASSIFY_SYSTEM,
                messages=[{"role": "user", "content": f"Classify these findings:\n\n{findings_text}"}],
                tools=[RECLASSIFY_TOOL],
                tool_choice={"type": "tool", "name": "submit_classifications"},
            )
            cost.track(cfg.get("enrichment_model", "claude-haiku-4-5-20251001"),
                      message.usage.input_tokens, message.usage.output_tokens)

            for block in message.content:
                if block.type == "tool_use":
                    for c in block.input.get("classifications", []):
                        db.execute(
                            "UPDATE findings SET lifecycle_stage = ?, authority_score = ? WHERE id = ?",
                            (c["lifecycle_stage"], c["authority_score"], c["finding_id"]),
                        )
                        classified += 1

            db.conn.commit()
            print(f"  {min(i + batch_size, len(rows))}/{len(rows)} classified", end="\r")

        except Exception as e:
            logger.error(f"Reclassify batch {i} failed: {e}")
            print(f"\n  [ERROR] Batch {i} failed: {e}")

        if i + batch_size < len(rows):
            time.sleep(0.3)

    # Report distribution
    dist = db.execute(
        """SELECT lifecycle_stage, COUNT(*) as cnt FROM findings
        WHERE topic_id = ? AND lifecycle_stage IS NOT NULL
        GROUP BY lifecycle_stage ORDER BY lifecycle_stage""",
        (topic_id,),
    ).fetchall()

    print(f"\n\n  Classified {classified}/{len(rows)} findings")
    print(f"\n  Lifecycle distribution for '{topic_id}':")
    for r in dist:
        print(f"    {r['lifecycle_stage']}: {r['cnt']}")
    print(f"\n  Cost: {cost.report()}")

    db.close()


def cmd_update_all(cfg: dict, since: str, registry_path: str):
    """Incremental update for all published topics."""
    topics = load_registry(registry_path)
    published = [t for t in topics if t.get("status") == "published"]

    if not published:
        print("No published topics to update.")
        return

    date_from = parse_since(since)
    print(f"\nUpdating {len(published)} published topics (since {date_from})...\n")

    for topic in published:
        print(f"--- {topic['id']} ---")
        cmd_topic(cfg, topic["id"], registry_path,
                  date_from=date_from, update_status=False)

    # Update last_researched dates
    save_registry(topics, registry_path)
    print(f"\nAll {len(published)} topics updated.")


def main():
    parser = argparse.ArgumentParser(description="OncoGuide Research Agent")
    parser.add_argument("--init", action="store_true", help="Initialize database")
    parser.add_argument("--topic", type=str, help="Research a specific topic by ID")
    parser.add_argument("--update-all", action="store_true", help="Update all published topics")
    parser.add_argument("--since", type=str, default="30d", help="Look back period for updates (e.g., 30d)")
    parser.add_argument("--list-topics", action="store_true", help="List all topics")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be executed without API calls")
    parser.add_argument("--seed", action="store_true", help="Import seed data from existing DBs")
    parser.add_argument("--seed-cna-path", type=str,
        default="/Users/dorins/Documents/cancer-news-agent/data/ret_findings_v3.db",
        help="Path to CNA database for seed import")
    parser.add_argument("--reclassify", action="store_true",
        help="Batch classify findings with NULL lifecycle_stage using Haiku")
    parser.add_argument("--config", type=str, default="config.json", help="Config file path")
    parser.add_argument("--registry", type=str, default="../../topics/registry.yaml", help="Registry file path")
    args = parser.parse_args()

    if args.list_topics:
        cmd_list_topics(args.registry)
        return

    cfg = load_config(args.config)
    setup_logging(cfg.get("log_file", "logs/research.log"), cfg.get("log_level", "INFO"))

    if args.init:
        cmd_init(cfg)
    elif args.seed:
        if not args.topic:
            print("ERROR: --seed requires --topic")
            sys.exit(1)
        cmd_seed(cfg, args.topic, args.seed_cna_path, args.registry)
    elif args.reclassify:
        if not args.topic:
            print("ERROR: --reclassify requires --topic")
            sys.exit(1)
        cmd_reclassify(cfg, args.topic)
    elif args.topic:
        cmd_topic(cfg, args.topic, args.registry, args.dry_run)
    elif args.update_all:
        cmd_update_all(cfg, args.since, args.registry)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
