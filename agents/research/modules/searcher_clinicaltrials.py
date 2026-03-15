"""ClinicalTrials.gov API v2 search backend."""

import logging
import time

import requests

logger = logging.getLogger(__name__)

CT_API_URL = "https://clinicaltrials.gov/api/v2/studies"

CT_FIELDS = (
    "protocolSection.identificationModule.nctId,"
    "protocolSection.identificationModule.briefTitle,"
    "protocolSection.statusModule.overallStatus,"
    "protocolSection.statusModule.lastUpdatePostDateStruct,"
    "protocolSection.designModule.phases,"
    "protocolSection.descriptionModule.briefSummary,"
    "protocolSection.conditionsModule.conditions,"
    "protocolSection.armsInterventionsModule.interventions"
)


def search_clinicaltrials(query: str, max_results: int = 10,
                          date_from: str = None) -> list:
    """
    Search ClinicalTrials.gov API v2.

    Returns list of dicts: {title, url, snippet, date, source, language}
    """
    params = {
        "format": "json",
        "fields": CT_FIELDS,
        "pageSize": min(max_results, 20),
        "query.term": query,
    }

    if date_from:
        params["filter.advanced"] = f"AREA[LastUpdatePostDate]RANGE[{date_from},MAX]"

    results = []
    pages_fetched = 0
    max_pages = (max_results + 19) // 20

    while pages_fetched < max_pages and len(results) < max_results:
        for attempt in range(2):
            try:
                resp = requests.get(CT_API_URL, params=params, timeout=20)
                if resp.status_code == 429:
                    logger.warning("ClinicalTrials.gov rate limited, waiting 5s...")
                    time.sleep(5)
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
            except requests.RequestException as e:
                if attempt == 0:
                    logger.warning(f"ClinicalTrials.gov request failed ({e}), retrying...")
                    time.sleep(2)
                else:
                    logger.error(f"ClinicalTrials.gov request failed after retry: {e}")
                    return results
        else:
            return results

        studies = data.get("studies", [])
        if not studies:
            break

        for study in studies:
            if len(results) >= max_results:
                break

            proto = study.get("protocolSection", {})
            ident = proto.get("identificationModule", {})
            status_mod = proto.get("statusModule", {})
            design = proto.get("designModule", {})
            desc = proto.get("descriptionModule", {})
            conds = proto.get("conditionsModule", {})
            arms = proto.get("armsInterventionsModule", {})

            nct_id = ident.get("nctId", "")
            title = ident.get("briefTitle", "")
            status = status_mod.get("overallStatus", "")
            last_update = status_mod.get("lastUpdatePostDateStruct", {})
            update_date = last_update.get("date", "")
            phases = design.get("phases", [])
            phase_str = ", ".join(phases) if phases else "N/A"
            summary = desc.get("briefSummary", "")
            conditions = conds.get("conditions", [])
            interventions = arms.get("interventions", [])
            intervention_names = [i.get("name", "") for i in interventions] if interventions else []

            snippet_parts = [f"Status: {status}", f"Phase: {phase_str}"]
            if conditions:
                snippet_parts.append(f"Conditions: {', '.join(conditions[:3])}")
            if intervention_names:
                snippet_parts.append(f"Interventions: {', '.join(intervention_names[:3])}")
            if summary:
                snippet_parts.append(summary[:300])
            snippet = " | ".join(snippet_parts)

            results.append({
                "title": f"[{nct_id}] {title}" if nct_id else title,
                "url": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
                "snippet": snippet,
                "date": update_date,
                "source": "clinicaltrials",
                "language": "en",
            })

        pages_fetched += 1

        next_token = data.get("nextPageToken")
        if not next_token or len(results) >= max_results:
            break
        params["pageToken"] = next_token
        time.sleep(1)

    logger.info(f"ClinicalTrials.gov: '{query[:60]}' -> {len(results)} results")
    return results
