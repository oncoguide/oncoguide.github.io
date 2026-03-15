"""openFDA API search backend."""

import logging
import time

import requests

logger = logging.getLogger(__name__)

OPENFDA_BASE = "https://api.fda.gov/drug"


def _make_request(url: str, params: dict, max_retries: int = 2) -> dict | None:
    """Make a request to the openFDA API with retry logic."""
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=20)
            if resp.status_code == 429:
                logger.warning("openFDA rate limited, waiting 10s...")
                time.sleep(10)
                continue
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            if attempt == 0:
                logger.warning(f"openFDA request failed ({e}), retrying...")
                time.sleep(2)
            else:
                logger.error(f"openFDA request failed after retry: {e}")
                return None
    return None


def search_openfda_adverse_events(drug_name: str, api_key: str = None,
                                  date_from: str = None, date_to: str = None,
                                  max_results: int = 10) -> list:
    """Search FDA Adverse Event Reporting System (FAERS) for a drug."""
    url = f"{OPENFDA_BASE}/event.json"

    search_parts = [f'patient.drug.openfda.brand_name:"{drug_name}"']
    if date_from:
        df = date_from.replace("-", "")
        dt = date_to.replace("-", "") if date_to else "20261231"
        search_parts.append(f"receivedate:[{df}+TO+{dt}]")

    params = {
        "search": "+AND+".join(search_parts),
        "limit": min(max_results, 100),
    }
    if api_key:
        params["api_key"] = api_key

    data = _make_request(url, params)
    if not data:
        return []

    results = []
    for event in data.get("results", []):
        reactions = event.get("patient", {}).get("reaction", [])
        reaction_names = [r.get("reactionmeddrapt", "") for r in reactions[:5]]
        reaction_str = ", ".join(r for r in reaction_names if r)

        patient = event.get("patient", {})
        age = patient.get("patientage")
        sex_code = patient.get("patientsex")
        sex = {"1": "Male", "2": "Female"}.get(sex_code, "Unknown")

        drugs = patient.get("drug", [])
        drug_names = [d.get("medicinalproduct", "") for d in drugs[:5]]

        outcome_str = event.get("serious", "")
        if outcome_str == "1":
            seriousness = []
            if event.get("seriousnessdeath") == "1":
                seriousness.append("death")
            if event.get("seriousnesshospitalization") == "1":
                seriousness.append("hospitalization")
            if event.get("seriousnesslifethreatening") == "1":
                seriousness.append("life-threatening")
            if event.get("seriousnessdisabling") == "1":
                seriousness.append("disability")
            outcome_str = "Serious: " + ", ".join(seriousness) if seriousness else "Serious"
        else:
            outcome_str = "Non-serious"

        receive_date = event.get("receivedate", "")
        if len(receive_date) == 8:
            receive_date = f"{receive_date[:4]}-{receive_date[4:6]}-{receive_date[6:8]}"

        safety_report_id = event.get("safetyreportid", "")

        title = f"FDA FAERS: {drug_name} -- {reaction_str}" if reaction_str else f"FDA FAERS: {drug_name} adverse event"
        snippet_parts = [
            f"Patient: {sex}, age {age}" if age else f"Patient: {sex}",
            f"Drugs: {', '.join(d for d in drug_names if d)}",
            f"Reactions: {reaction_str}" if reaction_str else "",
            outcome_str,
        ]
        snippet = " | ".join(p for p in snippet_parts if p)

        results.append({
            "title": title,
            "url": f"https://api.fda.gov/drug/event.json?search=safetyreportid:{safety_report_id}" if safety_report_id else "https://open.fda.gov/data/faers/",
            "snippet": snippet,
            "date": receive_date,
            "source": "openfda",
            "language": "en",
        })

    logger.info(f"openFDA FAERS: '{drug_name}' -> {len(results)} events")
    return results


def search_openfda_label_changes(drug_name: str, api_key: str = None,
                                 max_results: int = 5) -> list:
    """Search FDA drug label (SPL) data for a drug."""
    url = f"{OPENFDA_BASE}/label.json"

    params = {
        "search": f'openfda.brand_name:"{drug_name}"',
        "limit": min(max_results, 10),
    }
    if api_key:
        params["api_key"] = api_key

    data = _make_request(url, params)
    if not data:
        return []

    results = []
    for label in data.get("results", []):
        brand_names = label.get("openfda", {}).get("brand_name", [drug_name])
        brand = brand_names[0] if brand_names else drug_name

        effective_time = label.get("effective_time", "")
        if len(effective_time) == 8:
            effective_time = f"{effective_time[:4]}-{effective_time[4:6]}-{effective_time[6:8]}"

        version = label.get("version", "")
        indications = label.get("indications_and_usage", [""])[0][:200] if label.get("indications_and_usage") else ""
        warnings = label.get("warnings_and_cautions", label.get("warnings", [""]))[0][:200] if label.get("warnings_and_cautions") or label.get("warnings") else ""
        boxed = label.get("boxed_warning", [""])[0][:200] if label.get("boxed_warning") else ""

        title = f"FDA Label: {brand}"
        if version:
            title += f" (v{version})"

        snippet_parts = []
        if indications:
            snippet_parts.append(f"Indications: {indications}")
        if boxed:
            snippet_parts.append(f"BOXED WARNING: {boxed}")
        elif warnings:
            snippet_parts.append(f"Warnings: {warnings}")
        snippet = " | ".join(snippet_parts) if snippet_parts else f"FDA-approved labeling for {brand}"

        results.append({
            "title": title,
            "url": f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={brand}",
            "snippet": snippet,
            "date": effective_time,
            "source": "openfda",
            "language": "en",
        })

    logger.info(f"openFDA Label: '{drug_name}' -> {len(results)} labels")
    return results


def search_openfda_enforcement(drug_name: str, api_key: str = None,
                               max_results: int = 5) -> list:
    """Search FDA drug enforcement/recall data."""
    url = f"{OPENFDA_BASE}/enforcement.json"

    params = {
        "search": f'openfda.brand_name:"{drug_name}"',
        "limit": min(max_results, 10),
    }
    if api_key:
        params["api_key"] = api_key

    data = _make_request(url, params)
    if not data:
        return []

    results = []
    for recall in data.get("results", []):
        reason = recall.get("reason_for_recall", "Recall")
        classification = recall.get("classification", "")
        status = recall.get("status", "")
        distribution = recall.get("distribution_pattern", "")
        recall_date = recall.get("report_date", "")
        if len(recall_date) == 8:
            recall_date = f"{recall_date[:4]}-{recall_date[4:6]}-{recall_date[6:8]}"

        recall_number = recall.get("recall_number", "")
        product = recall.get("product_description", "")[:200]

        title = f"FDA Enforcement: {drug_name} -- {reason[:80]}"
        snippet_parts = [
            f"Classification: {classification}" if classification else "",
            f"Status: {status}" if status else "",
            f"Product: {product}" if product else "",
            f"Distribution: {distribution[:100]}" if distribution else "",
        ]
        snippet = " | ".join(p for p in snippet_parts if p)

        results.append({
            "title": title,
            "url": f"https://api.fda.gov/drug/enforcement.json?search=recall_number:{recall_number}" if recall_number else "https://open.fda.gov/data/res/",
            "snippet": snippet,
            "date": recall_date,
            "source": "openfda",
            "language": "en",
        })

    logger.info(f"openFDA Enforcement: '{drug_name}' -> {len(results)} recalls")
    return results


def search_openfda(query: str, api_key: str = "", date_from: str = None,
                   date_to: str = None, max_results: int = 10) -> list:
    """Unified search across all openFDA endpoints."""
    results = []
    results.extend(search_openfda_adverse_events(query, api_key, date_from, date_to, max_results))
    results.extend(search_openfda_label_changes(query, api_key, max_results))
    results.extend(search_openfda_enforcement(query, api_key, max_results))
    return results
