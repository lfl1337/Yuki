"""History router — paginated CRUD + CSV export."""

import csv
import io
import logging
import math

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import HistoryEntry
from ..schemas import HistoryEntryRead, HistoryPage

logger = logging.getLogger("yuki.routers.history")
router = APIRouter(prefix="/history", tags=["history"])

PER_PAGE = 20


def _to_read(e: HistoryEntry) -> HistoryEntryRead:
    return HistoryEntryRead(
        id=e.id, title=e.title, artist=e.artist, platform=e.platform,
        format=e.format, quality=e.quality, filepath=e.filepath,
        thumbnail_url=e.thumbnail_url, duration=e.duration, filesize=e.filesize,
        url=e.url, downloaded_at=e.downloaded_at,
    )


@router.get("", response_model=HistoryPage)
async def get_history(
    search: str = "",
    platform: str = "",
    format: str = "",
    page: int = 1,
    per_page: int = PER_PAGE,
    session: AsyncSession = Depends(get_session),
):
    q = select(HistoryEntry).order_by(HistoryEntry.downloaded_at.desc())
    if search:
        term = f"%{search.lower()}%"
        q = q.where(
            or_(
                HistoryEntry.title.ilike(term),
                HistoryEntry.artist.ilike(term),
                HistoryEntry.platform.ilike(term),
            )
        )
    if platform and platform.lower() != "all":
        if platform.lower() in ("video", "mp4"):
            q = q.where(HistoryEntry.format.in_(["video", "mp4"]))
        elif platform.lower() in ("audio", "mp3"):
            q = q.where(HistoryEntry.format.in_(["audio", "mp3"]))
        else:
            q = q.where(HistoryEntry.platform.ilike(f"%{platform}%"))
    if format and format.lower() not in ("all", ""):
        q = q.where(HistoryEntry.format == format.lower())

    total = await session.scalar(select(func.count()).select_from(q.subquery()))
    pages = math.ceil((total or 0) / per_page)
    offset = (page - 1) * per_page
    result = await session.execute(q.offset(offset).limit(per_page))
    items = [_to_read(e) for e in result.scalars()]
    return HistoryPage(items=items, total=total or 0, pages=pages)


@router.delete("/{entry_id}")
async def delete_entry(entry_id: str, session: AsyncSession = Depends(get_session)):
    entry = await session.get(HistoryEntry, entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    await session.delete(entry)
    await session.commit()
    return {"ok": True}


@router.delete("")
async def clear_history(session: AsyncSession = Depends(get_session)):
    await session.execute(delete(HistoryEntry))
    await session.commit()
    return {"ok": True}


@router.get("/export")
async def export_csv(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(HistoryEntry).order_by(HistoryEntry.downloaded_at.desc())
    )
    entries = result.scalars().all()

    buf = io.StringIO()
    fields = ["id", "title", "artist", "platform", "format", "quality",
              "filepath", "duration", "filesize", "downloaded_at", "url"]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for e in entries:
        writer.writerow({f: getattr(e, f, "") for f in fields})

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=yuki_history.csv"},
    )
