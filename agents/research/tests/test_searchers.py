"""Tests for search backends using mocked API responses."""
import json
import pytest
from unittest.mock import patch, MagicMock

from modules.searcher_serper import search_serper
from modules.searcher_pubmed import search_pubmed


class TestSerperSearcher:
    @patch("modules.searcher_serper.requests.post")
    def test_returns_list_of_findings(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "organic": [
                    {
                        "title": "Cancer Diagnosis Guide",
                        "link": "https://example.com/guide",
                        "snippet": "A comprehensive guide",
                        "date": "2026-03-15",
                    }
                ]
            },
        )
        results = search_serper("cancer diagnosis", "fake-key")
        assert len(results) == 1
        assert results[0]["title"] == "Cancer Diagnosis Guide"
        assert results[0]["source"] == "serper"

    @patch("modules.searcher_serper.requests.post")
    def test_handles_api_error(self, mock_post):
        mock_post.return_value = MagicMock(status_code=500, text="Server error")
        results = search_serper("cancer diagnosis", "fake-key")
        assert results == []


class TestPubMedSearcher:
    def test_returns_formatted_results(self):
        from Bio import Entrez
        with patch.object(Entrez, "esearch", return_value=MagicMock()), \
             patch.object(Entrez, "read", return_value={"IdList": []}):
            results = search_pubmed("cancer diagnosis", "test@example.com", max_results=1)
            assert isinstance(results, list)
            assert results == []  # empty IdList -> no results


class TestClinicalTrialsSearcher:
    @patch("modules.searcher_clinicaltrials.requests.get")
    def test_returns_list(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"studies": []}
        )
        from modules.searcher_clinicaltrials import search_clinicaltrials
        results = search_clinicaltrials("cancer", max_results=5)
        assert isinstance(results, list)


class TestOpenFDASearcher:
    @patch("modules.searcher_openfda.requests.get")
    def test_returns_list(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"results": []}
        )
        from modules.searcher_openfda import search_openfda
        results = search_openfda("selpercatinib")
        assert isinstance(results, list)


class TestCIViCSearcher:
    @patch("modules.searcher_civic.requests.post")
    def test_returns_list(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": {"evidenceItems": {"nodes": [], "totalCount": 0, "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
        )
        from modules.searcher_civic import search_civic
        results = search_civic("selpercatinib")
        assert isinstance(results, list)
