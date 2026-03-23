"""Settings router — key/value settings stored in SQLite."""

import json
import logging
from typing import Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import Setting
from ..schemas import SettingSave
from ..services.autostart import enable_autostart, disable_autostart, is_autostart_enabled

logger = logging.getLogger("yuki.routers.settings")
router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Setting))
    rows = result.scalars().all()
    out = {}
    for row in rows:
        try:
            out[row.key] = json.loads(row.value)
        except Exception:
            out[row.key] = row.value
    return out


@router.post("/save")
async def save_settings(body: SettingSave, session: AsyncSession = Depends(get_session)):
    for key, value in body.settings.items():
        existing = await session.get(Setting, key)
        serialized = json.dumps(value)
        if existing:
            existing.value = serialized
        else:
            session.add(Setting(key=key, value=serialized))

        # Side effects
        if key == "autostart":
            try:
                if value:
                    enable_autostart()
                else:
                    disable_autostart()
            except Exception as exc:
                logger.warning("Autostart toggle failed: %s", exc)

    await session.commit()
    return {"ok": True}


@router.patch("")
async def patch_settings(
    body: dict[str, Any] = Body(...),
    session: AsyncSession = Depends(get_session),
):
    """Partial settings update — upserts only the supplied keys."""
    for key, value in body.items():
        serialized = json.dumps(value)
        existing = await session.get(Setting, key)
        if existing:
            existing.value = serialized
        else:
            session.add(Setting(key=key, value=serialized))

        if key == "autostart":
            try:
                if value:
                    enable_autostart()
                else:
                    disable_autostart()
            except Exception as exc:
                logger.warning("Autostart toggle failed: %s", exc)

    await session.commit()
    return {"ok": True}


@router.get("/autostart")
async def get_autostart():
    return {"enabled": is_autostart_enabled()}
