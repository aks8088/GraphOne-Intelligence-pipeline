"""
src/scrapers/job_scraper.py - 24-Hour Fresh AI Job Signal Scraper
GraphOne / FrontierAtlas Intelligence Graph Ingestion Pipeline
"""

import asyncio
import xml.etree.ElementTree as ET
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
import httpx

from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger("JobScraper")

JOB_SOURCES = [
    {"name": "RemoteOK AI Jobs", "type": "remoteok", "url": "https://remoteok.com/api"},
    {"name": "Jobicy Dev Jobs", "type": "jobicy", "url": "https://jobicy.com/api/v2/remote-jobs?count=50&industry=engineering"},
    {"name": "Remotive Tech Jobs", "type": "remotive", "url": "https://remotive.com/api/remote-jobs?category=software-dev"},
    {"name": "Hacker News Hiring", "type": "hn_hiring", "url": "https://hn.algolia.com/api/v1/search_by_date?tags=story&query=hiring"},
    {"name": "WeWorkRemotely Dev RSS", "type": "wwr_rss", "url": "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"}
]

class JobScraper(BaseScraper):
    def __init__(self):
        super().__init__()

    @staticmethod
    def infer_role_family(title: str) -> str:
        """Infer functional role family from job title."""
        t = title.lower()
        if "research" in t or "scientist" in t or "phd" in t:
            return "Research"
        elif "data" in t or "ml" in t or "machine learning" in t or "ai" in t:
            return "Engineering (AI/ML)"
        elif "product" in t or "pm" in t:
            return "Product"
        elif "design" in t or "ui" in t or "ux" in t:
            return "Design"
        else:
            return "Engineering"

    async def scrape_remoteok(self, source: Dict[str, str]) -> List[Dict[str, Any]]:
        items = []
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
                resp = await client.get(source["url"], headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    jobs = resp.json()
                    for job in jobs[1:]:  # First item is metadata header
                        if not isinstance(job, dict):
                            continue
                        company = job.get("company", "Tech Startup")
                        position = job.get("position", "Software Engineer")
                        url = job.get("url") or f"https://remoteok.com/remote-jobs/{job.get('id')}"
                        date_str = job.get("date", "")

                        pub_dt = self.parse_datetime(date_str)
                        if not self.is_within_24_hours(pub_dt):
                            continue

                        items.append({
                            "source_name": source["name"],
                            "url": url,
                            "company": company,
                            "title": position,
                            "date": pub_dt.isoformat(),
                            "is_remote": True,
                            "role_family": self.infer_role_family(position)
                        })
        except Exception as e:
            logger.error(f"Error scraping RemoteOK: {e}")
        return items

    async def scrape_jobicy(self, source: Dict[str, str]) -> List[Dict[str, Any]]:
        items = []
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
                resp = await client.get(source["url"], headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    jobs = resp.json().get("jobs", [])
                    for job in jobs:
                        company = job.get("companyName", "Unknown Company")
                        title = job.get("jobTitle", "Software Engineer")
                        url = job.get("url", source["url"])
                        date_str = job.get("pubDate", "")

                        pub_dt = self.parse_datetime(date_str)
                        if not self.is_within_24_hours(pub_dt):
                            continue

                        items.append({
                            "source_name": source["name"],
                            "url": url,
                            "company": company,
                            "title": title,
                            "date": pub_dt.isoformat(),
                            "is_remote": True,
                            "role_family": self.infer_role_family(title)
                        })
        except Exception as e:
            logger.error(f"Error scraping Jobicy: {e}")
        return items

    async def scrape_remotive(self, source: Dict[str, str]) -> List[Dict[str, Any]]:
        items = []
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
                resp = await client.get(source["url"], headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    jobs = resp.json().get("jobs", [])
                    for job in jobs:
                        company = job.get("company_name", "AI Company")
                        title = job.get("title", "Developer")
                        url = job.get("url", source["url"])
                        date_str = job.get("publication_date", "")

                        pub_dt = self.parse_datetime(date_str)
                        if not self.is_within_24_hours(pub_dt):
                            continue

                        items.append({
                            "source_name": source["name"],
                            "url": url,
                            "company": company,
                            "title": title,
                            "date": pub_dt.isoformat(),
                            "is_remote": True,
                            "role_family": self.infer_role_family(title)
                        })
        except Exception as e:
            logger.error(f"Error scraping Remotive: {e}")
        return items

    async def scrape_hn_hiring(self, source: Dict[str, str]) -> List[Dict[str, Any]]:
        items = []
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
                resp = await client.get(source["url"], headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    hits = resp.json().get("hits", [])
                    for hit in hits:
                        title = hit.get("title", "")
                        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                        created_at = hit.get("created_at", "")

                        pub_dt = self.parse_datetime(created_at)
                        if not self.is_within_24_hours(pub_dt):
                            continue

                        company = "Hacker News Startup"
                        if "is hiring" in title.lower():
                            company = title.split("is hiring")[0].strip()

                        items.append({
                            "source_name": source["name"],
                            "url": url,
                            "company": company,
                            "title": title[:100],
                            "date": pub_dt.isoformat(),
                            "is_remote": "remote" in title.lower(),
                            "role_family": self.infer_role_family(title)
                        })
        except Exception as e:
            logger.error(f"Error scraping HN Hiring: {e}")
        return items

    async def scrape_wwr_rss(self, source: Dict[str, str]) -> List[Dict[str, Any]]:
        items = []
        xml_data = await self.fetch(source["url"])
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

                raw_title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Software Engineer"
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else source["url"]
                pub_str = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""

                pub_dt = self.parse_datetime(pub_str)
                if not self.is_within_24_hours(pub_dt):
                    continue

                company = "WeWorkRemotely Company"
                title = raw_title
                if ":" in raw_title:
                    parts = raw_title.split(":", 1)
                    company = parts[0].strip()
                    title = parts[1].strip()

                items.append({
                    "source_name": source["name"],
                    "url": link,
                    "company": company,
                    "title": title,
                    "date": pub_dt.isoformat(),
                    "is_remote": True,
                    "role_family": self.infer_role_family(title)
                })
        except Exception as e:
            logger.error(f"Error parsing WWR RSS: {e}")
        return items

    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape all 5 AI job boards concurrently with 24-hr freshness constraint."""
        logger.info("Scraping 5 AI Job Boards with 24-hour freshness constraint...")
        tasks = [
            self.scrape_remoteok(JOB_SOURCES[0]),
            self.scrape_jobicy(JOB_SOURCES[1]),
            self.scrape_remotive(JOB_SOURCES[2]),
            self.scrape_hn_hiring(JOB_SOURCES[3]),
            self.scrape_wwr_rss(JOB_SOURCES[4])
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        now_iso = datetime.now(timezone.utc).isoformat()
        records = []

        for res in results:
            if isinstance(res, list):
                for item in res:
                    records.append({
                        "schemaVersion": "1.0",
                        "recordType": "JOB",
                        "source": {
                            "name": item["source_name"],
                            "url": item["url"]
                        },
                        "content": {
                            "company": item["company"],
                            "title": item["title"],
                            "date": item["date"],
                            "is_remote": item["is_remote"],
                            "role_family": item["role_family"]
                        },
                        "collectedAt": now_iso
                    })

        logger.info(f"Successfully ingested {len(records)} 24-Hour Fresh Job Entities.")
        return records
