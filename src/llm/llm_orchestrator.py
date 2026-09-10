"""
src/llm/llm_orchestrator.py - Multi-Tier LLM Extraction Engine & Fallback Chain
GraphOne / FrontierAtlas Intelligence Graph Ingestion Pipeline
"""

import asyncio
import json
import random
import re
import logging
from typing import Dict, Any, Optional
import httpx

from src.config import GEMINI_API_KEY, GROQ_API_KEY, DEEPSEEK_API_KEY, SCHEMAS

logger = logging.getLogger("LLMOrchestrator")

class LLMOrchestrator:
    def __init__(self):
        self.gemini_key = GEMINI_API_KEY
        self.groq_key = GROQ_API_KEY
        self.deepseek_key = DEEPSEEK_API_KEY

        # Metrics Counters
        self.total_llm_requests = 0
        self.gemini_successes = 0
        self.gemini_failures = 0
        self.groq_successes = 0
        self.groq_failures = 0
        self.local_fallback_count = 0
        self.retries_429 = 0
        self.truncations_413 = 0

    def truncate_payload(self, text: str, max_chars: int = 4000) -> str:
        """Intelligent Payload Chunking strategy to avoid 413 Payload Too Large errors."""
        if not text or len(text) <= max_chars:
            return text
        
        self.truncations_413 += 1
        half = max_chars // 2
        truncated = f"{text[:half]}\n\n[... TRUNCATED TO PREVENT 413 OVERFLOW ...]\n\n{text[-half:]}"
        logger.debug(f"Payload truncated from {len(text)} to {len(truncated)} characters.")
        return truncated

    async def call_gemini_flash(self, prompt: str, system_instruction: str = "") -> Optional[Dict[str, Any]]:
        """Tier 1: Gemini Flash LLM Extraction."""
        if not self.gemini_key:
            return None
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        headers = {"Content-Type": "application/json"}
        full_prompt = f"{system_instruction}\n\n{prompt}".strip()
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data['candidates'][0]['content']['parts'][0]['text']
                    self.gemini_successes += 1
                    logger.info("LLMOrchestrator: Tier 1 Gemini: SUCCESS")
                    return json.loads(text)
                elif resp.status_code == 429:
                    self.retries_429 += 1
                    self.gemini_failures += 1
                    logger.warning("LLMOrchestrator: Tier 1 Gemini: RATE LIMITED -> falling back to Tier 2")
                    return None
                else:
                    self.gemini_failures += 1
                    logger.warning(f"LLMOrchestrator: Tier 1 Gemini failed HTTP {resp.status_code}")
                    return None
        except Exception as e:
            self.gemini_failures += 1
            logger.warning(f"LLMOrchestrator: Tier 1 Gemini exception: {e}")
            return None

    async def call_groq_llama(self, prompt: str, system_instruction: str = "") -> Optional[Dict[str, Any]]:
        """Tier 2: Groq Llama 3 LLM Extraction."""
        if not self.groq_key:
            return None

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }
        sys_content = system_instruction or "You are a precise data extraction engine. Output strictly valid JSON."
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": sys_content},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    self.groq_successes += 1
                    logger.info("LLMOrchestrator: Tier 2 Groq: SUCCESS")
                    return json.loads(content)
                elif resp.status_code == 429:
                    self.retries_429 += 1
                    self.groq_failures += 1
                    logger.warning("LLMOrchestrator: Tier 2 Groq: RATE LIMITED -> falling back to Tier 3")
                    return None
                else:
                    self.groq_failures += 1
                    logger.warning(f"LLMOrchestrator: Tier 2 Groq failed HTTP {resp.status_code}")
                    return None
        except Exception as e:
            self.groq_failures += 1
            logger.warning(f"LLMOrchestrator: Tier 2 Groq exception: {e}")
            return None

    def call_local_fallback(self, raw_text: str, task_type: str = "PRICING") -> Dict[str, Any]:
        """Tier 3: Rule-based Deterministic Structural Parser (Zero-Failure Guarantee)."""
        self.local_fallback_count += 1
        logger.info("LLMOrchestrator: Tier 3 Local: USED")
        
        txt_lower = raw_text.lower()
        if task_type == "PRICING":
            if "free" in txt_lower and "trial" in txt_lower:
                return {"pricingModel": "FREEMIUM", "confidence": 0.8}
            elif "freemium" in txt_lower or "pro plan" in txt_lower or "starter plan" in txt_lower:
                return {"pricingModel": "FREEMIUM", "confidence": 0.9}
            elif "enterprise" in txt_lower or "contact sales" in txt_lower or "book a demo" in txt_lower:
                return {"pricingModel": "ENTERPRISE", "confidence": 0.9}
            elif "pricing" in txt_lower and ("$ " in txt_lower or "/month" in txt_lower or "subscription" in txt_lower):
                return {"pricingModel": "PAID", "confidence": 0.8}
            elif "free" in txt_lower or "open source" in txt_lower or "apache" in txt_lower or "mit license" in txt_lower:
                return {"pricingModel": "FREE", "confidence": 0.85}
            else:
                return {"pricingModel": "UNKNOWN", "confidence": 0.5}
        
        return {"result": "UNKNOWN"}

    async def classify_pricing(self, text_description: str) -> Dict[str, Any]:
        """Classify product pricing model using multi-tier LLM fallback chain."""
        if not text_description or not text_description.strip():
            return {"pricingModel": "UNKNOWN", "method": "UNKNOWN", "evidence": "No text description"}

        self.total_llm_requests += 1
        safe_text = self.truncate_payload(text_description, max_chars=3000)
        
        system_prompt = "You are a product pricing classifier. Classify the pricing model of the given software/product based ONLY on the provided text. Return JSON with keys 'pricingModel' (one of FREE, FREEMIUM, PAID, ENTERPRISE, UNKNOWN) and 'evidence' (short quote from text or explanation)."
        user_prompt = f"Product Description:\n{safe_text}"

        # If no keys configured, skip LLM calls directly to local fallback
        if not self.gemini_key and not self.groq_key:
            fb = self.call_local_fallback(safe_text, task_type="PRICING")
            fb["method"] = "LOCAL_RULE"
            fb["evidence"] = "Deterministic regex match (No LLM keys configured)"
            return fb

        # Try Tier 1: Gemini
        for attempt in range(1, 3):
            res = await self.call_gemini_flash(user_prompt, system_instruction=system_prompt)
            if res and isinstance(res, dict) and "pricingModel" in res:
                res["method"] = "LLM_GEMINI"
                return res

            # Try Tier 2: Groq
            res = await self.call_groq_llama(user_prompt, system_instruction=system_prompt)
            if res and isinstance(res, dict) and "pricingModel" in res:
                res["method"] = "LLM_GROQ"
                return res

            jitter = (2 ** attempt) + random.uniform(0.1, 0.4)
            await asyncio.sleep(jitter)

        # Fallback to Tier 3
        fb = self.call_local_fallback(safe_text, task_type="PRICING")
        fb["method"] = "LOCAL_FALLBACK"
        fb["evidence"] = "Local rule classification after LLM fallback"
        return fb

    def get_metrics(self) -> Dict[str, Any]:
        """Return metrics summary dict."""
        return {
            "total_llm_requests": self.total_llm_requests,
            "gemini_successes": self.gemini_successes,
            "gemini_failures": self.gemini_failures,
            "groq_successes": self.groq_successes,
            "groq_failures": self.groq_failures,
            "local_fallback_count": self.local_fallback_count,
            "retries_429": self.retries_429,
            "truncations_413": self.truncations_413
        }
