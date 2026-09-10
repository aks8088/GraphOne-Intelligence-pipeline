"""
tests/test_llm_orchestrator.py - Unit Tests for LLM Orchestrator
"""

import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from src.llm.llm_orchestrator import LLMOrchestrator

class TestLLMOrchestrator(unittest.TestCase):
    def setUp(self):
        self.orchestrator = LLMOrchestrator()

    def test_413_truncation(self):
        long_text = "A" * 10000
        truncated = self.orchestrator.truncate_payload(long_text, max_chars=4000)
        self.assertLessEqual(len(truncated), 4200)
        self.assertIn("[... TRUNCATED TO PREVENT 413 OVERFLOW ...]", truncated)
        self.assertEqual(self.orchestrator.truncations_413, 1)

    def test_missing_api_keys_fallback(self):
        self.orchestrator.gemini_key = ""
        self.orchestrator.groq_key = ""
        
        result = asyncio.run(self.orchestrator.classify_pricing("Pro plan subscription costs $20/month"))
        self.assertEqual(result.get("pricingModel"), "FREEMIUM")
        self.assertEqual(result.get("method"), "LOCAL_RULE")
        self.assertEqual(self.orchestrator.local_fallback_count, 1)

    @patch("src.llm.llm_orchestrator.httpx.AsyncClient.post")
    def test_gemini_success(self, mock_post):
        self.orchestrator.gemini_key = "test_gemini_key"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"text": '{"pricingModel": "ENTERPRISE", "evidence": "Contact sales"}'}]
                }
            }]
        }
        mock_post.return_value = mock_resp

        result = asyncio.run(self.orchestrator.classify_pricing("Custom enterprise sales required."))
        self.assertEqual(result.get("pricingModel"), "ENTERPRISE")
        self.assertEqual(result.get("method"), "LLM_GEMINI")
        self.assertEqual(self.orchestrator.gemini_successes, 1)

    @patch("src.llm.llm_orchestrator.httpx.AsyncClient.post")
    def test_gemini_429_fallback_to_groq(self, mock_post):
        self.orchestrator.gemini_key = "test_gemini_key"
        self.orchestrator.groq_key = "test_groq_key"
        
        # Mock Gemini returning 429, Groq returning 200
        resp_429 = MagicMock()
        resp_429.status_code = 429

        resp_groq = MagicMock()
        resp_groq.status_code = 200
        resp_groq.json.return_value = {
            "choices": [{"message": {"content": '{"pricingModel": "FREE", "evidence": "Open source"}'}}]
        }

        mock_post.side_effect = [resp_429, resp_groq]

        result = asyncio.run(self.orchestrator.classify_pricing("Open source software"))
        self.assertEqual(result.get("pricingModel"), "FREE")
        self.assertEqual(result.get("method"), "LLM_GROQ")
        self.assertEqual(self.orchestrator.gemini_failures, 1)
        self.assertEqual(self.orchestrator.groq_successes, 1)

if __name__ == "__main__":
    unittest.main()
