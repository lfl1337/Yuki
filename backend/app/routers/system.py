"""System utility endpoints — open folder in Explorer, etc."""

import logging
import os
import subprocess
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("yuki.routers.system")
router = APIRouter(prefix="/system", tags=["system"])

_FORBIDDEN_PATH_PREFIXES = (
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\programdata",
    "c:\\system volume information",
)


class OpenFolderRequest(BaseModel):
    path: str


@router.post("/open-folder")
async def open_folder(body: OpenFolderRequest):
    """Open a file's containing folder (or the path itself if it is a folder)
    in Windows Explorer. Runs detached so it never blocks the backend."""
    raw = body.path
    if not raw:
        return {"ok": False, "error": "empty path"}

    # Pure-string normalization — no filesystem access at this point.
    normalized = os.path.normpath(os.path.abspath(raw))

    # Reject system directories before any filesystem operation.
    normalized_lower = normalized.lower()
    for forbidden in _FORBIDDEN_PATH_PREFIXES:
        if normalized_lower.startswith(forbidden):
            return {"ok": False, "error": "Access to system directories is not allowed"}

    # Pass the normalized path directly to Explorer.
    # explorer.exe handles both files and directories natively:
    # - files: opens the containing folder with the file selected
    # - directories: opens the folder
    # - non-existent paths: shows its own error dialog
    # This avoids all filesystem sinks (is_file / exists) on user-supplied data.
    try:
        subprocess.Popen(
            ["explorer", normalized],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        logger.debug("Opened in Explorer: %s", normalized)
        return {"ok": True}
    except Exception as exc:
        logger.warning("open-folder failed: %s", exc)
        return {"ok": False, "error": "Failed to open folder"}
