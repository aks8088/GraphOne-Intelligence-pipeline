# GraphOne / FrontierAtlas Intelligence Graph Ingestion Pipeline & Web API

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Executive Summary
**GraphOne / FrontierAtlas** is engineering the global Intelligence Graph for the artificial intelligence and venture ecosystem. This repository contains the complete, production-grade asynchronous ingestion pipeline and FastAPI web application designed for continuous ingestion, normalization, entity resolution, provenance tracking, and RESTful API access across startups, products, research papers (with dynamic GitHub metrics), AI job postings, and real-time news signals.

---

## Deployment Architecture

```
Browser / API Client / Interviewer Demonstration
                      │
                      ▼
         FastAPI Application (app.py)
                      │
                      ▼
   Existing GraphOne Pipeline (src/pipeline.py)
                      │
     ┌────────────────┼────────────────┐
     ▼                ▼                ▼
Data Acquisition   LLM Multi-Tier   GitHub API
 (Scrapers)         Enrichment      Enrichment
                      │
                      ▼
            Validation & Provenance
                      │
                      ▼
        Entity Resolution Engine
                      │
                      ▼
        CSV / Excel / PDF Exports
```

---

## Data Provenance & Anti-Fabrication Principles

- **No Synthetic Attributes**: Attributes such as product pricing models and startup employee counts are NEVER generated using round-robin index formulas, hashes, or arbitrary heuristics.
- **Explicit Unknown Values**: If source metadata does not provide pricing or employee counts, fields are explicitly set to `UNKNOWN` or `null`. Honest missing values are preferred over fabricated metrics.
- **Provenance Tracking**: Every derived attribute tracks extraction method and provenance (`SOURCE_METADATA`, `DETERMINISTIC_TEXT`, `LLM_GEMINI`, `LLM_GROQ`, `UNKNOWN`).

---

## Deliverables Summary

| Deliverable | File Path | Description |
| :--- | :--- | :--- |
| **FastAPI App** | [`app.py`](file:///c:/Users/LENOVO/OneDrive/Desktop/AI%20assignment/app.py) | Production Web API entry point serving pipeline control, status, & output downloads |
| **Excel Output (6 Tabs)** | [`data_output.xlsx`](file:///c:/Users/LENOVO/OneDrive/Desktop/AI%20assignment/data_output.xlsx) | Multi-tab formatted workbook with Startups, Products, Papers, Jobs, News, and Mapping Log |
| **CSV Datasets** | [`outputs/`](file:///c:/Users/LENOVO/OneDrive/Desktop/AI%20assignment/outputs/) | Individual CSV files for each entity type and audit log |
| **PDF Architecture Doc** | [`architecture.pdf`](file:///c:/Users/LENOVO/OneDrive/Desktop/AI%20assignment/architecture.pdf) | 3-Page executive technical architecture report (ReportLab) |
| **Verification Report** | [`final_authenticated_validation_report.md`](file:///c:/Users/LENOVO/OneDrive/Desktop/AI%20assignment/final_authenticated_validation_report.md) | Empirical forensic verification report |
| **Deployment Report** | [`deployment_verification_report.md`](file:///c:/Users/LENOVO/OneDrive/Desktop/AI%20assignment/deployment_verification_report.md) | Web API & Docker deployment verification audit |
| **Unit Test Suite** | [`tests/`](file:///c:/Users/LENOVO/OneDrive/Desktop/AI%20assignment/tests/) | 27 automated unit tests covering LLM, GitHub, Pricing, Employees, Entity Resolution, & API |

---

## Quick Start & Local Setup

### Prerequisites
- Python 3.10 or higher
- `pip` package manager
- Docker (optional, for containerized deployment)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables (Recommended)
Copy `.env.example` to `.env` and set credentials:
```bash
cp .env.example .env
```

Configure keys in `.env`:
```env
GEMINI_API_KEY="your_gemini_api_key"
GROQ_API_KEY="your_groq_api_key"
GITHUB_TOKEN="your_github_personal_access_token"
PORT=8000
```
*(Note: If API keys are unconfigured, the pipeline gracefully defaults to local rule classification and public APIs without failing).*

### 3. Run Automated Unit Tests
```bash
python -m pytest -q
```

### 4. Execute CLI Master Pipeline
```bash
python -m src.pipeline
```

---

## Deployment & FastAPI Web API

### 1. Starting FastAPI Web Server Locally
```bash
uvicorn app:app --reload --port 8000
```

Access the application in your browser:
- **Root Welcome Endpoint**: `http://localhost:8000/`
- **Health Check**: `http://localhost:8000/health`
- **Interactive Swagger Documentation**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

---

### 2. Interactive Swagger Demonstration Flow (`/docs`)

An interviewer can interact with the system entirely via Swagger UI:

1. **Check System Health**:
   - `GET /health` -> Returns `{"status": "healthy", "service": "GraphOne Intelligence Pipeline"}`

2. **Trigger Demo Ingestion Run (~5 seconds)**:
   - `POST /run` with request body:
     ```json
     {
       "mode": "demo"
     }
     ```
   - Response: `{"status": "started", "run_id": "a1b2c3d4", "mode": "demo"}`

3. **Check Live Run Status**:
   - `GET /status` -> Returns `{"status": "running", "elapsed_seconds": 2.4}` or `{"status": "completed", "runtime_seconds": 5.12}`

4. **Query Ingestion Results**:
   - `GET /results` -> Returns summary metrics of startups, products, papers, news, jobs, and entity mappings.

5. **Download Exported Artifacts**:
   - `GET /results/excel` -> Download formatted Excel workbook (`data_output.xlsx`)
   - `GET /results/pdf` -> Download 3-page Architecture PDF (`architecture.pdf`)
   - `GET /results/startups` -> Download Startups CSV (`outputs/startups.csv`)
   - `GET /results/products` -> Download Products CSV (`outputs/products.csv`)
   - `GET /results/papers` -> Download Research Papers CSV (`outputs/research_papers.csv`)

---

### 3. Execution Modes

- **Demo Mode (`POST /run {"mode": "demo"}`)**: Runs a lightweight, safe dataset (10 startups, 10 products, 10 papers, fresh news & jobs) designed for quick 5-second interviewer live demonstrations.
- **Full Mode (`POST /run {"mode": "full"}`)**: Executes the complete ingestion pipeline (1,000 startups, 1,000 products, 1,000 papers). Runs asynchronously in the background.
- **Concurrency Control**: Prevents duplicate execution. If a run is currently active, `POST /run` returns `HTTP 409 Conflict` with `status: "already_running"`.

---

### 4. Container Deployment with Docker

Build and launch the containerized API:

```bash
# Build Docker Image
docker build -t graphone-pipeline-api .

# Run Container on Port 8000
docker run -p 8000:8000 --env-file .env graphone-pipeline-api
```

Test Docker container health:
```bash
curl http://localhost:8000/health
```

---

### 5. Cloud Platform Deployment Guidelines (Render / Railway / App Runner)

This project is prepared for single-click cloud deployment:

- **Render**: Connect repository, select **Web Service**, set Runtime to **Docker**, and configure Environment Variables (`GEMINI_API_KEY`, `GROQ_API_KEY`, `GITHUB_TOKEN`). Set Health Check Path to `/health`.
- **Railway**: Connect repository, Railway automatically detects `Dockerfile` and deploys uvicorn on `$PORT`.
- **Build / Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- **Health Check Endpoint**: `/health`

---

## Key Technical Features

### 1. Multi-Tier LLM Orchestration
- **Tier 1**: Google Gemini 1.5 Flash API (`google-generativeai`).
- **Tier 2**: Groq Llama 3 API (`llama-3.1-8b-instant`).
- **Tier 3**: Local Rule-based Deterministic Structural Extractor.
- **Selective Invocation**: LLM calls are invoked selectively on unstructured descriptions to avoid API waste.

### 2. GitHub Star Enrichment & Rate Limiting
- Supports `GITHUB_TOKEN` authentication (`Bearer <token>`).
- Canonical URL normalization (`https://github.com/owner/repo`, `.git`, trailing slashes).
- In-memory repository caching (`_repo_cache`) to prevent duplicate API requests.
- Rate-limit header parsing and exponential backoff retry loop.

### 3. Non-Synthetic Data Integrity
- Derives pricing deterministically from source metadata or LLM classification; defaults to `UNKNOWN`.
- Verified employee counts assigned only when present in source data; defaults to `null` (`UNKNOWN`).

---

## License
Distributed under the MIT License. See `LICENSE` for details.
