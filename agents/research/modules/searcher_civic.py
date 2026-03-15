"""CIViC (Clinical Interpretation of Variants in Cancer) GraphQL backend."""

import logging
import time

import requests

logger = logging.getLogger(__name__)

CIVIC_API_URL = "https://civicdb.org/api/graphql"

EVIDENCE_QUERY = """
query SearchEvidence($therapyName: String, $molecularProfileName: String,
                     $first: Int, $after: String) {
  evidenceItems(
    therapyName: $therapyName
    molecularProfileName: $molecularProfileName
    first: $first
    after: $after
    status: ACCEPTED
  ) {
    totalCount
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      id
      name
      description
      evidenceType
      evidenceLevel
      evidenceDirection
      significance
      molecularProfile {
        name
      }
      disease {
        name
      }
      therapies {
        name
      }
      source {
        citation
        sourceUrl
        sourceType
      }
    }
  }
}
"""


def search_civic(query: str, max_results: int = 10) -> list:
    """
    Search CIViC database for genomic evidence items.

    The query is used as both therapyName and molecularProfileName
    (two separate searches, merged).

    Returns list of dicts: {title, url, snippet, date, source, language}
    """
    all_results = []

    # Search by therapy name first, then by molecular profile
    for search_field in ["therapyName", "molecularProfileName"]:
        variables = {
            "first": min(max_results, 25),
            search_field: query,
        }

        results = _fetch_evidence(variables, max_results - len(all_results))
        all_results.extend(results)

        if len(all_results) >= max_results:
            break

    # Dedup by URL
    seen = set()
    deduped = []
    for r in all_results:
        if r["url"] not in seen:
            seen.add(r["url"])
            deduped.append(r)

    logger.info(f"CIViC: '{query}' -> {len(deduped)} evidence items")
    return deduped[:max_results]


def _fetch_evidence(variables: dict, max_results: int) -> list:
    """Fetch evidence items from CIViC GraphQL API."""
    results = []
    cursor = None

    while len(results) < max_results:
        if cursor:
            variables["after"] = cursor

        for attempt in range(2):
            try:
                resp = requests.post(
                    CIVIC_API_URL,
                    json={"query": EVIDENCE_QUERY, "variables": variables},
                    headers={"Content-Type": "application/json"},
                    timeout=20,
                )
                if resp.status_code == 429:
                    logger.warning("CIViC rate limited, waiting 5s...")
                    time.sleep(5)
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
            except requests.RequestException as e:
                if attempt == 0:
                    logger.warning(f"CIViC request failed ({e}), retrying...")
                    time.sleep(2)
                else:
                    logger.error(f"CIViC request failed after retry: {e}")
                    return results
        else:
            return results

        if "errors" in data:
            logger.error(f"CIViC GraphQL errors: {data['errors']}")
            return results

        evidence_items = data.get("data", {}).get("evidenceItems", {})
        nodes = evidence_items.get("nodes", [])
        if not nodes:
            break

        for node in nodes:
            if len(results) >= max_results:
                break

            eid = node.get("id", "")
            mol_profile = node.get("molecularProfile", {}).get("name", "")
            disease = node.get("disease", {}).get("name", "")
            therapies = [t.get("name", "") for t in node.get("therapies", [])]
            therapy_str = ", ".join(t for t in therapies if t)
            ev_type = node.get("evidenceType", "")
            ev_level = node.get("evidenceLevel", "")
            ev_sig = node.get("significance", "")
            ev_dir = node.get("evidenceDirection", "")
            description = node.get("description", "")

            source = node.get("source", {})
            citation = source.get("citation", "")
            source_url = source.get("sourceUrl", "")

            title_parts = [f"CIViC EID{eid}"]
            if mol_profile:
                title_parts.append(mol_profile)
            if disease:
                title_parts.append(disease)
            if therapy_str:
                title_parts.append(therapy_str)
            title = " -- ".join(title_parts)

            url = source_url if source_url else f"https://civicdb.org/evidence/{eid}/summary"

            snippet_parts = [
                f"Evidence: {ev_type} ({ev_level})" if ev_level else f"Evidence: {ev_type}",
                f"Significance: {ev_sig}" if ev_sig else "",
                f"Direction: {ev_dir}" if ev_dir else "",
            ]
            if citation:
                snippet_parts.append(f"Source: {citation}")
            if description:
                snippet_parts.append(description[:300])
            snippet = " | ".join(p for p in snippet_parts if p)

            results.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "date": None,
                "source": "civic",
                "language": "en",
            })

        page_info = evidence_items.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
        time.sleep(1)

    return results
