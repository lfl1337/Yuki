"""
Spotify download via spotdl subprocess.
spotdl has no stable Python API — we use subprocess and parse stdout.
"""

import logging
import os
import subprocess
from pathlib import Path

from ..config import settings

logger = logging.getLogger("yuki.spotify")

AUDIO_QUALITY_MAP = {
    "best": "320",
    "320kbps": "320",
    "192kbps": "192",
    "128kbps": "128",
    "320": "320",
    "192": "192",
    "128": "128",
}


def download_spotify(job) -> str:
    """
    Download a Spotify URL via spotdl subprocess.
    Updates job.progress_pct as songs complete.
    Returns output directory path on success.
    Raises RuntimeError on failure.
    """
    output_dir = Path(job.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    bitrate = AUDIO_QUALITY_MAP.get(job.quality, "320")

    cmd = [
        "spotdl",
        job.url,
        "--output", str(output_dir / "{title}"),
        "--bitrate", f"{bitrate}k",
        "--ffmpeg", settings.ffmpeg_path,
        "--no-cache",
    ]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    logger.info("spotdl: %s", job.url)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "spotdl failed").strip()
        raise RuntimeError(f"spotdl error: {err[:200]}")

    job.progress_pct = 100
    return str(output_dir)
