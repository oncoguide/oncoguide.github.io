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
import sys
import time
from datetime import datetime, timedelta

import yaml

# Add parent to path for module imports
sys.path.insert(0, os.path.dirname(__file__))

from modules.database import Database
from modules.enrichment import enrich_batch, get_token_usage, reset_token_usage
from modules.guide_generator import generate_guide
from modules.query_expander import expand_queries
from modules.searcher_serper import search_serper
from modules.searcher_pubmed import search_pubmed
from modules.searcher_clinicaltrials import search_clinicaltrials
from modules.searcher_openfda import search_openfda
from modules.searcher_civic import search_civic
from modules.utils import compute_content_hash, extract_domain, now_iso, setup_logging

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
        print("  export PUBMED_EMAIL='your@email.com'")
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
        f.write("# Status: planned -> researching -> guide_ready -> drafting -> review -> published\n\n")
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


def cmd_topic(cfg: dict, topic_id: str, registry_path: str, dry_run: bool = False,
              date_from: str = None, date_to: str = None, update_status: bool = True):
    """Research a specific topic -- full pipeline.
    If update_status=False (used by --update-all), don't change topic status."""
    topics = load_registry(registry_path)
    topic = find_topic(topics, topic_id)
    if not topic:
        print(f"ERROR: Topic '{topic_id}' not found in registry.")
        sys.exit(1)

    start_time = time.time()
    reset_token_usage()

    print(f"\n=== Researching: {topic['title']} ===\n")

    # Step 1: Expand queries
    print("Step 1: Expanding queries...")
    queries = expand_queries(
        topic["title"], topic["search_queries"],
        cfg["anthropic_api_key"], cfg.get("query_expansion_model", "claude-haiku-4-5-20251001"),
    )
    print(f"  {len(topic['search_queries'])} base -> {len(queries)} total queries")

    if dry_run:
        print("\n--- DRY RUN ---")
        for q in queries:
            print(f"  [{q['search_engine']}] [{q.get('language', 'en')}] {q['query_text']}")
        print(f"\nEstimated API calls: {len(queries)} searches + enrichment")
        return

    # Step 2: Initialize DB and start run
    db = Database(cfg["database_path"])
    db.create_tables()
    db.backup(cfg.get("backup_dir", "data/backups"), cfg.get("max_backups", 10))
    run_id = db.start_run("topic", topic_id)

    # Update status (only for direct --topic calls, not --update-all)
    if update_status:
        topic["status"] = "researching"
        save_registry(topics, registry_path)

    # Step 3: Search
    print("Step 2: Searching...")
    all_results = []
    stats = {"queries_total": 0, "raw_results": 0, "after_dedup": 0,
             "after_enrichment": 0, "discarded": 0}

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
            db.log_search(run_id, q["query_text"], engine, q.get("language", "en"),
                         0, 0, "error", str(e))

        if delay > 0 and i < len(queries) - 1:
            time.sleep(delay)

    stats["after_dedup"] = len(all_results)
    print(f"\n  Total: {stats['raw_results']} raw -> {stats['after_dedup']} after dedup")

    # Step 4: Enrich
    if all_results:
        print(f"\nStep 3: Enriching {len(all_results)} findings...")
        enrichments = enrich_batch(
            all_results, topic["title"], cfg["anthropic_api_key"],
            cfg.get("enrichment_model", "claude-haiku-4-5-20251001"),
            cfg.get("delay_between_enrichments", 0.3),
            progress_callback=lambda cur, tot: print(f"  {cur}/{tot}", end="\r"),
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
                    "source_url": finding.get("url", ""),
                    "source_domain": extract_domain(finding.get("url", "")),
                    "source_platform": finding.get("source", "unknown"),
                    "date_published": finding.get("date"),
                    "date_found": now_iso(),
                    "run_id": run_id,
                })
                stats["after_enrichment"] += 1
            else:
                stats["discarded"] += 1

        print(f"  Relevant: {stats['after_enrichment']}, Discarded: {stats['discarded']}")

    # Step 5: Generate guide
    findings = db.get_findings_by_topic(topic_id, limit=500)
    if findings:
        guides_dir = cfg.get("guides_dir", "data/guides")
        output_path = os.path.join(guides_dir, f"{topic_id}.md")
        print(f"\nStep 4: Generating master guide...")
        generate_guide(
            topic["title"], findings, output_path,
            cfg["anthropic_api_key"], cfg.get("guide_model", "claude-haiku-4-5-20251001"),
        )
        print(f"  Guide saved: {output_path}")

    # Finish
    duration = time.time() - start_time
    stats["duration_seconds"] = round(duration, 1)
    db.finish_run(run_id, stats)
    db.close()

    # Update registry
    if update_status:
        topic["status"] = "guide_ready"
    topic["last_researched"] = datetime.now().strftime("%Y-%m-%d")
    save_registry(topics, registry_path)

    # Report
    tokens = get_token_usage()
    print(f"\n=== Done in {duration:.0f}s ===")
    print(f"  Queries: {stats['queries_total']}")
    print(f"  Results: {stats['raw_results']} raw -> {stats['after_dedup']} dedup -> {stats['after_enrichment']} relevant")
    print(f"  Tokens: {tokens['input']} in, {tokens['output']} out")


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
    elif args.topic:
        cmd_topic(cfg, args.topic, args.registry, args.dry_run)
    elif args.update_all:
        cmd_update_all(cfg, args.since, args.registry)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
