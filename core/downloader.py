"""
Download engine — wraps yt-dlp Python API and spotdl for Spotify.
All operations run in caller-provided threads; this class is thread-safe.
"""

import os
import threading
import logging
from pathlib import Path
from typing import Callable, Optional

import yt_dlp

from config import FFMPEG_PATH, AUDIO_QUALITY_MAP, FORMAT_VIDEO

logger = logging.getLogger(__name__)


class Downloader:
    """
    Manages a single download operation. Create a new instance per download.

    Callbacks (all called from the download thread, schedule via after() for UI):
        progress_callback(percent, speed, eta, filename)
        completion_callback(filepath, metadata)
        error_callback(error_message)
    """

    def __init__(
        self,
        progress_callback: Optional[Callable] = None,
        completion_callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
    ):
        self._progress_cb = progress_callback or (lambda *a: None)
        self._completion_cb = completion_callback or (lambda *a: None)
        self._error_cb = error_callback or (lambda *a: None)
        self._cancel_event = threading.Event()
        self._current_filepath: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cancel(self):
        """Signal the running download to stop."""
        self._cancel_event.set()

    def get_info(self, url: str) -> dict:
        """
        Fetch metadata without downloading.
        Returns dict: title, thumbnail_url, duration, uploader, platform, url
        """
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "ffmpeg_location": str(FFMPEG_PATH.parent),
        }
        try:
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
        except Exception as exc:
            logger.error("get_info failed: %s", exc)
            raise

    def download_audio(
        self,
        url: str,
        output_dir: str,
        quality: str = "320kbps",
        filename_template: str = "%(title)s",
    ):
        """Download and convert to MP3."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        bitrate = AUDIO_QUALITY_MAP.get(quality, "320")

        opts = self._base_opts(output_dir, filename_template)
        opts.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": bitrate,
                    },
                    {"key": "FFmpegMetadata"},
                    {"key": "EmbedThumbnail"},
                ],
                "writethumbnail": True,
            }
        )
        self._run_download(url, opts)

    def download_video(
        self,
        url: str,
        output_dir: str,
        quality: str = "best",
        filename_template: str = "%(title)s",
    ):
        """Download as MP4."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        fmt = FORMAT_VIDEO.get(quality, FORMAT_VIDEO["best"])

        opts = self._base_opts(output_dir, filename_template)
        opts.update(
            {
                "format": fmt,
                "postprocessors": [
                    {"key": "FFmpegMetadata"},
                ],
                "merge_output_format": "mp4",
                "writethumbnail": False,
            }
        )
        self._run_download(url, opts)

    def download_spotify(
        self,
        url: str,
        output_dir: str,
        quality: str = "320kbps",
    ):
        """Download Spotify track/album/playlist via spotdl."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._run_spotdl(url, output_dir, quality)
        except Exception as exc:
            logger.error("spotdl failed: %s", exc)
            self._error_cb(str(exc))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _base_opts(self, output_dir: Path, filename_template: str) -> dict:
        return {
            "ffmpeg_location": str(FFMPEG_PATH.parent),
            "outtmpl": str(output_dir / f"{filename_template}.%(ext)s"),
            "progress_hooks": [self._progress_hook],
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "addmetadata": True,
        }

    def _progress_hook(self, d: dict):
        if self._cancel_event.is_set():
            raise yt_dlp.utils.DownloadCancelled("Cancelled by user")

        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            downloaded = d.get("downloaded_bytes", 0)
            percent = min(downloaded / total * 100, 100.0)
            speed = d.get("speed") or 0
            eta = d.get("eta") or 0
            filename = Path(d.get("filename", "")).name
            self._progress_cb(percent, speed, eta, filename)
        elif status == "finished":
            self._current_filepath = d.get("filename", "")

    def _run_download(self, url: str, opts: dict):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filepath = self._resolve_output_path(opts, info)
                metadata = {
                    "title": info.get("title", ""),
                    "uploader": info.get("uploader") or info.get("channel", ""),
                    "duration": info.get("duration", 0),
                    "thumbnail_url": info.get("thumbnail", ""),
                    "platform": info.get("extractor_key", ""),
                    "filesize": info.get("filesize") or info.get("filesize_approx", 0),
                }
                self._completion_cb(filepath, metadata)
        except yt_dlp.utils.DownloadCancelled:
            logger.info("Download cancelled by user")
        except yt_dlp.utils.DownloadError as exc:
            self._error_cb(str(exc))
        except Exception as exc:
            logger.exception("Unexpected download error")
            self._error_cb(str(exc))

    def _resolve_output_path(self, opts: dict, info: dict) -> str:
        """Try to determine the actual output filepath after download."""
        if self._current_filepath:
            # Strip any .part suffix if present
            fp = self._current_filepath
            if fp.endswith(".part"):
                fp = fp[:-5]
            return fp
        # Fallback: reconstruct from template
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.prepare_filename(info)
        except Exception:
            return ""

    def _run_spotdl(self, url: str, output_dir: Path, quality: str):
        """Run spotdl via its Python API or subprocess fallback."""
        bitrate = AUDIO_QUALITY_MAP.get(quality, "320")
        try:
            from spotdl import Spotdl
            from spotdl.types.options import DownloaderOptions

            downloader_options = DownloaderOptions(
                output=str(output_dir / "{title}"),
                bitrate=f"{bitrate}k",
                ffmpeg=str(FFMPEG_PATH),
            )
            with Spotdl(
                client_id="",
                client_secret="",
                downloader_settings=downloader_options,
            ) as spotdl_instance:
                songs, _ = spotdl_instance.search([url])
                for i, song in enumerate(songs):
                    if self._cancel_event.is_set():
                        break
                    percent = (i / max(len(songs), 1)) * 100
                    self._progress_cb(percent, 0, 0, song.name)
                    spotdl_instance.download(song)
                self._completion_cb(str(output_dir), {"title": "Spotify download", "platform": "Spotify"})
        except ImportError:
            # Subprocess fallback
            import subprocess
            cmd = [
                "spotdl",
                url,
                "--output", str(output_dir / "{title}"),
                "--bitrate", f"{bitrate}k",
                "--ffmpeg", str(FFMPEG_PATH),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise RuntimeError(result.stderr or "spotdl failed")
            self._completion_cb(str(output_dir), {"title": "Spotify download", "platform": "Spotify"})
