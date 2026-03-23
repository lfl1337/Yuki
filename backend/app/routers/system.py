"""System utility endpoints — open folder in Explorer, etc."""

import logging
import os
import subprocess
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("yuki.routers.system")
router = APIRouter(prefix="/system", tags=["system"])


class OpenFolderRequest(BaseModel):
    path: str


@router.post("/open-folder")
async def open_folder(body: OpenFolderRequest):
    """Open a file's containing folder (or the path itself if it is a folder)
    in Windows Explorer. Runs detached so it never blocks the backend."""
    raw = body.path
    if not raw:
        return {"ok": False, "error": "empty path"}

    folder = Path(raw)
    if folder.is_file():
        folder = folder.parent

    if not folder.exists():
        return {"ok": False, "error": f"path does not exist: {folder}"}

    try:
        subprocess.Popen(
            ["explorer", str(folder)],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        logger.debug("Opened folder: %s", folder)
        return {"ok": True}
    except Exception as exc:
        logger.warning("open-folder failed: %s", exc)
        return {"ok": False, "error": str(exc)}
