"""
src/scrapers/paper_scraper.py - Research Papers & GitHub Metrics Scraper
GraphOne / FrontierAtlas Intelligence Graph Ingestion Pipeline
"""

import asyncio
import re
import xml.etree.ElementTree as ET
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import httpx

from src.scrapers.base_scraper import BaseScraper
from src.config import GITHUB_TOKEN

logger = logging.getLogger("PaperScraper")

class PaperScraper(BaseScraper):
    def __init__(self, target_count: int = 1000):
        super().__init__()
        self.target_count = target_count
        self.github_semaphore = asyncio.Semaphore(5)  # Specific rate limit semaphore for GitHub
        self._repo_cache: Dict[str, Optional[int]] = {}  # In-memory repository cache per run

        # Metrics Counters
        self.github_discovered = 0
        self.github_queried = 0
        self.github_cache_hits = 0
        self.github_successes = 0
        self.github_404s = 0
        self.github_rate_limits = 0
        self.github_stars_populated = 0
        self.github_stars_unavailable = 0

    @staticmethod
    def normalize_github_repo(url: str) -> Optional[Tuple[str, str]]:
        """
        Normalize arbitrary GitHub URL into canonical (owner, repo) tuple.
        Handles trailing slashes, .git extensions, subpaths, and query params.
        Example: https://github.com/OpenAI/SomeRepo/ -> ('OpenAI', 'SomeRepo')
        """
        if not url or "github.com" not in url:
            return None

        # Clean URL
        cleaned = url.strip()
        cleaned = re.sub(r'\.git$', '', cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.rstrip('/')

        # Extract owner/repo via regex
        match = re.search(r'github\.com/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)', cleaned)
        if match:
            owner = match.group(1)
            repo = match.group(2)
            # Filter out non-repo GitHub paths like /search, /topics, /orgs
            if owner.lower() in ["search", "topics", "orgs", "features", "pricing", "login", "signup"]:
                return None
            return (owner, repo)
        return None

    async def fetch_github_stars(self, github_url: str) -> Optional[int]:
        """
        Fetch dynamic GitHub star count with URL normalization, caching, rate-limit retries, and metrics.
        Never invents star counts; returns None if unavailable.
        """
        normalized = self.normalize_github_repo(github_url)
        if not normalized:
            return None

        owner, repo = normalized
        canonical_key = f"{owner.lower()}/{repo.lower()}"

        # Check in-memory cache first
        if canonical_key in self._repo_cache:
            self.github_cache_hits += 1
            return self._repo_cache[canonical_key]

        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        if GITHUB_TOKEN and GITHUB_TOKEN.strip():
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN.strip()}"

        async with self.github_semaphore:
            self.github_queried += 1
            for attempt in range(1, 3):
                try:
                    if self.client is None:
                        self.client = httpx.AsyncClient(timeout=10.0, follow_redirects=True, verify=False)

                    response = await self.client.get(api_url, headers=headers)

                    if response.status_code == 200:
                        data = response.json()
                        stars = data.get("stargazers_count")
                        self.github_successes += 1
                        self.github_stars_populated += 1
                        self._repo_cache[canonical_key] = stars
                        logger.info(f"GitHub Star Fetch SUCCESS: {owner}/{repo} -> {stars} stars")
                        return stars

                    elif response.status_code == 404:
                        self.github_404s += 1
                        self.github_stars_unavailable += 1
                        self._repo_cache[canonical_key] = None
                        logger.warning(f"GitHub Repository Not Found (404): {owner}/{repo}")
                        return None

                    elif response.status_code in [403, 429]:
                        self.github_rate_limits += 1
                        # Check rate limit reset header if available
                        reset_header = response.headers.get("x-ratelimit-reset")
                        retry_after = response.headers.get("retry-after")
                        
                        if retry_after:
                            wait_secs = float(retry_after)
                        else:
                            wait_secs = (2 ** attempt) + 0.5
                        
                        wait_secs = min(wait_secs, 0.5)
                        logger.warning(f"GitHub API Rate Limit ({response.status_code}) for {owner}/{repo}. Attempt {attempt}/2. Waiting {wait_secs:.1f}s.")
                        await asyncio.sleep(wait_secs)

                    else:
                        logger.warning(f"GitHub API HTTP {response.status_code} for {owner}/{repo}")
                        break

                except Exception as e:
                    logger.warning(f"GitHub API exception for {owner}/{repo}: {e}")
                    await asyncio.sleep(1.0)

            self.github_stars_unavailable += 1
            self._repo_cache[canonical_key] = None
            return None

    async def scrape_arxiv_papers(self, count: int = 1000) -> List[Dict[str, Any]]:
        """Scrape AI research papers from Arxiv API in concurrent batches."""
        papers = []
        batch_size = 200
        categories = ["cat:cs.AI", "cat:cs.LG", "cat:cs.CL", "cat:cs.CV", "cat:stat.ML"]
        query_str = "+OR+".join(categories)

        logger.info(f"Initiating bulk Arxiv harvest for target {count} papers...")

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=False) as client:
            tasks = []
            for start in range(0, count, batch_size):
                url = f"https://export.arxiv.org/api/query?search_query={query_str}&start={start}&max_results={batch_size}&sortBy=submittedDate&sortOrder=descending"
                tasks.append(client.get(url))

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for resp in responses:
                if isinstance(resp, Exception) or resp.status_code != 200:
                    continue

                try:
                    root = ET.fromstring(resp.text)
                    ns = {'atom': 'http://www.w3.org/2005/Atom'}
                    entries = root.findall('atom:entry', ns)

                    for entry in entries:
                        title_elem = entry.find('atom:title', ns)
                        title = title_elem.text.strip().replace('\n', ' ') if title_elem is not None else "Untitled Paper"

                        summary_elem = entry.find('atom:summary', ns)
                        summary = summary_elem.text.strip() if summary_elem is not None else ""

                        paper_id_elem = entry.find('atom:id', ns)
                        paper_url = paper_id_elem.text.strip() if paper_id_elem is not None else ""

                        pub_elem = entry.find('atom:published', ns)
                        pub_date_str = pub_elem.text.strip() if pub_elem is not None else ""
                        pub_date = self.parse_datetime(pub_date_str).isoformat()

                        authors = [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns) if a.find('atom:name', ns) is not None]

                        # Extract potential GitHub repository from abstract summary
                        github_match = re.search(r'https?://github\.com/[\w\-\.\/]+', summary)
                        github_url = github_match.group(0).rstrip(".,)") if github_match else None

                        if github_url:
                            self.github_discovered += 1

                        papers.append({
                            "title": title,
                            "authors": authors,
                            "summary": summary,
                            "paper_url": paper_url,
                            "github_url": github_url,
                            "published_date": pub_date
                        })
                except Exception as e:
                    logger.error(f"Error parsing Arxiv XML batch: {e}")

        logger.info(f"Harvested {len(papers)} Arxiv papers.")
        return papers

    async def scrape(self) -> List[Dict[str, Any]]:
        """Run paper scraping pipeline and enrich with GitHub stars."""
        raw_papers = await self.scrape_arxiv_papers(count=self.target_count)

        logger.info("Enriching papers with dynamic GitHub repository metrics...")
        now_iso = datetime.now(timezone.utc).isoformat()

        async def enrich_paper(paper: Dict[str, Any]) -> Dict[str, Any]:
            github_url = paper.get("github_url")
            stars = None
            if github_url:
                stars = await self.fetch_github_stars(github_url)

            return {
                "schemaVersion": "1.0",
                "recordType": "RESEARCH_PAPER",
                "source": {
                    "name": "Arxiv / Papers with Code",
                    "url": paper["paper_url"]
                },
                "content": {
                    "title": paper["title"],
                    "authors": paper["authors"],
                    "paper_url": paper["paper_url"],
                    "github_url": github_url,
                    "github_stars": stars,
                    "published_date": paper["published_date"]
                },
                "collectedAt": now_iso
            }

        tasks = [enrich_paper(p) for p in raw_papers]
        enriched_records = await asyncio.gather(*tasks)

        logger.info(f"Successfully constructed {len(enriched_records)} Research Paper Entities.")
        return enriched_records

    def get_metrics(self) -> Dict[str, Any]:
        """Return GitHub enrichment metrics summary dict."""
        return {
            "github_discovered": self.github_discovered,
            "github_queried": self.github_queried,
            "github_cache_hits": self.github_cache_hits,
            "github_successes": self.github_successes,
            "github_404s": self.github_404s,
            "github_rate_limits": self.github_rate_limits,
            "github_stars_populated": self.github_stars_populated,
            "github_stars_unavailable": self.github_stars_unavailable
        }
