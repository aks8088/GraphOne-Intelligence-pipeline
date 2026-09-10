"""
src/config.py - Core Configuration & Schema Definitions
GraphOne / FrontierAtlas Intelligence Graph Ingestion Pipeline
"""

import os
from pathlib import Path
from typing import Dict, Any

# Base Directories
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EXCEL_OUTPUT_PATH = BASE_DIR / "data_output.xlsx"
PDF_OUTPUT_PATH = BASE_DIR / "architecture.pdf"
MARKDOWN_ARCH_PATH = BASE_DIR / "architecture.md"

# API Keys (Loaded from environment variables with safe fallbacks)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Concurrency & Network Limits
MAX_CONCURRENT_REQUESTS = 20
DEFAULT_TIMEOUT = 15.0
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0

# Freshness Cutoff (24 Hours)
FRESHNESS_HOURS = 24

# Seed List of 50 Known AI Canonical Entities (Phase IV: Deterministic Entity Resolution)
SEED_AI_ENTITIES = [
    "OpenAI", "Anthropic", "Cohere", "Mistral AI", "Hugging Face",
    "Scale AI", "Midjourney", "Perplexity AI", "Stability AI", "Databricks",
    "LangChain", "Pinecone", "Weaviate", "Qdrant", "Together AI",
    "Anyscale", "Runway", "ElevenLabs", "Harvey", "Character.AI",
    "Replit", "Cursor", "Jasper", "Copy.ai", "SambaNova",
    "Groq", "Cerebras", "Modular", "DeepL", "Inflection AI",
    "Chai", "Synthesia", "HeyGen", "Descript", "Voiceflow",
    "LlamaIndex", "ChromaDB", "Unstructured", "Fixie", "Adept AI",
    "Imbue", "Sakana AI", "Pika", "Ideogram", "Suno",
    "Udio", "Luma AI", "Cognition AI", "Kling AI", "MiniMax"
]

# Entity Schema Prototypes (Exact Schema Specifications)
SCHEMAS = {
    "STARTUP": {
        "schemaVersion": "1.0",
        "recordType": "STARTUP",
        "source": {"name": "", "url": ""},
        "content": {
            "entityName": "",
            "data": {"employeeCount": None}
        },
        "collectedAt": ""
    },
    "PRODUCT": {
        "schemaVersion": "1.0",
        "recordType": "PRODUCT",
        "source": {"name": "", "url": ""},
        "content": {
            "startupName": "",
            "pricingModel": "UNKNOWN"  # FREE, FREEMIUM, PAID, ENTERPRISE, UNKNOWN
        },
        "collectedAt": ""
    },
    "RESEARCH_PAPER": {
        "schemaVersion": "1.0",
        "recordType": "RESEARCH_PAPER",
        "source": {"name": "", "url": ""},
        "content": {
            "title": "",
            "authors": [],
            "paper_url": "",
            "github_url": None,
            "github_stars": None,
            "published_date": ""
        },
        "collectedAt": ""
    },
    "JOB": {
        "schemaVersion": "1.0",
        "recordType": "JOB",
        "source": {"name": "", "url": ""},
        "content": {
            "company": "",
            "title": "",
            "date": "",
            "is_remote": True,
            "role_family": "Engineering"
        },
        "collectedAt": ""
    },
    "NEWS": {
        "schemaVersion": "1.0",
        "recordType": "NEWS",
        "source": {"name": "", "url": ""},
        "content": {
            "title": "",
            "summary": "",
            "published_date": ""
        },
        "collectedAt": ""
    }
}
