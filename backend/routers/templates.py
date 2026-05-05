"""Email templates CRUD router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.services import templates_store

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
async def list_templates() -> dict[str, Any]:
    return {"templates": templates_store.get_all()}


@router.get("/{template_id}")
async def get_one(template_id: str) -> dict[str, Any]:
    t = templates_store.get_by_id(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


@router.post("")
async def create_template(body: dict) -> dict[str, Any]:
    return templates_store.create(body)


@router.put("/{template_id}")
async def update_template(template_id: str, body: dict) -> dict[str, Any]:
    t = templates_store.update(template_id, body)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


@router.delete("/{template_id}")
async def delete_template(template_id: str) -> dict[str, Any]:
    if not templates_store.delete(template_id):
        raise HTTPException(status_code=404, detail="Template not found")
    return {"ok": True}
