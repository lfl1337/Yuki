"""
Silent auto-updater for Yuki.
Checks GitHub releases on startup (8s delay) and silently installs newer versions.
Never shows any UI — all errors are logged only.
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

from config import VERSION, GITHUB_REPO

logger = logging.getLogger(__name__)

GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class AutoUpdater:
    def check_in_background(self):
        """Schedule update check in a daemon thread after an 8-second delay."""
        t = threading.Timer(8.0, self._run)
        t.daemon = True
        t.start()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run(self):
        try:
            resp = requests.get(
                GITHUB_API_URL,
                timeout=15,
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.debug("Update check failed: %s", exc)
            return

        try:
            tag = data.get("tag_name", "").lstrip("v")
            if not tag:
                logger.debug("Update check: could not parse release tag")
                return

            try:
                needs_update = Version(tag) > Version(VERSION)
            except Exception:
                needs_update = tag != VERSION

            if not needs_update:
                logger.info("No update available (current=%s, latest=%s)", VERSION, tag)
                return

            logger.info("Update available: %s -> %s — downloading", VERSION, tag)

            # Find the Setup .exe asset
            assets = data.get("assets", [])
            setup_asset = next(
                (
                    a for a in assets
                    if "setup" in a.get("name", "").lower()
                    and a["name"].lower().endswith(".exe")
                ),
                None,
            )
            if not setup_asset:
                logger.info("Update: no Setup .exe asset found in release %s", tag)
                return

            download_url = setup_asset["browser_download_url"]
            if not isinstance(download_url, str) or not download_url.startswith("https://"):
                logger.warning("Update: download URL is not HTTPS, skipping: %s", download_url)
                return

            # Clean up any leftover update files from previous failed attempts
            for old in Path(tempfile.gettempdir()).glob("Yuki_Update_*.exe"):
                try:
                    old.unlink()
                except Exception:
                    pass

            installer_path = Path(tempfile.gettempdir()) / f"Yuki_Update_{uuid.uuid4().hex[:8]}.exe"

            # Download silently — no progress, no dialog, no toast
            try:
                with requests.get(download_url, timeout=300, stream=True) as r:
                    r.raise_for_status()
                    with open(installer_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)
            except Exception as exc:
                logger.debug("Update download failed: %s", exc)
                return

            logger.info("Update downloaded to %s — preparing install", installer_path)
            self._launch_installer(installer_path)

        except Exception as exc:
            logger.debug("Auto-update error: %s", exc)

    def _launch_installer(self, installer_path: Path):
        try:
            bat_path = Path(tempfile.gettempdir()) / f"yuki_update_{uuid.uuid4().hex[:8]}.bat"
            exe = str(installer_path)
            current_exe = sys.executable

            bat_content = (
                "@echo off\r\n"
                "timeout /t 2 /nobreak >nul\r\n"
                "taskkill /f /im Yuki.exe >nul 2>&1\r\n"
                f'start "" "{exe}" /S\r\n'
                "timeout /t 5 /nobreak >nul\r\n"
                f'start "" "{current_exe}" --updated\r\n'
                "exit\r\n"
            )
            bat_path.write_text(bat_content, encoding="utf-8")

            subprocess.Popen(
                ["cmd", "/c", str(bat_path)],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            )

            logger.info("Update installer launched, exiting for update")
            os._exit(0)
        except Exception as exc:
            logger.debug("Failed to launch installer: %s", exc)
