"""
FFmpeg-based file converter service.
Async with asyncio.Semaphore(2) for max 2 concurrent conversions.
Parses ffmpeg stderr for progress (time= pattern).
"""

import asyncio
import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..config import settings

logger = logging.getLogger("yuki.converter")

_semaphore: Optional[asyncio.Semaphore] = None
_jobs: dict[str, "ConversionJob"] = {}


def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.max_concurrent_conversions)
    return _semaphore


@dataclass
class ConversionJob:
    job_id: str
    input_path: str
    output_path: str = ""
    status: str = "waiting"   # waiting|converting|done|failed|cancelled
    progress_pct: float = 0
    error: str = ""
    duration_s: float = 0
    _cancel: asyncio.Event = field(default_factory=asyncio.Event, repr=False)


def get_job(job_id: str) -> Optional[ConversionJob]:
    return _jobs.get(job_id)


def get_active_jobs() -> list[ConversionJob]:
    return [j for j in _jobs.values() if j.status not in ("done", "error", "cancelled")]


def get_all_jobs() -> list[ConversionJob]:
    return list(_jobs.values())


def cancel_job(job_id: str) -> bool:
    job = _jobs.get(job_id)
    if not job:
        return False
    job._cancel.set()
    job.status = "cancelled"
    return True


async def start_conversion(
    files: list[str],
    output_format: str,
    quality: dict,
    output_dir: str,
    filename_mode: str = "keep",
    filename_suffix: str = "",
    filename_pattern: str = "{name}_{format}",
    create_subfolder: bool = False,
) -> list[str]:
    job_ids = []
    for input_path in files:
        job_id = str(uuid.uuid4())
        out_path = _resolve_output_path(
            input_path, output_format, output_dir,
            filename_mode, filename_suffix, filename_pattern, create_subfolder
        )
        job = ConversionJob(job_id=job_id, input_path=input_path, output_path=out_path)
        _jobs[job_id] = job
        asyncio.create_task(_run_conversion(job, output_format, quality))
        job_ids.append(job_id)
    return job_ids


def _resolve_output_path(
    input_path: str, output_format: str, output_dir: str,
    filename_mode: str, suffix: str, pattern: str, create_subfolder: bool
) -> str:
    p = Path(input_path)
    base_dir = Path(output_dir) if output_dir else p.parent
    if create_subfolder:
        base_dir = base_dir / "Yuki Converted"
    base_dir.mkdir(parents=True, exist_ok=True)

    ext = f".{output_format.lower()}"
    if filename_mode == "keep":
        name = p.stem
    elif filename_mode == "suffix":
        name = f"{p.stem}_{suffix or output_format}"
    else:
        import datetime
        name = pattern.format(
            name=p.stem,
            format=output_format.lower(),
            date=datetime.date.today().strftime("%Y%m%d"),
        )
    return str(base_dir / (name + ext))


def _build_ffmpeg_cmd(
    input_path: str,
    output_path: str,
    output_format: str,
    quality: dict,
) -> list[str]:
    fmt = output_format.lower()
    cmd = [settings.ffmpeg_path, "-y", "-i", input_path]

    audio_formats = {"mp3", "wav", "flac", "ogg", "aac", "opus", "m4a", "wma"}
    video_formats = {"mp4", "mkv", "avi", "mov", "webm", "gif"}

    if fmt in audio_formats:
        bitrate = quality.get("audio_bitrate", "320k")
        sample_rate = quality.get("sample_rate", "44100")
        if fmt == "mp3":
            cmd += ["-acodec", "libmp3lame", "-b:a", bitrate, "-ar", sample_rate]
        elif fmt == "flac":
            cmd += ["-acodec", "flac", "-ar", sample_rate]
        elif fmt in ("ogg",):
            cmd += ["-acodec", "libvorbis", "-b:a", bitrate, "-ar", sample_rate]
        elif fmt == "opus":
            cmd += ["-acodec", "libopus", "-b:a", bitrate, "-ar", sample_rate]
        elif fmt == "aac":
            cmd += ["-acodec", "aac", "-b:a", bitrate, "-ar", sample_rate]
        elif fmt == "m4a":
            cmd += ["-acodec", "aac", "-b:a", bitrate, "-ar", sample_rate]
        else:
            cmd += ["-b:a", bitrate, "-ar", sample_rate]
    elif fmt in video_formats:
        vcodec_map = {"h264": "libx264", "h265": "libx265", "vp9": "libvpx-vp9"}
        codec = vcodec_map.get(quality.get("video_codec", "h264"), "libx264")
        resolution = quality.get("video_resolution", "original")
        vab = quality.get("video_audio_bitrate", "192k")
        if resolution != "original" and fmt != "gif":
            h = resolution.replace("p", "")
            cmd += ["-vf", f"scale=-2:{h}"]
        if fmt == "gif":
            cmd += ["-vf", "fps=10,scale=320:-1:flags=lanczos", "-loop", "0"]
        else:
            cmd += ["-vcodec", codec, "-acodec", "aac", "-b:a", vab]

    cmd.append(output_path)
    return cmd


_TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")


async def _run_conversion(job: ConversionJob, output_format: str, quality: dict) -> None:
    async with get_semaphore():
        if job._cancel.is_set():
            return
        job.status = "converting"
        try:
            # Get duration first
            probe_cmd = [
                settings.ffprobe_path, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                job.input_path,
            ]
            try:
                probe = await asyncio.create_subprocess_exec(
                    *probe_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                stdout, _ = await probe.communicate()
                job.duration_s = float(stdout.decode().strip() or 0)
            except Exception:
                job.duration_s = 0

            cmd = _build_ffmpeg_cmd(
                job.input_path, job.output_path, output_format, quality
            )
            logger.info("ffmpeg command: %s", " ".join(cmd))
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )

            # Read stderr for progress
            while True:
                if job._cancel.is_set():
                    proc.kill()
                    job.status = "cancelled"
                    return
                line = await proc.stderr.readline()
                if not line:
                    break
                text = line.decode(errors="replace")
                m = _TIME_RE.search(text)
                if m and job.duration_s > 0:
                    h, mn, s = m.groups()
                    elapsed = int(h) * 3600 + int(mn) * 60 + float(s)
                    job.progress_pct = min(elapsed / job.duration_s * 100, 99.0)

            await proc.wait()
            logger.info("ffmpeg returncode: %s for %s", proc.returncode, job.input_path)
            if proc.returncode == 0:
                job.status = "done"
                job.progress_pct = 100
            else:
                job.status = "error"
                job.error = f"ffmpeg exited with code {proc.returncode}"
        except Exception as exc:
            job.status = "error"
            job.error = str(exc)
            logger.error("Conversion failed for %s: %s", job.input_path, exc)
