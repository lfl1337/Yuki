"""Converter router — ffmpeg-based file conversion with SSE progress."""

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from ..schemas import ConverterStartRequest, ConversionJobRead
from ..services import converter as conv

logger = logging.getLogger("yuki.routers.converter")
router = APIRouter(prefix="/converter", tags=["converter"])


def _job_to_read(job) -> ConversionJobRead:
    return ConversionJobRead(
        job_id=job.job_id,
        input_path=job.input_path,
        output_path=job.output_path,
        status=job.status,
        progress_pct=round(job.progress_pct, 1),
        error=job.error,
    )


@router.post("/start")
async def start(body: ConverterStartRequest):
    if not body.files:
        raise HTTPException(400, "No files provided")
    job_ids = await conv.start_conversion(
        files=body.files,
        output_format=body.output_format,
        quality=body.quality.model_dump(),
        output_dir=body.output_dir,
        filename_mode=body.filename_mode,
        filename_suffix=body.filename_suffix,
        filename_pattern=body.filename_pattern,
        create_subfolder=body.create_subfolder,
    )
    return {"job_ids": job_ids}


@router.get("/status/{job_id}", response_model=ConversionJobRead)
async def get_status(job_id: str):
    job = conv.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return _job_to_read(job)


@router.delete("/cancel/{job_id}")
async def cancel(job_id: str):
    ok = conv.cancel_job(job_id)
    return {"ok": ok}


@router.get("/stream")
async def stream(request: Request):
    """SSE: all conversion jobs every 500ms."""
    async def generator():
        import asyncio
        while True:
            if await request.is_disconnected():
                break
            jobs = [_job_to_read(j).model_dump() for j in conv.get_all_jobs()]
            yield {"data": json.dumps(jobs)}
            await asyncio.sleep(0.5)
    return EventSourceResponse(generator())
