import pytest
import os
from pathlib import Path
from openpyxl import Workbook
from src.core.storage import list_files, read_leads, get_existing_businesses, get_existing_direct_lead_urls
from src.core.config import COLD_OUTPUT_DIR, DIRECT_OUTPUT_DIR

@pytest.fixture
def cold_xlsx(tmp_path, monkeypatch):
    """Create a temp cold outreach Excel file."""
    import src.core.storage as storage_mod
    import src.core.config as config_mod

    cold_dir = tmp_path / "cold"
    cold_dir.mkdir()
    monkeypatch.setattr(storage_mod, "COLD_OUTPUT_DIR", cold_dir)
    monkeypatch.setattr(storage_mod, "OUTPUT_DIR", tmp_path)

    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    ws.append(["Lead_ID", "Business_Name", "City", "State", "Phone", "Priority", "Score"])
    ws.append(["abc123", "Joe Plumbing", "Miami", "FL", "(305) 555-1234", "HOT", 45])
    ws.append(["def456", "Quick Fix", "Miami", "FL", "(305) 555-5678", "WARM", 30])
    path = cold_dir / "test_leads.xlsx"
    wb.save(path)
    return path, cold_dir, tmp_path

def test_list_files_cold(cold_xlsx):
    path, cold_dir, tmp_path = cold_xlsx
    import src.core.storage as storage_mod
    storage_mod.COLD_OUTPUT_DIR = cold_dir
    files = list_files("cold")
    assert len(files) == 1
    assert files[0]["name"] == "test_leads.xlsx"
    assert files[0]["section"] == "cold"

def test_read_leads_cold(cold_xlsx):
    path, cold_dir, tmp_path = cold_xlsx
    import src.core.storage as storage_mod
    storage_mod.COLD_OUTPUT_DIR = cold_dir
    headers, rows = read_leads("test_leads.xlsx", "cold")
    assert "Lead_ID" in headers
    assert len(rows) == 2
    assert rows[0]["Business_Name"] == "Joe Plumbing"

def test_list_files_empty_direct(cold_xlsx):
    _, _, tmp_path = cold_xlsx
    import src.core.storage as storage_mod
    direct_dir = tmp_path / "direct"
    direct_dir.mkdir(exist_ok=True)
    storage_mod.DIRECT_OUTPUT_DIR = direct_dir
    files = list_files("direct")
    assert len(files) == 0
