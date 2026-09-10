"""
tests/test_github_enrichment.py - Unit Tests for GitHub Star Count Enrichment
"""

import unittest
from unittest.mock import patch, MagicMock
import asyncio

from src.scrapers.paper_scraper import PaperScraper

class TestGitHubEnrichment(unittest.TestCase):
    def setUp(self):
        self.scraper = PaperScraper()

    def test_github_url_normalization(self):
        url1 = "https://github.com/OpenAI/GPT-4"
        url2 = "https://github.com/OpenAI/GPT-4/"
        url3 = "https://github.com/OpenAI/GPT-4.git"

        norm1 = PaperScraper.normalize_github_repo(url1)
        norm2 = PaperScraper.normalize_github_repo(url2)
        norm3 = PaperScraper.normalize_github_repo(url3)

        self.assertEqual(norm1, ("OpenAI", "GPT-4"))
        self.assertEqual(norm2, ("OpenAI", "GPT-4"))
        self.assertEqual(norm3, ("OpenAI", "GPT-4"))

    @patch("src.scrapers.paper_scraper.httpx.AsyncClient.get")
    def test_github_successful_star_fetch(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"stargazers_count": 1540}
        mock_get.return_value = mock_resp

        stars = asyncio.run(self.scraper.fetch_github_stars("https://github.com/OpenAI/GPT-4"))
        self.assertEqual(stars, 1540)
        self.assertEqual(self.scraper.github_successes, 1)
        self.assertEqual(self.scraper.github_stars_populated, 1)

    @patch("src.scrapers.paper_scraper.httpx.AsyncClient.get")
    def test_github_cache_hit(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"stargazers_count": 500}
        mock_get.return_value = mock_resp

        stars1 = asyncio.run(self.scraper.fetch_github_stars("https://github.com/meta-llama/llama3"))
        stars2 = asyncio.run(self.scraper.fetch_github_stars("https://github.com/meta-llama/llama3/"))

        self.assertEqual(stars1, 500)
        self.assertEqual(stars2, 500)
        self.assertEqual(self.scraper.github_queried, 1)  # Only queried once
        self.assertEqual(self.scraper.github_cache_hits, 1)  # Second call hit cache

    @patch("src.scrapers.paper_scraper.httpx.AsyncClient.get")
    def test_github_404_handling(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        stars = asyncio.run(self.scraper.fetch_github_stars("https://github.com/nonexistent/fake-repo"))
        self.assertIsNone(stars)
        self.assertEqual(self.scraper.github_404s, 1)
        self.assertEqual(self.scraper.github_stars_unavailable, 1)

    @patch("src.scrapers.paper_scraper.httpx.AsyncClient.get")
    def test_github_rate_limit_handling(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.headers = {"retry-after": "1"}
        mock_get.return_value = mock_resp

        stars = asyncio.run(self.scraper.fetch_github_stars("https://github.com/rate/limited"))
        self.assertIsNone(stars)
        self.assertGreaterEqual(self.scraper.github_rate_limits, 1)
        self.assertEqual(self.scraper.github_stars_unavailable, 1)

if __name__ == "__main__":
    unittest.main()
