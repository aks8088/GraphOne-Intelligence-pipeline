"""
app.py - FastAPI Web Application & API Entry Point
GraphOne / FrontierAtlas Intelligence Graph Ingestion Pipeline
"""

import os
import sys
import time
import uuid
import logging
import asyncio
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.abspath("."))

from src.pipeline import MasterPipeline
from src.exporters.google_sheets_exporter import GoogleSheetsExporter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("GraphOneAPI")

app = FastAPI(
    title="GraphOne / FrontierAtlas Intelligence Graph Ingestion API",
    description=(
        "Production-grade Web API serving the GraphOne / FrontierAtlas multi-dimensional "
        "AI ingestion pipeline. Features continuous data acquisition, multi-tier LLM enrichment "
        "(Gemini -> Groq -> Local), rate-limited GitHub star enrichment, and deterministic entity resolution."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend and browser testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pipeline State Manager
class PipelineStateManager:
    def __init__(self):
        self.is_running: bool = False
        self.current_run_id: Optional[str] = None
        self.current_mode: Optional[str] = None
        self.start_time: Optional[float] = None
        self.last_run_result: Optional[Dict[str, Any]] = None
        self.last_error: Optional[str] = None
        self._lock = asyncio.Lock()

state_manager = PipelineStateManager()

# Request & Response Schemas
class RunRequest(BaseModel):
    mode: str = Field(
        default="demo",
        description="Execution mode: 'demo' (small safe dataset, ~5s) or 'full' (1,000 items per category)."
    )

class HealthResponse(BaseModel):
    status: str
    service: str

# Helper function to run pipeline in background
async def _execute_pipeline_background(run_id: str, mode: str):
    logger.info(f"API Background Worker: Starting pipeline run '{run_id}' in '{mode}' mode...")
    start_ts = time.time()
    try:
        if mode == "demo":
            pipeline = MasterPipeline(target_startups=10, target_products=10, target_papers=10)
        else:
            pipeline = MasterPipeline(target_startups=1000, target_products=1000, target_papers=1000)

        result = await pipeline.run()
        
        async with state_manager._lock:
            state_manager.is_running = False
            state_manager.last_run_result = result
            state_manager.last_error = None
            
        logger.info(f"API Background Worker: Pipeline run '{run_id}' completed successfully in {time.time() - start_ts:.2f}s.")
    except Exception as e:
        logger.error(f"API Background Worker: Pipeline run '{run_id}' failed: {e}", exc_info=True)
        async with state_manager._lock:
            state_manager.is_running = False
            state_manager.last_error = f"Pipeline execution failed: {str(e)}"

# Endpoints
@app.get("/", summary="Root Welcome & Documentation Link")
def read_root():
    return {
        "service": "GraphOne / FrontierAtlas Intelligence Graph Pipeline API",
        "status": "operational",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "trigger_run": "/run (POST)",
            "status": "/status",
            "results": "/results",
            "downloads": [
                "/results/startups",
                "/results/products",
                "/results/papers",
                "/results/news",
                "/results/jobs",
                "/results/entity-mappings",
                "/results/excel",
                "/results/pdf"
            ]
        }
    }

@app.get("/health", response_model=HealthResponse, summary="Service Health Check")
def health_check():
    return {
        "status": "healthy",
        "service": "GraphOne Intelligence Pipeline"
    }

@app.post("/run", summary="Trigger Ingestion Pipeline (Demo or Full Mode)")
async def trigger_pipeline(request: RunRequest, background_tasks: BackgroundTasks):
    mode = request.mode.lower().strip()
    if mode not in ["demo", "full"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid execution mode. Allowed modes are 'demo' (fast ~5s run) or 'full'."
        )

    async with state_manager._lock:
        if state_manager.is_running:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "status": "already_running",
                    "message": "A pipeline run is already in progress.",
                    "run_id": state_manager.current_run_id,
                    "mode": state_manager.current_mode,
                    "elapsed_seconds": round(time.time() - (state_manager.start_time or time.time()), 2)
                }
            )

        run_id = str(uuid.uuid4())[:8]
        state_manager.is_running = True
        state_manager.current_run_id = run_id
        state_manager.current_mode = mode
        state_manager.start_time = time.time()
        state_manager.last_error = None

    background_tasks.add_task(_execute_pipeline_background, run_id, mode)

    return {
        "status": "started",
        "run_id": run_id,
        "mode": mode,
        "message": f"Pipeline execution started in '{mode}' mode."
    }

@app.get("/status", summary="Check Active / Recent Pipeline Status")
def get_pipeline_status():
    if state_manager.is_running:
        elapsed = round(time.time() - (state_manager.start_time or time.time()), 2)
        return {
            "status": "running",
            "run_id": state_manager.current_run_id,
            "mode": state_manager.current_mode,
            "elapsed_seconds": elapsed
        }
    elif state_manager.last_error:
        return {
            "status": "failed",
            "run_id": state_manager.current_run_id,
            "mode": state_manager.current_mode,
            "error": state_manager.last_error
        }
    elif state_manager.last_run_result:
        return {
            "status": "completed",
            "run_id": state_manager.current_run_id,
            "mode": state_manager.current_mode,
            "runtime_seconds": state_manager.last_run_result.get("runtime_seconds"),
            "metrics": state_manager.last_run_result
        }
    else:
        return {
            "status": "idle",
            "message": "No pipeline run has been executed during this session."
        }

@app.get("/results", summary="Get Latest Ingestion Pipeline Summary Metrics")
def get_pipeline_results():
    if state_manager.last_run_result:
        return state_manager.last_run_result

    # Fallback to inspecting output files if existing from disk
    csv_paths = {
        "startups": "outputs/startups.csv",
        "products": "outputs/products.csv",
        "papers": "outputs/research_papers.csv",
        "news": "outputs/news.csv",
        "jobs": "outputs/jobs.csv",
        "entity_mappings": "outputs/entity_mapping_log.csv"
    }

    if os.path.exists("outputs/startups.csv"):
        try:
            import pandas as pd
            counts = {}
            for k, p in csv_paths.items():
                if os.path.exists(p):
                    df = pd.read_csv(p)
                    counts[k] = len(df)
            return {
                "status": "completed_from_disk",
                "startups": counts.get("startups", 0),
                "products": counts.get("products", 0),
                "papers": counts.get("papers", 0),
                "news": counts.get("news", 0),
                "jobs": counts.get("jobs", 0),
                "entity_mappings": counts.get("entity_mappings", 0),
                "note": "Metrics loaded from output files on disk."
            }
        except Exception as e:
            logger.warning(f"Failed to read metrics from disk: {e}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No pipeline results available. Trigger a run first using POST /run."
    )

# File Download Helper
def _serve_output_file(file_path: str, filename: str, media_type: str):
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requested artifact '{filename}' not found. Please run the pipeline first using POST /run."
        )
    return FileResponse(path=file_path, filename=filename, media_type=media_type)

@app.get("/results/startups", summary="Download Startups CSV Dataset")
def download_startups():
    return _serve_output_file("outputs/startups.csv", "startups.csv", "text/csv")

@app.get("/results/products", summary="Download Products CSV Dataset")
def download_products():
    return _serve_output_file("outputs/products.csv", "products.csv", "text/csv")

@app.get("/results/papers", summary="Download Research Papers CSV Dataset")
def download_papers():
    return _serve_output_file("outputs/research_papers.csv", "research_papers.csv", "text/csv")

@app.get("/results/news", summary="Download Fresh News CSV Dataset")
def download_news():
    return _serve_output_file("outputs/news.csv", "news.csv", "text/csv")

@app.get("/results/jobs", summary="Download Fresh Jobs CSV Dataset")
def download_jobs():
    return _serve_output_file("outputs/jobs.csv", "jobs.csv", "text/csv")

@app.get("/results/entity-mappings", summary="Download Entity Mapping Log CSV")
def download_entity_mappings():
    return _serve_output_file("outputs/entity_mapping_log.csv", "entity_mapping_log.csv", "text/csv")

@app.get("/results/excel", summary="Download Multi-Tab Excel Workbook")
def download_excel():
    return _serve_output_file("data_output.xlsx", "data_output.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.get("/results/pdf", summary="Download Executive Architecture PDF Report")
def download_pdf():
    return _serve_output_file("architecture.pdf", "architecture.pdf", "application/pdf")

@app.get("/results/google-sheets", summary="Get Google Sheets Dynamic Import Links & Live Sync")
def get_google_sheets():
    links = GoogleSheetsExporter.get_google_sheets_import_links()
    sync = GoogleSheetsExporter.sync_to_live_google_sheet()
    return {
        "google_sheets_export": links,
        "live_sync_status": sync
    }
