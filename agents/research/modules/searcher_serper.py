"""Serper.dev Google search backend."""

import logging
import time

import requests

from .utils import sanitize_text, parse_date

logger = logging.getLogger(__name__)

SERPER_URL = "https://google.serper.dev/search"

# Map language codes to Serper gl/hl parameters
LANG_TO_GL = {
    "en": "us", "es": "es", "de": "de", "fr": "fr", "it": "it",
    "pt": "br", "nl": "nl", "pl": "pl", "ro": "ro",
}


def search_serper(query: str, api_key: str, language: str = "en",
                  date_from: str = None, date_to: str = None,
                  max_results: int = 10) -> list:
    """
    Search Google via Serper.dev API.

    Returns list of dicts: {title, url, snippet, date, source, language}
    """
    q = query
    if date_from:
        q += f" after:{date_from}"
    if date_to:
        q += f" before:{date_to}"

    gl = LANG_TO_GL.get(language, "us")
    hl = language

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "q": q,
        "num": max_results,
        "gl": gl,
        "hl": hl,
    }

    for attempt in range(2):
        try:
            resp = requests.post(SERPER_URL, json=payload, headers=headers, timeout=15)
            if resp.status_code == 429:
                logger.warning("Serper rate limited, waiting 5s...")
                time.sleep(5)
                continue
            if resp.status_code != 200:
                logger.error(f"Serper returned {resp.status_code}: {resp.text[:200]}")
                return []
            data = resp.json()
            break
        except requests.RequestException as e:
            if attempt == 0:
                logger.warning(f"Serper request failed ({e}), retrying...")
                time.sleep(2)
            else:
                logger.error(f"Serper request failed after retry: {e}")
                return []
    else:
        return []

    results = []
    for item in data.get("organic", []):
        results.append({
            "title": sanitize_text(item.get("title", "")),
            "url": item.get("link", ""),
            "snippet": sanitize_text(item.get("snippet", "")),
            "date": parse_date(item.get("date")),
            "source": "serper",
            "language": language,
        })

    logger.info(f"Serper: '{query[:60]}' -> {len(results)} results")
    return results
