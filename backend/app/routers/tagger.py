"""Tagger router — ID3/MP4 tag read/write/cover art/rename."""

import asyncio
import base64
import io
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..schemas import (
    TaggerReadRequest, TagsRead, TagsWriteRequest,
    CoverFromUrlRequest, RenameRequest, AutoNameRequest,
    BatchSaveRequest, BatchSaveResult,
)
from ..services.tagger import MP3Tagger

logger = logging.getLogger("yuki.routers.tagger")
router = APIRouter(prefix="/tagger", tags=["tagger"])
_tagger = MP3Tagger()


async def _validate_audio_filepath(filepath: str) -> Path:
    """Resolve and validate a user-supplied file path."""
    p = Path(filepath).resolve()
    exists = await asyncio.to_thread(p.exists)
    if not exists:
        raise HTTPException(status_code=404, detail="File not found")
    is_file = await asyncio.to_thread(p.is_file)
    if not is_file:
        raise HTTPException(status_code=400, detail="Path is not a file")
    # Reject access to system directories
    p_str = str(p).lower()
    for forbidden in ("c:\\windows", "c:\\program files"):
        if p_str.startswith(forbidden):
            raise HTTPException(status_code=403, detail="Access to system directories is not allowed")
    return p


def _encode_cover(filepath: str) -> str | None:
    try:
        img = _tagger.get_cover_art(filepath)
        if img:
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=85)
            return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        pass
    return None


@router.post("/read", response_model=TagsRead)
async def read_tags(body: TaggerReadRequest):
    await _validate_audio_filepath(body.filepath)
    try:
        tags = await asyncio.to_thread(_tagger.read_tags, body.filepath)
        cover = await asyncio.to_thread(_encode_cover, body.filepath)
        p = Path(body.filepath)
        stat = await asyncio.to_thread(p.stat)
        size = stat.st_size
        duration = 0
        try:
            import mutagen
            audio = mutagen.File(body.filepath)
            if audio and hasattr(audio, "info"):
                duration = int(audio.info.length)
        except Exception:
            pass
        return TagsRead(
            filepath=body.filepath,
            title=tags.get("title", ""),
            artist=tags.get("artist", ""),
            album=tags.get("album", ""),
            album_artist=tags.get("album_artist", ""),
            year=tags.get("year", ""),
            genre=tags.get("genre", ""),
            track_number=tags.get("track_number", ""),
            total_tracks=tags.get("total_tracks", ""),
            disc_number=tags.get("disc_number", ""),
            bpm=tags.get("bpm", ""),
            composer=tags.get("composer", ""),
            comment=tags.get("comment", ""),
            cover_art_b64=cover,
            filesize=size,
            duration=duration,
            filename=p.name,
        )
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/write")
async def write_tags(body: TagsWriteRequest):
    await _validate_audio_filepath(body.filepath)
    tags = {k: v for k, v in body.model_dump(exclude={"filepath", "cover_art_b64"}).items() if v is not None and str(v).strip() != ''}
    try:
        if tags:
            await asyncio.to_thread(_tagger.write_tags, body.filepath, tags)
        # Handle cover art if provided as data URI
        if body.cover_art_b64:
            b64 = body.cover_art_b64
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            img_bytes = base64.b64decode(b64)
            # Write via temp file approach
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                tf.write(img_bytes)
                tmp_path = tf.name
            try:
                await asyncio.to_thread(_tagger.set_cover_art, body.filepath, tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/batch-save", response_model=BatchSaveResult)
async def batch_save(body: BatchSaveRequest):
    if not body.filepaths:
        raise HTTPException(400, "No files provided")
    try:
        result = await asyncio.to_thread(
            _tagger.batch_write_tags, body.filepaths, body.tags
        )
        return BatchSaveResult(**result)
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/cover-from-url")
async def cover_from_url(body: CoverFromUrlRequest):
    url = body.url.strip()
    if not url.startswith("https://"):
        raise HTTPException(400, "Cover URL must use HTTPS")
    try:
        import requests as req
        resp = req.get(url, timeout=10)
        resp.raise_for_status()
        from PIL import Image
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        return {"cover_art_b64": b64}
    except Exception as exc:
        raise HTTPException(400, f"Failed to fetch cover: {exc}")


@router.post("/rename")
async def rename(body: RenameRequest):
    await _validate_audio_filepath(body.filepath)
    ok, result = await asyncio.to_thread(_tagger.rename_file, body.filepath, body.new_name)
    if ok:
        return {"ok": True, "new_filepath": result}
    raise HTTPException(400, result)


@router.get("/auto-name")
async def auto_name(filepath: str):
    await _validate_audio_filepath(filepath)
    try:
        tags = await asyncio.to_thread(_tagger.read_tags, filepath)
        artist = tags.get("artist", "")
        title = tags.get("title", "")
        import re
        if artist and title:
            name = re.sub(r'[\\/:*?"<>|]', "", f"{artist} - {title}")
        elif title:
            name = re.sub(r'[\\/:*?"<>|]', "", title)
        else:
            name = Path(filepath).stem
        return {"suggested_name": name}
    except Exception as exc:
        raise HTTPException(400, str(exc))
