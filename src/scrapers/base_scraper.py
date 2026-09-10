"""
src/scrapers/base_scraper.py - Base Async Scraper with Anti-Bot & Date Normalization
GraphOne / FrontierAtlas Intelligence Graph Ingestion Pipeline
"""

import asyncio
import random
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from src.config import MAX_CONCURRENT_REQUESTS, DEFAULT_TIMEOUT, MAX_RETRIES, FRESHNESS_HOURS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("BaseScraper")

# User-Agent Pool for Anti-Bot Bypass
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
]

class BaseScraper:
    def __init__(self, concurrency_limit: int = MAX_CONCURRENT_REQUESTS):
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1"
        }
        self.client = httpx.AsyncClient(
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
            verify=False
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def fetch(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Fetch URL content with rate limiting, User-Agent rotation, and exponential backoff."""
        async with self.semaphore:
            req_headers = {"User-Agent": random.choice(USER_AGENTS)}
            if headers:
                req_headers.update(headers)
            
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    if not self.client:
                        self.client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True, verify=False)
                    
                    response = await self.client.get(url, headers=req_headers)
                    if response.status_code == 200:
                        return response.text
                    elif response.status_code in [429, 503, 502]:
                        backoff = (2 ** attempt) + random.uniform(0.1, 1.0)
                        logger.warning(f"HTTP {response.status_code} for {url}. Retrying in {backoff:.2f}s (Attempt {attempt}/{MAX_RETRIES})")
                        await asyncio.sleep(backoff)
                    else:
                        logger.warning(f"HTTP {response.status_code} for {url}")
                        return None
                except Exception as e:
                    backoff = (2 ** attempt) + random.uniform(0.1, 1.0)
                    logger.warning(f"Fetch error for {url}: {e}. Retrying in {backoff:.2f}s (Attempt {attempt}/{MAX_RETRIES})")
                    await asyncio.sleep(backoff)
            return None

    @staticmethod
    def parse_datetime(date_str: str) -> datetime:
        """Parse arbitrary date string into UTC datetime object."""
        if not date_str:
            return datetime.now(timezone.utc)
        
        cleaned = str(date_str).strip()
        now_utc = datetime.now(timezone.utc)
        
        # Handle relative date strings (e.g., "2 hours ago", "15 mins ago", "1 day ago")
        rel_match = re.search(r'(\d+)\s*(hour|min|minute|day|sec|second)s?\s*ago', cleaned, re.IGNORECASE)
        if rel_match:
            amount = int(rel_match.group(1))
            unit = rel_match.group(2).lower()
            if 'sec' in unit:
                return now_utc - timedelta(seconds=amount)
            elif 'min' in unit:
                return now_utc - timedelta(minutes=amount)
            elif 'hour' in unit:
                return now_utc - timedelta(hours=amount)
            elif 'day' in unit:
                return now_utc - timedelta(days=amount)

        if cleaned.lower() in ["yesterday", "1 day ago"]:
            return now_utc - timedelta(days=1)
        if cleaned.lower() in ["today", "just now"]:
            return now_utc

        # Standard date parsing via dateutil
        try:
            parsed = date_parser.parse(cleaned)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            else:
                parsed = parsed.astimezone(timezone.utc)
            return parsed
        except Exception:
            return now_utc

    @classmethod
    def is_within_24_hours(cls, date_input: Any) -> bool:
        """Check if a date is strictly within the last 24 hours."""
        if isinstance(date_input, str):
            dt = cls.parse_datetime(date_input)
        elif isinstance(date_input, datetime):
            dt = date_input if date_input.tzinfo else date_input.replace(tzinfo=timezone.utc)
        else:
            return False

        cutoff = datetime.now(timezone.utc) - timedelta(hours=FRESHNESS_HOURS)
        return dt >= cutoff
