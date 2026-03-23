"""Player router — audio playback control + SSE position stream."""

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from ..schemas import PlayerLoadRequest, PlayerSeekRequest, PlayerVolumeRequest, PlayerStatus
from ..services import player as player_svc
from ..services.player_engine import AudioPlayer

logger = logging.getLogger("yuki.routers.player")
router = APIRouter(prefix="/player", tags=["player"])


def _get() -> AudioPlayer:
    return player_svc.get_player()


@router.post("/load")
async def load(body: PlayerLoadRequest):
    from pathlib import Path
    if not Path(body.filepath).exists():
        raise HTTPException(404, f"File not found: {body.filepath}")
    try:
        await asyncio.to_thread(_get().load, body.filepath)
        # Warm the tag cache immediately so SSE never reads from disk
        await asyncio.to_thread(player_svc.notify_loaded, body.filepath)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/play")
async def play():
    """Resume if paused, otherwise start from beginning."""
    p = _get()
    if p.is_paused():
        await asyncio.to_thread(p.resume)
    else:
        await asyncio.to_thread(p.play)
    return {"ok": True}


@router.post("/pause")
async def pause():
    await asyncio.to_thread(_get().pause)
    return {"ok": True}


@router.post("/stop")
async def stop():
    await asyncio.to_thread(_get().stop)
    return {"ok": True}


@router.post("/seek")
async def seek(body: PlayerSeekRequest):
    await asyncio.to_thread(_get().seek, body.position)
    return {"ok": True}


@router.post("/volume")
async def volume(body: PlayerVolumeRequest):
    await asyncio.to_thread(_get().set_volume, body.volume)
    return {"ok": True}


@router.get("/status", response_model=PlayerStatus)
async def status():
    data = await asyncio.to_thread(player_svc.get_status_dict)
    return PlayerStatus(**data)


@router.get("/stream")
async def stream(request: Request):
    """SSE: player position updates every 500ms."""
    return EventSourceResponse(player_svc.sse_generator(request))
