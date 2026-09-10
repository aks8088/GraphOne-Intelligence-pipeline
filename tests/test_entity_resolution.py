"""
tests/test_entity_resolution.py - Unit Tests for Entity Resolution Engine
"""

import unittest
from src.entity_resolution.resolver import EntityResolver

class TestEntityResolution(unittest.TestCase):
    def setUp(self):
        self.resolver = EntityResolver()

    def test_exact_match(self):
        canonical = self.resolver.resolve("OpenAI", entity_type="STARTUP")
        self.assertEqual(canonical, "OpenAI")

    def test_alias_match(self):
        canonical = self.resolver.resolve("OpenAI, Inc.", entity_type="STARTUP")
        self.assertEqual(canonical, "OpenAI")

    def test_fuzzy_match(self):
        canonical = self.resolver.resolve("Minimaxai", entity_type="STARTUP")
        self.assertEqual(canonical, "MiniMax")

    def test_normalized_title_fallback(self):
        canonical = self.resolver.resolve("some-new-ai-startup inc.", entity_type="STARTUP")
        self.assertEqual(canonical, "Some New Ai Startup")

if __name__ == "__main__":
    unittest.main()
