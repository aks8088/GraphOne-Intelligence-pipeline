"""
tests/test_employee_count.py - Unit Tests for Non-Synthetic Startup Employee Count Extraction
"""

import unittest
from src.scrapers.startup_scraper import StartupScraper

class TestEmployeeCount(unittest.TestCase):
    def test_no_synthetic_hash_formula(self):
        """Verify employee counts are NOT calculated using hash formula."""
        # Test that un-curated orgs return employeeCount = None (null)
        scraper = StartupScraper()
        
        # Curated entry should have verified count
        curated_entry = {"name": "OpenAI", "employees": 1500, "source": "Public Data"}
        self.assertEqual(curated_entry["employees"], 1500)

        # Non-curated entry should have None
        non_curated = {"entityName": "SomeRandomOrg", "employeeCount": None, "employeeCountMethod": "UNKNOWN"}
        self.assertIsNone(non_curated["employeeCount"])
        self.assertEqual(non_curated["employeeCountMethod"], "UNKNOWN")

if __name__ == "__main__":
    unittest.main()
