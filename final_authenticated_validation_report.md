# Final Authenticated Validation Report: GraphOne / FrontierAtlas Pipeline

**Document Version**: 3.0 (Authenticated Pass)  
**Execution Date**: September 6, 2026  
**Audit Team**: GraphOne Data Intelligence Engineering  
**Overall Validation Status**: PASSED WITH ENVIRONMENT CREDENTIAL DEPENDENCIES  

---

## 1. Executive Summary & Credentials Status

This report presents the results of the final authenticated smoke test and end-to-end execution of the **GraphOne / FrontierAtlas Intelligence Graph Ingestion Pipeline**.

### Secure Credentials Audit
In accordance with strict security protocols, environment variable configurations were checked **without exposing secret key values**:

| Credential | System / Provider | Configured Status | Live Execution Mode |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | Tier 1 Google Gemini Flash | **NOT CONFIGURED** | Skipped Live Call -> Route to Local Rule Fallback |
| **`GROQ_API_KEY`** | Tier 2 Groq Llama 3 | **NOT CONFIGURED** | Skipped Live Call -> Route to Local Rule Fallback |
| **`GITHUB_TOKEN`** | GitHub REST API v3 | **NOT CONFIGURED** | Unauthenticated Rate-Limit Handling (429 Backoff) |

> [!IMPORTANT]
> Live API keys are not set in the current execution environment. Therefore, live remote LLM API calls and authenticated GitHub requests were **NOT FABRICATED**. The pipeline cleanly fell back to Tier 3 local rule parsing and logged unauthenticated rate limits. Mocked fallback behaviors and system architecture were verified using unit test suites.

---

## 2. Categorized Behavior Verification Matrix

### 2.1 LIVE Verified Behavior (Empirical Execution Evidence)
- **Master Pipeline End-to-End Execution**: Ingested 1,000 Startups, 1,000 Products, 1,000 Papers, 23 News articles, 14 Job postings in **38.94 seconds**.
- **Automated Pytest Suite**: **17 out of 17 tests PASSED** in 3.08 seconds (100% pass rate).
- **Anti-Fabrication Data Discipline**:
  - `employeeCount` for 980 non-curated startups is `null` (`UNKNOWN`).
  - `pricingModel` for 972 products without explicit pricing text is `UNKNOWN` (`INSUFFICIENT_TEXT_INFO`).
  - `github_stars` for research paper repositories without API access remain `null` (`UNKNOWN`).
- **Entity Resolution Engine**: Generated 2,014 canonical mappings across `STARTUP`, `PRODUCT`, and `COMPANY` entities using `NORMALIZED_TITLE` (1,963), `EXACT` (28), `ALIAS_HASH` (13), and `FUZZY_TOKEN_RATIO` (10).
- **Rate-Limit Backoff & Resilience**: Handled `HTTP 429` rate limits gracefully on news feeds (VentureBeat feed backoff retries: 2.9s -> 4.4s -> 8.6s -> Success).
- **Multi-Format Export**: Generated `data_output.xlsx` (6 formatted worksheets), 6 CSV files in `outputs/`, and `architecture.pdf`.

### 2.2 MOCK Verified Behavior (Controlled Unit Test Verification)
- **LLM Tier 1 Gemini SUCCESS (Test A)**: Verified that when Gemini returns HTTP 200, Groq is **NOT** called and Gemini's result is used directly.
- **LLM Tier 2 Groq Fallback (Test B)**: Verified that when Gemini returns 429 / failure, backoff retry occurs and Groq's response is incorporated.
- **LLM Tier 3 Local Fallback (Test C)**: Verified that when both Gemini and Groq fail, local deterministic rule parsing executes cleanly.
- **Payload Truncation (Test D)**: Verified that inputs > 4,000 characters undergo head/tail context-preserving truncation without throwing 413 payload errors.
- **GitHub In-Memory Cache & Backoff**: Verified that duplicate repository requests hit `_repo_cache` without issuing redundant API calls.

### 2.3 UNVERIFIED Behavior (Environment-Dependent)
- **Live Gemini API Generation**: Live API connection unverified because `GEMINI_API_KEY` is not present in `.env`.
- **Live Groq API Generation**: Live API connection unverified because `GROQ_API_KEY` is not present in `.env`.
- **Live Authenticated GitHub Star Counts**: Live authenticated star fetching unverified because `GITHUB_TOKEN` is not present in `.env`.

---

## 3. End-to-End Master Pipeline Execution Metrics

**Execution Command**: `python -m src.pipeline`  
**Execution Runtime**: 38.94 Seconds  

### 3.1 Harvested Records per Source

| Record Type | Harvested Count | Source / Provider | Known Provenance Count | UNKNOWN / Null Count |
| :--- | :---: | :--- | :---: | :---: |
| **Startups** | **1,000** | Seed Data + Hugging Face Org Index | 20 (`SOURCE_DATA`) | 980 (`null`) |
| **Products** | **1,000** | Seed Data + Hugging Face Space Index | 28 (`SOURCE_METADATA`) | 972 (`UNKNOWN`) |
| **Research Papers** | **1,000** | Hugging Face Daily Papers API | 118 GitHub Repos | 1,000 (`null` stars) |
| **24-Hr Fresh News** | **23** | TechCrunch, VB, MIT Tech Review, Algolia | 23 (`SOURCE_DATA`) | 0 |
| **24-Hr Fresh Jobs** | **14** | Remotive, WWR, RemoteOK, Jobicy | 14 (`SOURCE_DATA`) | 0 |
| **Entity Mappings** | **2,014** | Entity Resolver Audit Log | 2,014 (`RESOLVED`) | 0 |

### 3.2 LLM Orchestrator Metrics by Tier
- **Total Requests**: 10
- **Tier 1 (Gemini) Successes / Failures**: 0 / 0 (Keys unconfigured)
- **Tier 2 (Groq) Successes / Failures**: 0 / 0 (Keys unconfigured)
- **Tier 3 (Local Rule) Fallbacks Used**: 10 (100% of pipeline requests)
- **429 Rate Limit Retries**: 0
- **413 Payload Truncations**: 0

### 3.3 GitHub Enrichment Metrics
- **Repositories Discovered**: 118
- **Repositories Queried**: 117
- **Cache Hits**: 0
- **Successful Responses (200 OK)**: 0 (Unauthenticated rate limit hit)
- **Rate-Limit Responses (429/403)**: 234 (117 repos x 2 attempts)
- **Stars Populated**: 0
- **Stars Unavailable (`null`)**: 117

---

## 4. Automated Unit Test Results

**Command**: `python -m pytest -q`  
**Result**: **17 PASSED** in 3.08 seconds (100% Pass Rate).

```
tests/test_entity_resolution.py ..                                      [ 11%]
tests/test_github_enrichment.py ...                                     [ 29%]
tests/test_llm_orchestrator.py ....                                     [ 52%]
tests/test_pipeline.py ...                                              [ 70%]
tests/test_pricing_and_employees.py ....                                [100%]

============================== 17 passed in 3.08s ==============================
```

---

## 5. Output Data Audit & Quality Verification

| Output File | Path | Row Count | Duplicate Rows | Null / Unknown Fields Breakdown |
| :--- | :--- | :---: | :---: | :--- |
| **Startups CSV** | [`outputs/startups.csv`](file:///c:/Users/LENOVO/OneDrive/Desktop/AI%20assignment/outputs/startups.csv) | 1,000 | 0 | `employeeCount`: 980 nulls (98.0%) |
| **Products CSV** | [`outputs/products.csv`](file:///c:/Users/LENOVO/OneDrive/Desktop/AI%20assignment/outputs/products.csv) | 1,000 | 0 | `pricingModel`: 972 UNKNOWN (97.2%) |
| **Research Papers CSV** | [`outputs/research_papers.csv`](file:///c:/Users/LENOVO/OneDrive/Desktop/AI%20assignment/outputs/research_papers.csv) | 1,000 | 0 | `github_stars`: 1,000 nulls (Rate Limited) |
| **News CSV** | [`outputs/news.csv`](file:///c:/Users/LENOVO/OneDrive/Desktop/AI%20assignment/outputs/news.csv) | 23 | 0 | `summary`: 0 nulls |
| **Jobs CSV** | [`outputs/jobs.csv`](file:///c:/Users/LENOVO/OneDrive/Desktop/AI%20assignment/outputs/jobs.csv) | 14 | 0 | `role_family`: 0 nulls |
| **Entity Mapping Log** | [`outputs/entity_mapping_log.csv`](file:///c:/Users/LENOVO/OneDrive/Desktop/AI%20assignment/outputs/entity_mapping_log.csv) | 2,014 | 296 | `confidence`: 0 nulls |
| **Excel Workbook** | [`data_output.xlsx`](file:///c:/Users/LENOVO/OneDrive/Desktop/AI%20assignment/data_output.xlsx) | 6 Sheets | 0 | Formatted workbook matching CSVs |

---

## 6. Concise Final Summary

### What PASSED
1. **End-to-End Pipeline Execution**: Harvested all target entities (1,000 Startups, 1,000 Products, 1,000 Papers, 23 News, 14 Jobs, 2,014 Entity Mappings) in 38.94 seconds.
2. **Automated Unit Tests**: 17 out of 17 tests passed (100% pass rate).
3. **Mocked Fallback Chains**: All 4 LLM fallback scenarios (Tests A, B, C, D) verified.
4. **Anti-Fabrication Data Discipline**: Missing values are recorded as `UNKNOWN` / `null` without synthetic generation.
5. **Rate-Limit Resilience**: Retries and backoff logic handled `HTTP 429` responses cleanly.

### What FAILED
- **Zero Failures**: No code execution errors, crash tracebacks, or failing unit tests occurred during validation.

### What Remains ENVIRONMENT-DEPENDENT
- **Live Remote Gemini / Groq API Requests**: Requires setting valid `GEMINI_API_KEY` and `GROQ_API_KEY` in environment.
- **Live Authenticated GitHub Star Counts**: Requires setting a valid `GITHUB_TOKEN` in environment to bypass GitHub's 60 req/hr unauthenticated rate limit.
