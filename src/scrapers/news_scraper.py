"""
src/scrapers/news_scraper.py - 24-Hour Fresh AI News Signal Scraper
GraphOne / FrontierAtlas Intelligence Graph Ingestion Pipeline
"""

import asyncio
import xml.etree.ElementTree as ET
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger("NewsScraper")

NEWS_SOURCES = [
    {"name": "TechCrunch AI", "type": "rss", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "VentureBeat AI", "type": "rss", "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "MIT Tech Review AI", "type": "rss", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/"},
    {"name": "Hacker News AI", "type": "hn_api", "url": "https://hn.algolia.com/api/v1/search_by_date?tags=story&query=AI"},
    {"name": "Hugging Face Daily Papers", "type": "hf_api", "url": "https://huggingface.co/api/daily_papers"}
]

class NewsScraper(BaseScraper):
    def __init__(self):
        super().__init__()

    async def scrape_rss_source(self, source: Dict[str, str]) -> List[Dict[str, Any]]:
        """Scrape RSS feed news source with 24-hr freshness enforcement."""
        items = []
        name = source["name"]
        url = source["url"]

        xml_data = await self.fetch(url)
        if not xml_data:
            return items

        try:
            root = ET.fromstring(xml_data)
            channel = root.find("channel")
            if channel is None:
                return items

            for elem in channel.findall("item"):
                title_elem = elem.find("title")
                link_elem = elem.find("link")
                pub_elem = elem.find("pubDate")
                desc_elem = elem.find("description")

                title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Untitled News"
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else url
                pub_str = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""

                # Parse & Normalize Date
                pub_dt = self.parse_datetime(pub_str)

                # Strict 24-Hour Freshness Check
                if not self.is_within_24_hours(pub_dt):
                    continue

                summary = ""
                if desc_elem is not None and desc_elem.text:
                    soup = BeautifulSoup(desc_elem.text, "html.parser")
                    summary = soup.get_text().strip()[:400]

                items.append({
                    "source_name": name,
                    "url": link,
                    "title": title,
                    "summary": summary or title,
                    "published_date": pub_dt.isoformat()
                })
        except Exception as e:
            logger.error(f"Error parsing RSS news for {name}: {e}")

        return items

    async def scrape_hn_api(self, source: Dict[str, str]) -> List[Dict[str, Any]]:
        """Scrape Hacker News AI stories via Algolia API with 24-hr freshness."""
        items = []
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
                resp = await client.get(source["url"])
                if resp.status_code == 200:
                    hits = resp.json().get("hits", [])
                    for hit in hits:
                        title = hit.get("title", "")
                        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                        created_at = hit.get("created_at", "")
                        
                        pub_dt = self.parse_datetime(created_at)
                        if not self.is_within_24_hours(pub_dt):
                            continue

                        items.append({
                            "source_name": source["name"],
                            "url": url,
                            "title": title,
                            "summary": f"Hacker News submission with {hit.get('points', 0)} points and {hit.get('num_comments', 0)} comments.",
                            "published_date": pub_dt.isoformat()
                        })
        except Exception as e:
            logger.error(f"Error scraping HN API: {e}")
        return items

    async def scrape_hf_api(self, source: Dict[str, str]) -> List[Dict[str, Any]]:
        """Scrape Hugging Face daily AI news & paper announcements."""
        items = []
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
                resp = await client.get(source["url"])
                if resp.status_code == 200:
                    papers = resp.json()
                    for item in papers:
                        p = item.get("paper", {})
                        title = p.get("title", "")
                        summary = p.get("summary", "")[:300]
                        pub_str = p.get("publishedAt", "")
                        paper_id = p.get("id", "")
                        url = f"https://huggingface.co/papers/{paper_id}" if paper_id else "https://huggingface.co/papers"

                        pub_dt = self.parse_datetime(pub_str)
                        if not self.is_within_24_hours(pub_dt):
                            continue

                        items.append({
                            "source_name": source["name"],
                            "url": url,
                            "title": title,
                            "summary": summary or title,
                            "published_date": pub_dt.isoformat()
                        })
        except Exception as e:
            logger.error(f"Error scraping Hugging Face news API: {e}")
        return items

    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape all 5 AI news sources concurrently with 24-hr freshness guarantee."""
        logger.info("Scraping 5 AI News sources with 24-hour freshness constraint...")
        all_news = []
        tasks = []

        for src in NEWS_SOURCES:
            if src["type"] == "rss":
                tasks.append(self.scrape_rss_source(src))
            elif src["type"] == "hn_api":
                tasks.append(self.scrape_hn_api(src))
            elif src["type"] == "hf_api":
                tasks.append(self.scrape_hf_api(src))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        now_iso = datetime.now(timezone.utc).isoformat()
        records = []

        for res in results:
            if isinstance(res, list):
                for item in res:
                    records.append({
                        "schemaVersion": "1.0",
                        "recordType": "NEWS",
                        "source": {
                            "name": item["source_name"],
                            "url": item["url"]
                        },
                        "content": {
                            "title": item["title"],
                            "summary": item["summary"],
                            "published_date": item["published_date"]
                        },
                        "collectedAt": now_iso
                    })

        logger.info(f"Successfully ingested {len(records)} 24-Hour Fresh News Entities.")
        return records
