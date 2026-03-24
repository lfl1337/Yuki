"""
MP3/M4A tag reader and writer using mutagen.
Supports ID3 (MP3) and MP4/M4A tags with cover art embedding.
"""

import io
import logging
from pathlib import Path
from typing import Optional, Union

import requests
from mutagen.id3 import (
    ID3,
    ID3NoHeaderError,
    TIT2, TPE1, TALB, TPE2, TDRC, TCON, TRCK, TPOS, COMM,
    TCOM, TBPM, APIC,
)
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image

logger = logging.getLogger(__name__)


def safe_int(value) -> Optional[int]:
    """Convert value to int, returning None for empty/invalid input."""
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None

TAG_MAP_ID3 = {
    "title": TIT2,
    "artist": TPE1,
    "album": TALB,
    "album_artist": TPE2,
    "year": TDRC,
    "genre": TCON,
    "composer": TCOM,
    "bpm": TBPM,
}

TAG_MAP_MP4 = {
    "title": "\xa9nam",
    "artist": "\xa9ART",
    "album": "\xa9alb",
    "album_artist": "aART",
    "year": "\xa9day",
    "genre": "\xa9gen",
    "composer": "\xa9wrt",
    "bpm": "tmpo",
    "comment": "\xa9cmt",
    "track_number": "trkn",
    "disc_number": "disk",
}


class MP3Tagger:
    """Read and write audio file metadata using mutagen."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_tags(self, filepath: Union[str, Path]) -> dict:
        """Return dict of all readable tags from the file."""
        filepath = Path(filepath)
        ext = filepath.suffix.lower()
        try:
            if ext in (".mp3",):
                result = self._read_id3(filepath)
            elif ext in (".m4a", ".mp4", ".aac"):
                result = self._read_mp4(filepath)
            else:
                result = self._read_id3(filepath)
            logger.info("Tags read: %s", filepath)
            return result
        except Exception as exc:
            logger.error("Tag read failed: %s — %s", filepath, exc)
            return {}

    def write_tags(self, filepath: Union[str, Path], tags: dict):
        """Write the provided tags dict to the file."""
        filepath = Path(filepath)
        ext = filepath.suffix.lower()
        try:
            if ext in (".mp3",):
                self._write_id3(filepath, tags)
            elif ext in (".m4a", ".mp4", ".aac"):
                self._write_mp4(filepath, tags)
            else:
                self._write_id3(filepath, tags)
            logger.info("Tags saved: %s", filepath)
        except Exception as exc:
            logger.error("Tag save failed: %s — %s", filepath, exc)
            raise

    def set_cover_art(self, filepath: Union[str, Path], source: Union[str, Path]):
        """
        Embed cover art from a local file path or HTTP URL.
        source can be a file path (str/Path) or an HTTP URL string.
        """
        filepath = Path(filepath)
        image_data, mime = self._load_image_bytes(source)
        if not image_data:
            return
        ext = filepath.suffix.lower()
        try:
            if ext in (".mp3",):
                self._set_cover_id3(filepath, image_data, mime)
            elif ext in (".m4a", ".mp4", ".aac"):
                self._set_cover_mp4(filepath, image_data, mime)
            else:
                self._set_cover_id3(filepath, image_data, mime)
            logger.info("Cover art embedded: %s", filepath)
        except Exception as exc:
            logger.error("set_cover_art failed: %s", exc)
            raise

    def get_cover_art(self, filepath: Union[str, Path]) -> Optional[Image.Image]:
        """Return embedded cover art as a PIL Image, or None."""
        filepath = Path(filepath)
        ext = filepath.suffix.lower()
        try:
            if ext in (".mp3",):
                return self._get_cover_id3(filepath)
            elif ext in (".m4a", ".mp4", ".aac"):
                return self._get_cover_mp4(filepath)
            else:
                return self._get_cover_id3(filepath)
        except Exception as exc:
            logger.error("get_cover_art failed: %s", exc)
            return None

    def clear_all_tags(self, filepath: Union[str, Path]):
        """Remove all metadata from the file."""
        filepath = Path(filepath)
        ext = filepath.suffix.lower()
        try:
            if ext in (".mp3",):
                audio = MP3(filepath)
                audio.tags = None
                audio.save(filepath, v1=0, v2_version=3)
            elif ext in (".m4a", ".mp4", ".aac"):
                audio = MP4(filepath)
                audio.clear()
                audio.save()
            else:
                from mutagen import File as MuFile
                audio = MuFile(filepath)
                if audio and audio.tags:
                    audio.tags.clear()
                    audio.save()
        except Exception as exc:
            logger.error("clear_all_tags failed: %s", exc)
            raise

    def rename_file(self, current_path: Union[str, Path], new_name: str) -> tuple:
        import re
        current_path = Path(current_path)
        if not current_path.exists():
            return (False, "File not found")
        stripped = new_name.strip()
        if not stripped:
            return (False, "Filename cannot be empty")
        if re.search(r'[\\/:*?"<>|]', stripped):
            return (False, 'Filename contains illegal characters: \\ / : * ? " < > |')
        new_path = current_path.parent / (stripped + current_path.suffix)
        if new_path.exists() and new_path != current_path:
            return (False, "A file with that name already exists")
        try:
            current_path.rename(new_path)
            return (True, str(new_path))
        except PermissionError:
            return (False, "Permission denied — file may be in use")
        except OSError as exc:
            return (False, f"Rename failed: {exc}")

    # ------------------------------------------------------------------
    # ID3 helpers
    # ------------------------------------------------------------------

    def _read_id3(self, filepath: Path) -> dict:
        try:
            audio = MP3(filepath, ID3=ID3)
        except ID3NoHeaderError:
            return {}
        tags = audio.tags
        if not tags:
            return {}
        result = {}
        for key, frame_cls in TAG_MAP_ID3.items():
            frame = tags.get(frame_cls.__name__)
            if frame:
                result[key] = str(frame.text[0]) if hasattr(frame, "text") else str(frame)
        # Track number
        trck = tags.get("TRCK")
        if trck:
            parts = str(trck.text[0]).split("/")
            result["track_number"] = parts[0]
            if len(parts) > 1:
                result["total_tracks"] = parts[1]
        # Disc number
        tpos = tags.get("TPOS")
        if tpos:
            parts = str(tpos.text[0]).split("/")
            result["disc_number"] = parts[0]
        # Comment
        for key in tags.keys():
            if key.startswith("COMM"):
                result["comment"] = str(tags[key].text[0])
                break
        return result

    def _write_id3(self, filepath: Path, tags: dict):
        try:
            audio = MP3(filepath, ID3=ID3)
        except Exception:
            audio = MP3(filepath)
        if audio.tags is None:
            audio.add_tags()
        id3 = audio.tags
        for key, frame_cls in TAG_MAP_ID3.items():
            if key in tags and tags[key] is not None:
                id3.setall(frame_cls.__name__, [frame_cls(text=str(tags[key]))])
        if "track_number" in tags:
            trck = str(tags["track_number"])
            if "total_tracks" in tags:
                trck += f"/{tags['total_tracks']}"
            id3.setall("TRCK", [TRCK(text=trck)])
        if "disc_number" in tags:
            id3.setall("TPOS", [TPOS(text=str(tags["disc_number"]))])
        if "comment" in tags:
            id3.setall("COMM::eng", [COMM(text=str(tags["comment"]), lang="eng", desc="")])
        audio.save(filepath, v2_version=3)

    def _set_cover_id3(self, filepath: Path, data: bytes, mime: str):
        try:
            audio = MP3(filepath, ID3=ID3)
        except Exception:
            audio = MP3(filepath)
        if audio.tags is None:
            audio.add_tags()
        audio.tags.setall(
            "APIC",
            [
                APIC(
                    encoding=3,
                    mime=mime,
                    type=3,  # Front cover
                    desc="Cover",
                    data=data,
                )
            ],
        )
        audio.save(filepath, v2_version=3)

    def _get_cover_id3(self, filepath: Path) -> Optional[Image.Image]:
        try:
            audio = MP3(filepath, ID3=ID3)
        except Exception:
            return None
        if not audio.tags:
            return None
        for key in audio.tags.keys():
            if key.startswith("APIC"):
                apic = audio.tags[key]
                return Image.open(io.BytesIO(apic.data))
        return None

    # ------------------------------------------------------------------
    # MP4/M4A helpers
    # ------------------------------------------------------------------

    def _read_mp4(self, filepath: Path) -> dict:
        audio = MP4(filepath)
        result = {}
        for key, mp4_key in TAG_MAP_MP4.items():
            val = audio.tags.get(mp4_key) if audio.tags else None
            if val:
                if key == "bpm":
                    result[key] = str(val[0])
                elif key in ("track_number", "disc_number"):
                    pair = val[0]
                    result[key] = str(pair[0])
                    if pair[1]:
                        suffix = "total_tracks" if key == "track_number" else "total_discs"
                        result[suffix] = str(pair[1])
                else:
                    result[key] = str(val[0])
        return result

    def _write_mp4(self, filepath: Path, tags: dict):
        audio = MP4(filepath)
        if audio.tags is None:
            audio.add_tags()
        for key, mp4_key in TAG_MAP_MP4.items():
            if key not in tags or tags[key] is None:
                continue
            val = tags[key]
            if key == "bpm":
                bpm_val = safe_int(val)
                if bpm_val is not None:
                    audio.tags[mp4_key] = [bpm_val]
            elif key == "track_number":
                track_val = safe_int(val)
                if track_val is not None:
                    total = safe_int(tags.get("total_tracks")) or 0
                    audio.tags[mp4_key] = [(track_val, total)]
            elif key == "disc_number":
                disc_val = safe_int(val)
                if disc_val is not None:
                    audio.tags[mp4_key] = [(disc_val, 0)]
            else:
                audio.tags[mp4_key] = [str(val)]
        audio.save()

    def _set_cover_mp4(self, filepath: Path, data: bytes, mime: str):
        audio = MP4(filepath)
        if audio.tags is None:
            audio.add_tags()
        fmt = MP4Cover.FORMAT_PNG if "png" in mime else MP4Cover.FORMAT_JPEG
        audio.tags["covr"] = [MP4Cover(data, imageformat=fmt)]
        audio.save()

    def _get_cover_mp4(self, filepath: Path) -> Optional[Image.Image]:
        audio = MP4(filepath)
        if not audio.tags:
            return None
        covers = audio.tags.get("covr")
        if covers:
            return Image.open(io.BytesIO(bytes(covers[0])))
        return None

    # ------------------------------------------------------------------
    # Image loading
    # ------------------------------------------------------------------

    def _load_image_bytes(self, source: Union[str, Path]) -> tuple:
        """Returns (bytes, mime_type) or (None, None)."""
        try:
            if isinstance(source, str) and source.lower().startswith("https://"):
                resp = requests.get(source, timeout=10)
                resp.raise_for_status()
                data = resp.content
                ct = resp.headers.get("Content-Type", "image/jpeg")
                mime = ct.split(";")[0].strip()
            else:
                path = Path(source)
                data = path.read_bytes()
                ext = path.suffix.lower()
                mime = "image/png" if ext == ".png" else "image/jpeg"
            # Normalize to JPEG for compatibility
            img = Image.open(io.BytesIO(data)).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            return buf.getvalue(), "image/jpeg"
        except Exception as exc:
            logger.error("_load_image_bytes failed: %s", exc)
            return None, None
