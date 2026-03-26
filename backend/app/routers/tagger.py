"""Tagger router — ID3/MP4 tag read/write/cover art/rename."""

import asyncio
import base64
import io
import ipaddress
import logging
import os
import socket
from pathlib import Path
from urllib.parse import urlparse

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

_ALLOWED_AUDIO_EXTENSIONS = frozenset({
    ".mp3", ".flac", ".wav", ".ogg", ".aac", ".m4a", ".opus",
    ".wma", ".mp4", ".mkv", ".avi", ".mov", ".webm",
})

_FORBIDDEN_PATH_PREFIXES = (
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\programdata",
    "c:\\system volume information",
)


async def _validate_audio_filepath(filepath: str) -> str:
    """
    Sanitize and validate a user-supplied file path.

    Returns the normalized absolute path as a plain string.
    All callers MUST use this return value — never the original user input.

    Sanitization steps (all before any filesystem access):
      1. os.path.normpath(os.path.abspath()) — pure-string normalization,
         no symlink resolution and therefore no filesystem sink at this step.
      2. File-extension allowlist check.
      3. Forbidden system-directory blocklist check.

    Filesystem existence checks use the already-sanitized *normalized* string,
    not the original *filepath* argument.
    """
    # Pure-string normalization — no filesystem access, no symlink following.
    normalized = os.path.normpath(os.path.abspath(filepath))

    # 1. Extension allowlist — evaluated on the normalized string only.
    _, ext = os.path.splitext(normalized)
    if ext.lower() not in _ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")

    # 2. Forbidden system directories — blocklist on normalized string.
    normalized_lower = normalized.lower()
    for forbidden in _FORBIDDEN_PATH_PREFIXES:
        if normalized_lower.startswith(forbidden):
            raise HTTPException(
                status_code=403,
                detail="Access to system directories is not allowed",
            )

    # 3. Filesystem checks — performed on `normalized`, not on raw `filepath`.
    p = Path(normalized)
    if not await asyncio.to_thread(p.exists):
        raise HTTPException(status_code=404, detail="File not found")
    if not await asyncio.to_thread(p.is_file):
        raise HTTPException(status_code=400, detail="Path is not a file")

    return normalized


def _is_safe_cover_url(url: str) -> bool:
    """Block SSRF: only allow HTTPS URLs that resolve to public IP addresses."""
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname.lower() in ("localhost", "metadata.google.internal"):
            return False
        try:
            ip = ipaddress.ip_address(socket.gethostbyname(hostname))
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except (socket.gaierror, ValueError):
            return False
        return True
    except Exception:
        return False


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
    safe = await _validate_audio_filepath(body.filepath)
    try:
        tags = await asyncio.to_thread(_tagger.read_tags, safe)
        cover = await asyncio.to_thread(_encode_cover, safe)
        p = Path(safe)
        stat = await asyncio.to_thread(p.stat)
        size = stat.st_size
        duration = 0
        try:
            import mutagen
            audio = mutagen.File(safe)
            if audio and hasattr(audio, "info"):
                duration = int(audio.info.length)
        except Exception:
            pass
        return TagsRead(
            filepath=safe,
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
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/write")
async def write_tags(body: TagsWriteRequest):
    safe = await _validate_audio_filepath(body.filepath)
    tags = {
        k: v
        for k, v in body.model_dump(exclude={"filepath", "cover_art_b64"}).items()
        if v is not None and str(v).strip() != ""
    }
    try:
        if tags:
            await asyncio.to_thread(_tagger.write_tags, safe, tags)
        if body.cover_art_b64:
            b64 = body.cover_art_b64
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            img_bytes = base64.b64decode(b64)
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                tf.write(img_bytes)
                tmp_path = tf.name
            try:
                await asyncio.to_thread(_tagger.set_cover_art, safe, tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        return {"ok": True}
    except HTTPException:
        raise
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
    if not _is_safe_cover_url(url):
        raise HTTPException(400, "Cover URL must use HTTPS and point to a public host")
    try:
        import requests as req
        # Reconstruct the URL from parsed components so the raw user-supplied
        # string does not flow directly into the HTTP client.
        parsed = urlparse(url)
        safe_url = f"https://{parsed.netloc}{parsed.path}"
        if parsed.query:
            safe_url += f"?{parsed.query}"
        resp = req.get(safe_url, timeout=10)
        resp.raise_for_status()
        from PIL import Image
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        return {"cover_art_b64": b64}
    except HTTPException:
        raise
    except Exception:
        logger.warning("Failed to fetch cover from URL", exc_info=True)
        raise HTTPException(400, "Failed to fetch cover image")


@router.post("/rename")
async def rename(body: RenameRequest):
    safe = await _validate_audio_filepath(body.filepath)
    ok, result = await asyncio.to_thread(_tagger.rename_file, safe, body.new_name)
    if ok:
        return {"ok": True, "new_filepath": result}
    raise HTTPException(400, result)


@router.get("/auto-name")
async def auto_name(filepath: str):
    safe = await _validate_audio_filepath(filepath)
    try:
        tags = await asyncio.to_thread(_tagger.read_tags, safe)
        artist = tags.get("artist", "")
        title = tags.get("title", "")
        import re
        if artist and title:
            name = re.sub(r'[\\/:*?"<>|]', "", f"{artist} - {title}")
        elif title:
            name = re.sub(r'[\\/:*?"<>|]', "", title)
        else:
            name = Path(safe).stem
        return {"suggested_name": name}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, str(exc))
