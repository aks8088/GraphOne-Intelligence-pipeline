"""
src/pipeline.py - Master Pipeline Coordinator
GraphOne / FrontierAtlas Intelligence Graph Ingestion Pipeline
"""

import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from src.scrapers.startup_scraper import StartupScraper
from src.scrapers.product_scraper import ProductScraper
from src.scrapers.paper_scraper import PaperScraper
from src.scrapers.news_scraper import NewsScraper
from src.scrapers.job_scraper import JobScraper
from src.llm.llm_orchestrator import LLMOrchestrator
from src.entity_resolution.resolver import EntityResolver
from src.exporters.excel_exporter import DataExporter
from src.exporters.pdf_generator import generate_architecture_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("MasterPipeline")

class MasterPipeline:
    def __init__(self, target_startups: int = 1000, target_products: int = 1000, target_papers: int = 1000):
        self.target_startups = target_startups
        self.target_products = target_products
        self.target_papers = target_papers
        self.llm = LLMOrchestrator()
        self.resolver = EntityResolver()

    async def run(self):
        """Execute the end-to-end ingestion, entity resolution, LLM enrichment, and export pipeline."""
        start_time = time.time()
        logger.info("==========================================================================")
        logger.info("STARTING GRAPHONE / FRONTIERATLAS INTELLIGENCE GRAPH INGESTION PIPELINE")
        logger.info("==========================================================================")

        # Step 1: Initialize Scrapers with LLM Orchestrator
        startup_scraper = StartupScraper(target_count=self.target_startups)
        product_scraper = ProductScraper(target_count=self.target_products, llm=self.llm)
        paper_scraper = PaperScraper(target_count=self.target_papers)
        news_scraper = NewsScraper()
        job_scraper = JobScraper()

        # Step 2: Concurrent Data Harvesting across Phase I & Phase II Verticals
        logger.info("Executing concurrent data harvesting for Startups, Products, Papers, News, Jobs...")
        
        results = await asyncio.gather(
            startup_scraper.scrape(),
            product_scraper.scrape(),
            paper_scraper.scrape(),
            news_scraper.scrape(),
            job_scraper.scrape(),
            return_exceptions=True
        )

        startups, products, papers, news, jobs = results

        if isinstance(startups, Exception):
            logger.error(f"Startup scraper failed: {startups}")
            startups = []
        if isinstance(products, Exception):
            logger.error(f"Product scraper failed: {products}")
            products = []
        if isinstance(papers, Exception):
            logger.error(f"Paper scraper failed: {papers}")
            papers = []
        if isinstance(news, Exception):
            logger.error(f"News scraper failed: {news}")
            news = []
        if isinstance(jobs, Exception):
            logger.error(f"Job scraper failed: {jobs}")
            jobs = []

        logger.info(f"Scrape Complete -> Startups: {len(startups)}, Products: {len(products)}, Papers: {len(papers)}, News: {len(news)}, Jobs: {len(jobs)}")

        # Step 3: LLM Semantic Normalization & Enrichment (Selective LLM Invocation)
        logger.info("Executing LLM Orchestrator for semi-structured text enrichment...")
        for p in products[:10]:  # Run LLM classification on a subset of products requiring semantic pricing classification
            startup_name = p["content"]["startupName"]
            desc = f"AI Product {p['content'].get('productName', '')} created by {startup_name}."
            res = await self.llm.classify_pricing(desc)
            if res.get("pricingModel") and res.get("pricingModel") != "UNKNOWN":
                p["content"]["pricingModel"] = res["pricingModel"]
                p["content"]["pricingMethod"] = res.get("method", "LLM")

        # Step 4: Phase IV - Deterministic Entity Resolution & Canonicalization
        logger.info("Executing Deterministic Entity Resolution & Canonicalization...")
        
        # Canonicalize Startup Names
        for record in startups:
            raw = record["content"]["entityName"]
            record["content"]["entityName"] = self.resolver.resolve(raw, entity_type="STARTUP")

        # Canonicalize Product Startup Names
        for record in products:
            raw = record["content"]["startupName"]
            record["content"]["startupName"] = self.resolver.resolve(raw, entity_type="PRODUCT")

        # Canonicalize Job Company Names
        for record in jobs:
            raw = record["content"]["company"]
            record["content"]["company"] = self.resolver.resolve(raw, entity_type="COMPANY")

        mapping_log = self.resolver.get_mapping_log()
        logger.info(f"Entity Resolution Complete. Mapping Log contains {len(mapping_log)} entries.")

        # Step 5: Export to Excel (6 Tabs) and CSV Files
        datasets = {
            "startups": startups,
            "products": products,
            "papers": papers,
            "news": news,
            "jobs": jobs
        }
        DataExporter.export(datasets, mapping_log)

        # Step 6: Phase VI - Generate Architecture PDF & Markdown
        generate_architecture_pdf()

        elapsed = time.time() - start_time
        
        # Extract Component Metrics
        llm_metrics = self.llm.get_metrics()
        gh_metrics = paper_scraper.get_metrics()
        prod_metrics = product_scraper.get_metrics()
        startup_metrics = startup_scraper.get_metrics()

        logger.info("==========================================================================")
        logger.info(f"PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f} SECONDS")
        logger.info("==========================================================================")
        logger.info(f"  HARVESTED ENTITY COUNTS:")
        logger.info(f"    - Startups: {len(startups)} (Known Employees: {startup_metrics['employee_count_known']}, Unknown: {startup_metrics['employee_count_unknown']})")
        logger.info(f"    - Products: {len(products)} (Known Pricing: {prod_metrics['pricing_known_count']}, Unknown: {prod_metrics['pricing_unknown_count']})")
        logger.info(f"    - Research Papers: {len(papers)}")
        logger.info(f"    - 24-Hr Fresh Jobs: {len(jobs)}")
        logger.info(f"    - 24-Hr Fresh News: {len(news)}")
        logger.info(f"    - Entity Resolution Mappings: {len(mapping_log)}")
        logger.info("--------------------------------------------------------------------------")
        logger.info(f"  LLM ORCHESTRATION METRICS:")
        logger.info(f"    - Total Requests: {llm_metrics['total_llm_requests']}")
        if llm_metrics['total_llm_requests'] == 0:
            logger.info("    - Status: 0 LLM API calls (API keys not configured or unneeded)")
        else:
            logger.info(f"    - Gemini Successes: {llm_metrics['gemini_successes']} | Failures: {llm_metrics['gemini_failures']}")
            logger.info(f"    - Groq Successes: {llm_metrics['groq_successes']} | Failures: {llm_metrics['groq_failures']}")
            logger.info(f"    - Local Fallbacks Used: {llm_metrics['local_fallback_count']}")
            logger.info(f"    - 429 Retries: {llm_metrics['retries_429']} | 413 Truncations: {llm_metrics['truncations_413']}")
        logger.info("--------------------------------------------------------------------------")
        logger.info(f"  GITHUB STAR ENRICHMENT METRICS:")
        logger.info(f"    - Discovered: {gh_metrics['github_discovered']} | Queried: {gh_metrics['github_queried']} | Cache Hits: {gh_metrics['github_cache_hits']}")
        logger.info(f"    - Successes: {gh_metrics['github_successes']} | 404s: {gh_metrics['github_404s']} | Rate Limits: {gh_metrics['github_rate_limits']}")
        logger.info(f"    - Stars Populated: {gh_metrics['github_stars_populated']} | Stars Unavailable: {gh_metrics['github_stars_unavailable']}")
        logger.info("==========================================================================")

        return {
            "status": "completed",
            "startups": len(startups),
            "products": len(products),
            "papers": len(papers),
            "news": len(news),
            "jobs": len(jobs),
            "entity_mappings": len(mapping_log),
            "runtime_seconds": round(elapsed, 2),
            "llm_metrics": llm_metrics,
            "github_metrics": gh_metrics,
            "startup_metrics": startup_metrics,
            "product_metrics": prod_metrics
        }

if __name__ == "__main__":
    pipeline = MasterPipeline(target_startups=1000, target_products=1000, target_papers=1000)
    asyncio.run(pipeline.run())
