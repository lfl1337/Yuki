"""
yt-dlp auto-update checker.
Runs on startup in a background thread; also exposes manual_update().
"""

import logging
import subprocess
import sys
import threading
from typing import Callable, Optional

import requests
from packaging.version import Version

logger = logging.getLogger(__name__)

YTDLP_PYPI_URL = "https://pypi.org/pypi/yt-dlp/json"


def _get_installed_version() -> Optional[str]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--version"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() or None
    except Exception:
        try:
            import yt_dlp
            return yt_dlp.version.__version__
        except Exception:
            return None


def _get_latest_version() -> Optional[str]:
    try:
        resp = requests.get(YTDLP_PYPI_URL, timeout=10)
        resp.raise_for_status()
        return resp.json()["info"]["version"]
    except Exception as exc:
        logger.warning("Could not fetch yt-dlp latest version: %s", exc)
        return None


def _do_update() -> bool:
    """Run pip install -U yt-dlp. Returns True on success."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "yt-dlp", "--quiet"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            logger.info("yt-dlp updated successfully")
            return True
        else:
            logger.error("yt-dlp update failed: %s", result.stderr)
            return False
    except Exception as exc:
        logger.error("yt-dlp update error: %s", exc)
        return False


class Updater:
    """
    Checks for yt-dlp updates and optionally installs them.

    on_update_available(current, latest) — called if update exists
    on_update_done(success) — called after update attempt
    """

    def __init__(
        self,
        on_update_available: Optional[Callable[[str, str], None]] = None,
        on_update_done: Optional[Callable[[bool], None]] = None,
    ):
        self._on_available = on_update_available or (lambda c, l: None)
        self._on_done = on_update_done or (lambda ok: None)

    def check_and_update(self, auto_update: bool = True):
        """Start background check. If auto_update is True, install silently."""
        thread = threading.Thread(
            target=self._run,
            args=(auto_update,),
            daemon=True,
            name="updater",
        )
        thread.start()

    def manual_update(self):
        """Trigger a manual update in the background."""
        thread = threading.Thread(
            target=self._force_update,
            daemon=True,
            name="manual-updater",
        )
        thread.start()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run(self, auto_update: bool):
        current = _get_installed_version()
        latest = _get_latest_version()
        if not current or not latest:
            return
        try:
            needs_update = Version(latest) > Version(current)
        except Exception:
            needs_update = latest != current

        if needs_update:
            self._on_available(current, latest)
            if auto_update:
                ok = _do_update()
                self._on_done(ok)

    def _force_update(self):
        ok = _do_update()
        self._on_done(ok)
