"""
Download service — wraps yt-dlp Python API.
Thread-based with semaphore limiting (max 3 concurrent).
Saves completed downloads to history DB via asyncio bridge.
"""

import asyncio
import logging
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yt_dlp

from ..config import settings
from .detector import detect_platform

logger = logging.getLogger("yuki.downloader")

AUDIO_QUALITY_MAP = {
    "best": "0",
    "320kbps": "320",
    "192kbps": "192",
    "128kbps": "128",
    "320": "320",
    "192": "192",
    "128": "128",
}

FORMAT_VIDEO = {
    "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
    "720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",
    "480p": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]",
    "360p": "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]",
}

_jobs: dict[str, "DownloadJob"] = {}
_semaphore = threading.Semaphore(3)
_event_loop: Optional[asyncio.AbstractEventLoop] = None
_lock = threading.Lock()


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _event_loop
    _event_loop = loop


@dataclass
class DownloadJob:
    job_id: str
    url: str
    format: str
    quality: str
    output_dir: str
    status: str = "queued"
    title: str = ""
    artist: str = ""
    platform: str = ""
    thumbnail_url: str = ""
    progress_pct: float = 0
    speed: float = 0
    eta: int = 0
    filepath: str = ""
    error: str = ""
    cancel_event: threading.Event = field(default_factory=threading.Event)
    _current_filepath: str = field(default="", repr=False)


def start_download(url: str, fmt: str, quality: str, output_dir: str) -> str:
    job_id = str(uuid.uuid4())
    job = DownloadJob(job_id=job_id, url=url, format=fmt, quality=quality,
                      output_dir=output_dir)
    detected = detect_platform(url)
    job.platform = detected.get("platform", "Unknown")
    with _lock:
        _jobs[job_id] = job
    t = threading.Thread(target=_run_job, args=(job,), daemon=True,
                         name=f"dl-{job_id[:8]}")
    t.start()
    return job_id


def get_job(job_id: str) -> Optional[DownloadJob]:
    return _jobs.get(job_id)


def get_active_jobs() -> list[DownloadJob]:
    with _lock:
        return [j for j in _jobs.values()
                if j.status not in ("done", "error", "cancelled")]


def get_all_jobs() -> list[DownloadJob]:
    with _lock:
        return list(_jobs.values())


def cancel_job(job_id: str) -> bool:
    job = _jobs.get(job_id)
    if not job:
        return False
    job.cancel_event.set()
    job.status = "cancelled"
    return True


def cancel_all() -> None:
    for job_id in list(_jobs.keys()):
        cancel_job(job_id)


def remove_job(job_id: str) -> None:
    with _lock:
        _jobs.pop(job_id, None)


def get_info(url: str) -> dict:
    """Fetch metadata without downloading. Returns dict."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "ffmpeg_location": str(Path(settings.ffmpeg_path).parent),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("title", "Unknown"),
            "thumbnail_url": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader") or info.get("channel", ""),
            "platform": info.get("extractor_key", "Unknown"),
            "url": url,
        }


# ---- Internal ----

def _run_job(job: DownloadJob) -> None:
    _semaphore.acquire()
    try:
        if job.cancel_event.is_set():
            return
        job.status = "fetching"

        # 1. Fetch metadata
        try:
            info = get_info(job.url)
            job.title = info.get("title", job.url)
            job.artist = info.get("uploader", "")
            job.thumbnail_url = info.get("thumbnail_url", "")
            if not job.platform or job.platform == "Unknown":
                job.platform = info.get("platform", "Unknown")
        except Exception as exc:
            logger.warning("Metadata fetch failed (non-fatal): %s", exc)
            job.title = job.url

        if job.cancel_event.is_set():
            job.status = "cancelled"
            return

        job.status = "downloading"

        # 2. Download
        if job.platform == "Spotify":
            _run_spotify(job)
        elif job.format == "audio":
            _run_ytdlp_audio(job)
        else:
            _run_ytdlp_video(job)

    except Exception as exc:
        job.status = "error"
        job.error = str(exc)
        logger.error("Download job %s failed: %s", job.job_id[:8], exc)
    finally:
        _semaphore.release()


class _CancelledError(Exception):
    pass


def _progress_hook(job: DownloadJob):
    def hook(d: dict):
        if job.cancel_event.is_set():
            raise _CancelledError("Cancelled")
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            downloaded = d.get("downloaded_bytes", 0)
            job.progress_pct = min(downloaded / total * 100, 100.0)
            job.speed = d.get("speed") or 0
            job.eta = d.get("eta") or 0
            job._current_filepath = d.get("filename", "")
        elif status == "finished":
            job._current_filepath = d.get("filename", "")
            job.status = "processing"
    return hook


def _base_opts(job: DownloadJob) -> dict:
    Path(job.output_dir).mkdir(parents=True, exist_ok=True)
    return {
        "ffmpeg_location": str(Path(settings.ffmpeg_path).parent),
        "outtmpl": str(Path(job.output_dir) / "%(title)s.%(ext)s"),
        "progress_hooks": [_progress_hook(job)],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "addmetadata": True,
        "windowsfilenames": True,
        "overwrites": False,
    }


def _resolve_output(opts: dict, info: dict, job: DownloadJob) -> str:
    try:
        requested = info.get("requested_downloads") or []
        if requested:
            fp = requested[0].get("filepath", "")
            if fp and Path(fp).exists():
                return str(Path(fp).resolve())
    except Exception:
        pass
    if job._current_filepath:
        fp = job._current_filepath.removesuffix(".part")
        p = Path(fp)
        if p.exists():
            return str(p.resolve())
        for ext in (".mp3", ".m4a", ".flac", ".wav", ".ogg", ".aac", ".opus", ".mp4"):
            c = p.with_suffix(ext)
            if c.exists():
                return str(c.resolve())
    return ""


def _run_ytdlp_audio(job: DownloadJob) -> None:
    bitrate = AUDIO_QUALITY_MAP.get(job.quality, "320")
    opts = _base_opts(job)
    opts.update({
        "format": "bestaudio/best",
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": bitrate},
            {"key": "FFmpegMetadata"},
            {"key": "EmbedThumbnail"},
        ],
        "writethumbnail": True,
        "prefer_ffmpeg": True,
    })
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(job.url, download=True)
            job.filepath = _resolve_output(opts, info, job)
            job.status = "done"
            job.progress_pct = 100
            _save_to_history(job, info)
    except _CancelledError:
        job.status = "cancelled"
    except yt_dlp.utils.DownloadError as exc:
        job.status = "error"
        job.error = str(exc)


def _run_ytdlp_video(job: DownloadJob) -> None:
    fmt = FORMAT_VIDEO.get(job.quality, FORMAT_VIDEO["best"])
    opts = _base_opts(job)
    opts.update({
        "format": fmt,
        "postprocessors": [{"key": "FFmpegMetadata"}],
        "merge_output_format": "mp4",
    })
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(job.url, download=True)
            job.filepath = _resolve_output(opts, info, job)
            job.status = "done"
            job.progress_pct = 100
            _save_to_history(job, info)
    except _CancelledError:
        job.status = "cancelled"
    except yt_dlp.utils.DownloadError as exc:
        job.status = "error"
        job.error = str(exc)


def _run_spotify(job: DownloadJob) -> None:
    from .spotify import download_spotify
    try:
        filepath = download_spotify(job)
        job.filepath = filepath
        job.status = "done"
        job.progress_pct = 100
        _save_to_history(job, {})
    except Exception as exc:
        job.status = "error"
        job.error = str(exc)


def _save_to_history(job: DownloadJob, info: dict) -> None:
    """Save completed download to SQLite via asyncio bridge."""
    if not _event_loop:
        return
    entry = {
        "title": job.title or info.get("title", ""),
        "artist": job.artist or info.get("uploader") or info.get("channel", ""),
        "platform": job.platform,
        "format": job.format,
        "quality": job.quality,
        "filepath": job.filepath,
        "thumbnail_url": job.thumbnail_url or info.get("thumbnail", ""),
        "duration": int(info.get("duration", 0)),
        "filesize": int(info.get("filesize") or info.get("filesize_approx", 0)),
        "url": job.url,
    }
    asyncio.run_coroutine_threadsafe(_async_save_history(entry), _event_loop)


async def _async_save_history(entry: dict) -> None:
    try:
        from ..database import AsyncSessionLocal
        from ..models import HistoryEntry
        from uuid import uuid4
        from datetime import datetime
        async with AsyncSessionLocal() as s:
            s.add(HistoryEntry(
                id=str(uuid4()),
                downloaded_at=datetime.now().isoformat(),
                **entry,
            ))
            await s.commit()
    except Exception as exc:
        logger.error("Failed to save history entry: %s", exc)
