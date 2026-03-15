"""PubMed/Entrez search backend."""

import logging
import time

logger = logging.getLogger(__name__)


def search_pubmed(query: str, email: str, date_from: str = None,
                  date_to: str = None, max_results: int = 10) -> list:
    """
    Search PubMed via Biopython Entrez.

    Returns list of dicts: {title, url, snippet, date, source, language}
    """
    try:
        from Bio import Entrez
    except ImportError:
        logger.error("Biopython not installed -- skipping PubMed search.")
        return []

    Entrez.email = email
    Entrez.tool = "OncoGuide_Research_Agent"

    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": "relevance",
    }
    if date_from:
        search_params["mindate"] = date_from.replace("-", "/")
    if date_to:
        search_params["maxdate"] = date_to.replace("-", "/")
    if date_from or date_to:
        search_params["datetype"] = "pdat"

    try:
        handle = Entrez.esearch(**search_params)
        search_results = Entrez.read(handle)
        handle.close()
        id_list = search_results.get("IdList", [])
    except Exception as e:
        logger.error(f"PubMed search failed: {e}")
        return []

    if not id_list:
        logger.info(f"PubMed: '{query[:60]}' -> 0 results")
        return []

    # Fetch details
    try:
        time.sleep(0.4)  # Respect NCBI rate limits
        handle = Entrez.efetch(db="pubmed", id=",".join(id_list),
                               rettype="xml", retmode="xml")
        from lxml import etree

        xml_data = handle.read()
        handle.close()

        if isinstance(xml_data, str):
            xml_data = xml_data.encode("utf-8")
        root = etree.fromstring(xml_data)

        results = []
        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else ""

            title_el = article.find(".//ArticleTitle")
            title = title_el.text if title_el is not None and title_el.text else ""
            if not title and title_el is not None:
                title = "".join(title_el.itertext())

            abstract_el = article.find(".//AbstractText")
            abstract = ""
            if abstract_el is not None:
                abstract = "".join(abstract_el.itertext())

            # Get publication date
            pub_date = None
            date_el = article.find(".//PubDate")
            if date_el is not None:
                year = date_el.findtext("Year", "")
                month = date_el.findtext("Month", "01")
                day = date_el.findtext("Day", "01")
                month_map = {
                    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
                    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
                    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
                }
                if month in month_map:
                    month = month_map[month]
                try:
                    pub_date = f"{year}-{int(month):02d}-{int(day):02d}"
                except (ValueError, TypeError):
                    pub_date = f"{year}-01-01" if year else None

            if pmid and title:
                results.append({
                    "title": title.strip(),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "snippet": abstract[:500] if abstract else "",
                    "date": pub_date,
                    "source": "pubmed",
                    "language": "en",
                })

        logger.info(f"PubMed: '{query[:60]}' -> {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"PubMed fetch failed: {e}")
        return []
