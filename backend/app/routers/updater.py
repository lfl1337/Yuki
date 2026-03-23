"""Updater router — yt-dlp and app update checks."""

import asyncio
import json
import logging

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from ..services.auto_updater import check_now

logger = logging.getLogger("yuki.routers.updater")
router = APIRouter(prefix="/updater", tags=["updater"])


def _ytdlp_version() -> str:
    try:
        import yt_dlp
        return yt_dlp.version.__version__
    except Exception:
        return "unknown"


def _ytdlp_latest() -> str:
    try:
        import requests
        resp = requests.get("https://pypi.org/pypi/yt-dlp/json", timeout=8)
        resp.raise_for_status()
        return resp.json()["info"]["version"]
    except Exception:
        return _ytdlp_version()


@router.get("/status")
async def status():
    app_status = await asyncio.to_thread(check_now)
    current = await asyncio.to_thread(_ytdlp_version)
    latest = await asyncio.to_thread(_ytdlp_latest)
    from packaging.version import Version
    try:
        ytdlp_has_update = Version(latest) > Version(current)
    except Exception:
        ytdlp_has_update = False
    return {
        "ytdlp_current": current,
        "ytdlp_latest": latest,
        "ytdlp_has_update": ytdlp_has_update,
        "app_current": app_status["current"],
        "app_latest": app_status["latest"],
        "app_has_update": app_status["has_update"],
    }


@router.post("/update-ytdlp")
async def update_ytdlp(request: Request):
    """SSE stream: run pip install --upgrade yt-dlp and stream progress."""
    async def generator():
        import subprocess, sys
        try:
            yield {"data": json.dumps({"status": "starting"})}
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                yield {"data": json.dumps({"status": "progress", "line": line.decode().strip()})}
            await proc.wait()
            if proc.returncode == 0:
                yield {"data": json.dumps({"status": "done"})}
            else:
                yield {"data": json.dumps({"status": "error", "code": proc.returncode})}
        except Exception as exc:
            yield {"data": json.dumps({"status": "error", "message": str(exc)})}

    return EventSourceResponse(generator())
