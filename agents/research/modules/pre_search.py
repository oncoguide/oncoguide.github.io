"""Pre-search: ground discovery loop with real external data.

Generates template queries (mechanical, zero AI) + Haiku complement queries,
searches all backends, enriches with Haiku, returns formatted top findings
as context text for the oncologist's system prompt.

Results are ephemeral -- NOT stored in the database.
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
# Zero AI involvement -- this is the anchor that catches what Claude does not know.

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


HAIKU_QUERIES_TOOL = {
    "name": "submit_haiku_queries",
    "description": "Submit AI-generated complement search queries for pre-search phase",
    "input_schema": {
        "type": "object",
        "properties": {
            "queries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "query_text": {"type": "string"},
                        "search_engine": {
                            "type": "string",
                            "enum": ["pubmed", "serper", "clinicaltrials", "openfda", "civic"],
                        },
                        "language": {"type": "string"},
                    },
                    "required": ["query_text", "search_engine"],
                },
            }
        },
        "required": ["queries"],
    },
}

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

Use the submit_haiku_queries tool. No duplicates with existing templates."""


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
            tools=[HAIKU_QUERIES_TOOL],
            tool_choice={"type": "tool", "name": "submit_haiku_queries"},
        )
        cost.track(model, message.usage.input_tokens, message.usage.output_tokens)

        queries = message.content[0].input["queries"]
        for q in queries:
            q.setdefault("language", "en")
        logger.info(f"Haiku generated {len(queries)} complement queries")
        return queries

    except Exception as e:
        logger.error(f"Haiku query generation failed: {e}")
        return []


# --- Searcher dispatch (no DB dependency) ---


def _get_available_searchers(cfg: dict) -> dict:
    """Return searcher functions for backends with available API keys."""
    searchers = {}
    if cfg.get("serper_api_key"):
        searchers["serper"] = lambda q, cfg_inner, **kw: search_serper(
            q["query_text"], cfg_inner["serper_api_key"], q.get("language", "en"),
            kw.get("date_from"), kw.get("date_to"), cfg_inner.get("max_results_per_query", 10))
    if cfg.get("pubmed_email"):
        searchers["pubmed"] = lambda q, cfg_inner, **kw: search_pubmed(
            q["query_text"], cfg_inner["pubmed_email"],
            kw.get("date_from"), kw.get("date_to"), cfg_inner.get("max_results_per_query", 10))
    # clinicaltrials has no API key requirement
    searchers["clinicaltrials"] = lambda q, cfg_inner, **kw: search_clinicaltrials(
        q["query_text"], cfg_inner.get("max_results_per_query", 10), kw.get("date_from"))
    if cfg.get("openfda_api_key"):
        searchers["openfda"] = lambda q, cfg_inner, **kw: search_openfda(
            q["query_text"], cfg_inner.get("openfda_api_key", ""),
            kw.get("date_from"), kw.get("date_to"), cfg_inner.get("max_results_per_query", 10))
    # civic has no API key requirement
    searchers["civic"] = lambda q, cfg_inner, **kw: search_civic(
        q["query_text"], cfg_inner.get("max_results_per_query", 10))
    return searchers


# --- Format findings as context string ---


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
        truncated = result[:MAX_CONTEXT_CHARS].rsplit("\n", 1)[0]
        truncated += "\n\n... (findings truncated, see logs for full output)"
        result = truncated

    return result


# --- Execute searches (no DB) ---


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
