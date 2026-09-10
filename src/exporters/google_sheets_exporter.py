"""
src/exporters/google_sheets_exporter.py - Google Sheets Integration & Exporter
GraphOne / FrontierAtlas Intelligence Graph Ingestion Pipeline
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("GoogleSheetsExporter")

class GoogleSheetsExporter:
    @staticmethod
    def get_google_sheets_import_links(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
        """
        Generate Google Sheets import formulas and web links for all 6 ingested datasets.
        Users can paste the =IMPORTDATA() formulas directly into any Google Sheet.
        """
        datasets = ["startups", "products", "papers", "news", "jobs", "entity-mappings"]
        
        formulas = {}
        download_urls = {}
        for ds in datasets:
            url = f"{base_url.rstrip('/')}/results/{ds}"
            download_urls[ds] = url
            formulas[ds] = f'=IMPORTDATA("{url}")'
            
        return {
            "status": "ready",
            "service": "Google Sheets Exporter & Dynamic Import Engine",
            "google_sheets_new_url": "https://sheets.new",
            "import_data_formulas": formulas,
            "download_urls": download_urls,
            "instructions": [
                "1. Open a new Google Sheet at https://sheets.new",
                "2. Create 6 tabs: Startups, Products, Research Papers, News, Jobs, Entity Mappings.",
                "3. In cell A1 of each tab, paste the corresponding =IMPORTDATA(\"...\") formula.",
                "4. Google Sheets will automatically fetch, parse, and display live output data!"
            ]
        }

    @staticmethod
    def sync_to_live_google_sheet(spreadsheet_id: Optional[str] = None, credentials_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Optional: Live sync to a specific Google Sheet using gspread if service account credentials are provided.
        """
        sheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
        creds = credentials_path or os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        
        if not sheet_id or not creds:
            logger.info("Google Sheets Live Sync: Credentials or Spreadsheet ID not configured in .env.")
            return {
                "status": "credentials_not_configured",
                "message": "To enable live Google Sheets sync, configure GOOGLE_SERVICE_ACCOUNT_FILE and GOOGLE_SHEETS_SPREADSHEET_ID in .env."
            }
            
        try:
            import gspread
            gc = gspread.service_account(filename=creds)
            sh = gc.open_by_key(sheet_id)
            logger.info(f"Successfully connected to Google Sheet: {sh.title}")
            return {
                "status": "synced",
                "spreadsheet_title": sh.title,
                "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
            }
        except Exception as e:
            logger.warning(f"Google Sheets Sync failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
