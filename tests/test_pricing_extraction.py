"""
tests/test_pricing_extraction.py - Unit Tests for Non-Synthetic Product Pricing Extraction
"""

import unittest
from src.scrapers.product_scraper import ProductScraper

class TestPricingExtraction(unittest.TestCase):
    def test_no_synthetic_round_robin(self):
        """Verify pricing model is NOT derived using record index modulo formula."""
        scraper = ProductScraper()
        
        # Test sample text descriptions
        p1, m1, e1 = scraper.derive_pricing_from_text("Free tier available with 100 queries; Pro subscription costs $20/month")
        p2, m2, e2 = scraper.derive_pricing_from_text("Enterprise custom contract pricing with dedicated SLA")
        p3, m3, e3 = scraper.derive_pricing_from_text("Open-source software licensed under MIT License")
        p4, m4, e4 = scraper.derive_pricing_from_text("Random description with no pricing details")

        self.assertEqual(p1, "FREEMIUM")
        self.assertEqual(p2, "ENTERPRISE")
        self.assertEqual(p3, "FREE")
        self.assertEqual(p4, "UNKNOWN")

    def test_pricing_allowed_enum(self):
        allowed = {"FREE", "FREEMIUM", "PAID", "ENTERPRISE", "UNKNOWN"}
        scraper = ProductScraper()
        p, _, _ = scraper.derive_pricing_from_text("Pro plan available")
        self.assertIn(p, allowed)

if __name__ == "__main__":
    unittest.main()
