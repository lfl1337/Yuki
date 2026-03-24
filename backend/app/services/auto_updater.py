"""
Yuki app auto-updater — checks GitHub releases, downloads Setup.exe silently.
"""

import logging
import os
import subprocess
import sys
import tempfile
import threading
import uuid
from pathlib import Path

import requests
from packaging.version import Version

logger = logging.getLogger("yuki.auto_updater")

VERSION = "2.1.3"
GITHUB_REPO = "lfl1337/Yuki"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def check_in_background(delay_s: float = 8.0) -> None:
    """Schedule update check after delay_s seconds."""
    t = threading.Timer(delay_s, _run)
    t.daemon = True
    t.start()


def check_now() -> dict:
    """
    Synchronous check — returns status dict immediately.
    Does NOT download or install.
    """
    try:
        resp = requests.get(GITHUB_API_URL, timeout=10,
                            headers={"Accept": "application/vnd.github.v3+json"})
        resp.raise_for_status()
        data = resp.json()
        tag = data.get("tag_name", "").lstrip("v")
        if not tag:
            return {"has_update": False, "latest": VERSION, "current": VERSION}
        has_update = Version(tag) > Version(VERSION)
        return {"has_update": has_update, "latest": tag, "current": VERSION}
    except Exception as exc:
        logger.debug("Update check failed: %s", exc)
        return {"has_update": False, "latest": VERSION, "current": VERSION, "error": str(exc)}


def _run() -> None:
    try:
        resp = requests.get(GITHUB_API_URL, timeout=15,
                            headers={"Accept": "application/vnd.github.v3+json"})
        resp.raise_for_status()
        data = resp.json()
        tag = data.get("tag_name", "").lstrip("v")
        if not tag or not (Version(tag) > Version(VERSION)):
            logger.info("No app update available (current=%s latest=%s)", VERSION, tag or "?")
            return

        logger.info("App update available: %s → %s", VERSION, tag)
        assets = data.get("assets", [])
        asset = next(
            (a for a in assets
             if "setup" in a.get("name", "").lower() and a["name"].lower().endswith(".exe")),
            None,
        )
        if not asset:
            logger.info("No Setup.exe asset in release %s", tag)
            return

        url = asset["browser_download_url"]
        if not isinstance(url, str) or not url.startswith("https://"):
            logger.warning("Update URL is not HTTPS: %s", url)
            return

        # Clean up old update files
        for old in Path(tempfile.gettempdir()).glob("Yuki_Update_*.exe"):
            try:
                old.unlink()
            except Exception:
                pass

        installer = Path(tempfile.gettempdir()) / f"Yuki_Update_{uuid.uuid4().hex[:8]}.exe"
        with requests.get(url, timeout=300, stream=True) as r:
            r.raise_for_status()
            with open(installer, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

        logger.info("Update downloaded: %s", installer)
        _launch_installer(installer)

    except Exception as exc:
        logger.debug("Auto-update error: %s", exc)


def _launch_installer(installer: Path) -> None:
    try:
        bat = Path(tempfile.gettempdir()) / f"yuki_update_{uuid.uuid4().hex[:8]}.bat"
        bat.write_text(
            "@echo off\r\n"
            "timeout /t 2 /nobreak >nul\r\n"
            "taskkill /f /im Yuki.exe >nul 2>&1\r\n"
            "taskkill /f /im yuki-backend-x86_64-pc-windows-msvc.exe >nul 2>&1\r\n"
            f'start "" "{installer}" /S\r\n'
            "exit\r\n",
            encoding="utf-8",
        )
        subprocess.Popen(
            ["cmd", "/c", str(bat)],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        )
        logger.info("Update installer launched — exiting for update")
        os._exit(0)
    except Exception as exc:
        logger.debug("Failed to launch installer: %s", exc)
