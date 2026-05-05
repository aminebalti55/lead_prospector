"""Settings GET + PUT endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.services import settings_store

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings() -> dict[str, Any]:
    return settings_store.get_masked()


@router.put("")
async def update_settings(body: dict) -> dict[str, Any]:
    settings_store.save(body)
    return settings_store.get_masked()
