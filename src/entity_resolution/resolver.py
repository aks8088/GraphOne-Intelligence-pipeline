"""
src/entity_resolution/resolver.py - Deterministic Entity Resolution Engine
GraphOne / FrontierAtlas Intelligence Graph Ingestion Pipeline
"""

import re
import logging
from typing import Tuple, List, Dict, Any
from rapidfuzz import fuzz

from src.config import SEED_AI_ENTITIES

logger = logging.getLogger("EntityResolver")

# Common Alias Map for known AI company string variations
ALIAS_MAP = {
    "open ai": "OpenAI",
    "openai inc": "OpenAI",
    "openai corp": "OpenAI",
    "openai, inc.": "OpenAI",
    "openai llc": "OpenAI",
    "anthropic pb": "Anthropic",
    "anthropic pbc": "Anthropic",
    "anthropic inc": "Anthropic",
    "cohere ai": "Cohere",
    "cohere inc": "Cohere",
    "mistralai": "Mistral AI",
    "mistral.ai": "Mistral AI",
    "huggingface": "Hugging Face",
    "huggingface inc": "Hugging Face",
    "scaleai": "Scale AI",
    "scale ai inc": "Scale AI",
    "perplexity": "Perplexity AI",
    "perplexity.ai": "Perplexity AI",
    "stability.ai": "Stability AI",
    "stabilityai": "Stability AI",
    "langchain inc": "LangChain",
    "pinecone.io": "Pinecone",
    "together.ai": "Together AI",
    "runwayml": "Runway",
    "eleven labs": "ElevenLabs",
    "character ai": "Character.AI",
    "character.ai inc": "Character.AI"
}

# Legal entity suffixes to remove during normalization
LEGAL_SUFFIXES = r'\b(inc|incorporated|corp|corporation|llc|ltd|limited|co|pbc|pb|group|labs|tech|technology|ai)\b'

class EntityResolver:
    def __init__(self, seed_entities: List[str] = SEED_AI_ENTITIES):
        self.seed_entities = seed_entities
        self.seed_lookup = {e.lower(): e for e in seed_entities}
        self.mapping_log: List[Dict[str, Any]] = []

    @staticmethod
    def normalize_string(text: str) -> str:
        """Strip legal suffixes, punctuation, and return lowercased clean string."""
        if not text:
            return ""
        # Lowercase and clean characters
        clean = text.lower().replace(".", " ").replace(",", " ").replace("-", " ")
        clean = re.sub(LEGAL_SUFFIXES, '', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def resolve(self, raw_name: str, entity_type: str = "STARTUP") -> str:
        """
        Canonicalize entity name and append to resolution mapping log.
        Returns canonical entity string.
        """
        if not raw_name or not raw_name.strip():
            return "Unknown Entity"

        raw_clean = raw_name.strip()
        normalized = self.normalize_string(raw_clean)

        # 1. Exact Seed Match
        if normalized in self.seed_lookup:
            canonical = self.seed_lookup[normalized]
            self._log_mapping(raw_clean, canonical, entity_type, 1.00, "EXACT")
            return canonical

        # 2. Alias Hash Lookup
        if normalized in ALIAS_MAP:
            canonical = ALIAS_MAP[normalized]
            self._log_mapping(raw_clean, canonical, entity_type, 1.00, "ALIAS_HASH")
            return canonical

        # 3. Fuzzy Matching against Seed Entities using RapidFuzz
        best_match = None
        best_score = 0.0

        for seed in self.seed_entities:
            score = fuzz.token_sort_ratio(normalized, self.normalize_string(seed))
            if score > best_score:
                best_score = score
                best_match = seed

        if best_match and best_score >= 82.0:
            confidence = round(best_score / 100.0, 2)
            self._log_mapping(raw_clean, best_match, entity_type, confidence, "FUZZY_TOKEN_RATIO")
            return best_match

        # 4. Standard Title Case Canonicalization Fallback
        canonical = raw_clean.replace("-", " ").replace("_", " ").title()
        canonical = re.sub(r'\b(Inc|Corp|Llc|Ltd|Co)\b', '', canonical, flags=re.IGNORECASE).strip(" .,")
        canonical = re.sub(r'\s+', ' ', canonical).strip()
        self._log_mapping(raw_clean, canonical, entity_type, 0.90, "NORMALIZED_TITLE")
        return canonical

    def _log_mapping(self, raw: str, canonical: str, entity_type: str, confidence: float, method: str):
        """Append mapping entry to audit log."""
        self.mapping_log.append({
            "rawName": raw,
            "canonicalName": canonical,
            "entityType": entity_type,
            "confidence": confidence,
            "matchMethod": method
        })

    def get_mapping_log(self) -> List[Dict[str, Any]]:
        """Return full Entity Mapping Log."""
        return self.mapping_log
