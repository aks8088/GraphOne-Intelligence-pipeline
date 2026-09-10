"""
tests/test_pipeline.py - Unit/Integration Tests for Master Pipeline Execution
"""

import unittest
from unittest.mock import patch, MagicMock
import asyncio

from src.pipeline import MasterPipeline

class TestMasterPipeline(unittest.TestCase):
    @patch("src.pipeline.StartupScraper.scrape")
    @patch("src.pipeline.ProductScraper.scrape")
    @patch("src.pipeline.PaperScraper.scrape")
    @patch("src.pipeline.NewsScraper.scrape")
    @patch("src.pipeline.JobScraper.scrape")
    def test_pipeline_execution_flow(self, mock_jobs, mock_news, mock_papers, mock_products, mock_startups):
        mock_startups.return_value = [{"schemaVersion": "1.0", "recordType": "STARTUP", "source": {"name": "Test", "url": "http://test.com"}, "content": {"entityName": "OpenAI", "data": {"employeeCount": 1500, "employeeCountMethod": "SOURCE_DATA"}}, "collectedAt": "2026-09-06T12:00:00Z"}]
        mock_products.return_value = [{"schemaVersion": "1.0", "recordType": "PRODUCT", "source": {"name": "Test", "url": "http://test.com"}, "content": {"startupName": "OpenAI", "pricingModel": "FREEMIUM", "pricingMethod": "SOURCE_METADATA"}, "collectedAt": "2026-09-06T12:00:00Z"}]
        mock_papers.return_value = [{"schemaVersion": "1.0", "recordType": "RESEARCH_PAPER", "source": {"name": "Test", "url": "http://test.com"}, "content": {"title": "Test Paper", "authors": ["Author 1"], "paper_url": "http://test.com", "github_url": "https://github.com/OpenAI/GPT", "github_stars": 100, "published_date": "2026-09-06T12:00:00Z"}, "collectedAt": "2026-09-06T12:00:00Z"}]
        mock_news.return_value = []
        mock_jobs.return_value = []

        pipeline = MasterPipeline(target_startups=1, target_products=1, target_papers=1)
        asyncio.run(pipeline.run())

        self.assertGreaterEqual(len(pipeline.resolver.get_mapping_log()), 2)

if __name__ == "__main__":
    unittest.main()
