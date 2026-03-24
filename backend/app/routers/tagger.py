"""Tagger router — ID3/MP4 tag read/write/cover art/rename."""

import asyncio
import base64
import io
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..schemas import (
    TaggerReadRequest, TagsRead, TagsWriteRequest,
    CoverFromUrlRequest, RenameRequest, AutoNameRequest
)
from ..services.tagger import MP3Tagger

logger = logging.getLogger("yuki.routers.tagger")
router = APIRouter(prefix="/tagger", tags=["tagger"])
_tagger = MP3Tagger()


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
    if not Path(body.filepath).exists():
        raise HTTPException(404, f"File not found: {body.filepath}")
    try:
        tags = await asyncio.to_thread(_tagger.read_tags, body.filepath)
        cover = await asyncio.to_thread(_encode_cover, body.filepath)
        p = Path(body.filepath)
        size = p.stat().st_size
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
    if not Path(body.filepath).exists():
        raise HTTPException(404, f"File not found: {body.filepath}")
    tags = body.model_dump(exclude={"filepath", "cover_art_b64"})
    try:
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
    ok, result = await asyncio.to_thread(_tagger.rename_file, body.filepath, body.new_name)
    if ok:
        return {"ok": True, "new_filepath": result}
    raise HTTPException(400, result)


@router.get("/auto-name")
async def auto_name(filepath: str):
    if not Path(filepath).exists():
        raise HTTPException(404, "File not found")
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
