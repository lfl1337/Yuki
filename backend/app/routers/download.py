"""Download router — yt-dlp + spotdl downloads with SSE progress stream."""

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from ..schemas import (
    DownloadStartRequest, BatchDownloadRequest,
    DownloadJobRead, DetectResult
)
from ..services import downloader as dl
from ..services.detector import detect_platform
from ..config import settings

logger = logging.getLogger("yuki.routers.download")
router = APIRouter(prefix="/download", tags=["download"])


def _job_to_read(job) -> DownloadJobRead:
    return DownloadJobRead(
        job_id=job.job_id,
        url=job.url,
        format=job.format,
        quality=job.quality,
        status=job.status,
        title=job.title,
        artist=job.artist,
        platform=job.platform,
        thumbnail_url=job.thumbnail_url,
        progress_pct=round(job.progress_pct, 1),
        speed=job.speed,
        eta=job.eta,
        filepath=job.filepath,
        error=job.error,
    )


@router.post("/start", response_model=DownloadJobRead)
async def start_download(body: DownloadStartRequest):
    if not body.url.strip():
        raise HTTPException(400, "URL is required")
    output_dir = body.output_dir or settings.data_dir + "/Downloads"
    job_id = dl.start_download(
        url=body.url.strip(),
        fmt=body.format,
        quality=body.quality,
        output_dir=output_dir,
    )
    job = dl.get_job(job_id)
    return _job_to_read(job)


@router.post("/batch")
async def batch_download(body: BatchDownloadRequest):
    if not body.urls:
        raise HTTPException(400, "No URLs provided")
    output_dir = body.output_dir or settings.data_dir + "/Downloads"
    job_ids = []
    for url in body.urls:
        url = url.strip()
        if not url:
            continue
        detected = detect_platform(url)
        if not detected["valid"]:
            continue
        job_id = dl.start_download(
            url=url, fmt=body.format,
            quality=body.quality, output_dir=output_dir
        )
        job_ids.append(job_id)
    return {"job_ids": job_ids}


@router.get("/status/{job_id}", response_model=DownloadJobRead)
async def get_status(job_id: str):
    job = dl.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return _job_to_read(job)


@router.delete("/cancel/{job_id}")
async def cancel(job_id: str):
    ok = dl.cancel_job(job_id)
    return {"ok": ok}


@router.get("/stream")
async def stream_jobs(request: Request):
    """SSE: pushes all active download jobs every 500ms."""
    async def generator():
        while True:
            if await request.is_disconnected():
                break
            jobs = [_job_to_read(j).model_dump() for j in dl.get_all_jobs()]
            yield {"data": json.dumps(jobs)}
            import asyncio
            await asyncio.sleep(0.5)
    return EventSourceResponse(generator())


@router.get("/detect", response_model=DetectResult)
async def detect(url: str):
    """Fast URL detection + optional metadata fetch."""
    url = url.strip()
    if not url:
        raise HTTPException(400, "URL required")
    result = detect_platform(url)
    if not result["valid"]:
        return DetectResult(platform="Unknown", valid=False, type="video")

    # Try to fetch metadata (non-blocking best-effort)
    try:
        import asyncio
        info = await asyncio.to_thread(dl.get_info, url)
        return DetectResult(
            platform=result["platform"],
            valid=True,
            type=result["type"],
            title=info.get("title", ""),
            thumbnail_url=info.get("thumbnail_url", ""),
            duration=int(info.get("duration", 0)),
            uploader=info.get("uploader", ""),
        )
    except Exception:
        return DetectResult(
            platform=result["platform"],
            valid=True,
            type=result["type"],
        )
