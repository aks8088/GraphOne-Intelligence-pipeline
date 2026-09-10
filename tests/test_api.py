"""
tests/test_api.py - FastAPI Web Application Unit Tests
GraphOne / FrontierAtlas Intelligence Graph Ingestion Pipeline
"""

import os
import sys
import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))

from app import app, state_manager

client = TestClient(app)

class TestFastAPIApplication(unittest.TestCase):

    def setUp(self):
        # Reset state manager before each test
        state_manager.is_running = False
        state_manager.current_run_id = None
        state_manager.current_mode = None
        state_manager.start_time = None
        state_manager.last_run_result = None
        state_manager.last_error = None

    def test_health_endpoint(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "GraphOne Intelligence Pipeline")
        self.assertNotIn("GEMINI_API_KEY", str(data))
        self.assertNotIn("GROQ_API_KEY", str(data))
        self.assertNotIn("GITHUB_TOKEN", str(data))

    def test_root_endpoint(self):
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("documentation", data)
        self.assertEqual(data["documentation"], "/docs")

    @patch("app.MasterPipeline")
    def test_trigger_demo_mode(self, mock_master_pipeline):
        mock_instance = AsyncMock()
        mock_instance.run.return_value = {
            "status": "completed",
            "startups": 10,
            "products": 10,
            "papers": 10,
            "news": 5,
            "jobs": 5,
            "entity_mappings": 20,
            "runtime_seconds": 2.5
        }
        mock_master_pipeline.return_value = mock_instance

        response = client.post("/run", json={"mode": "demo"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "started")
        self.assertEqual(data["mode"], "demo")
        self.assertIn("run_id", data)

    def test_invalid_execution_mode(self):
        response = client.post("/run", json={"mode": "super_fast_invalid"})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("detail", data)

    def test_duplicate_run_prevention(self):
        state_manager.is_running = True
        state_manager.current_run_id = "run12345"
        state_manager.current_mode = "demo"

        response = client.post("/run", json={"mode": "demo"})
        self.assertEqual(response.status_code, 409)
        data = response.json()
        self.assertEqual(data["status"], "already_running")
        self.assertEqual(data["run_id"], "run12345")

    def test_status_endpoint_idle(self):
        response = client.get("/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "idle")

    def test_status_endpoint_running(self):
        state_manager.is_running = True
        state_manager.current_run_id = "test_run_id"
        state_manager.current_mode = "demo"
        state_manager.start_time = 100.0

        response = client.get("/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["run_id"], "test_run_id")

    def test_results_endpoint_completed(self):
        state_manager.last_run_result = {
            "status": "completed",
            "startups": 1000,
            "products": 1000,
            "papers": 1000,
            "news": 23,
            "jobs": 14,
            "entity_mappings": 2014,
            "runtime_seconds": 35.17
        }
        response = client.get("/results")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["startups"], 1000)
        self.assertEqual(data["runtime_seconds"], 35.17)

    def test_download_endpoints_exist(self):
        # If outputs exist, returns file response (200 OK); if missing, returns 404
        for endpoint in ["/results/startups", "/results/products", "/results/excel", "/results/pdf"]:
            response = client.get(endpoint)
            self.assertIn(response.status_code, [200, 404])

    @patch("app._execute_pipeline_background")
    def test_pipeline_failure_handling(self, mock_bg_task):
        state_manager.last_error = "Pipeline execution failed: Network timeout"
        state_manager.current_run_id = "err_run_id"
        state_manager.current_mode = "full"

        response = client.get("/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["error"], "Pipeline execution failed: Network timeout")

    def test_google_sheets_endpoint(self):
        response = client.get("/results/google-sheets")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("google_sheets_export", data)
        self.assertIn("import_data_formulas", data["google_sheets_export"])

if __name__ == "__main__":
    unittest.main()
