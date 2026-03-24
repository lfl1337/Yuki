"""Pydantic request/response schemas."""

from typing import Optional
from pydantic import BaseModel


# ---- Download ----

class DownloadStartRequest(BaseModel):
    url: str
    format: str = "audio"       # "audio" | "video"
    quality: str = "320kbps"
    output_dir: str = ""


class BatchDownloadRequest(BaseModel):
    urls: list[str]
    format: str = "audio"
    quality: str = "320kbps"
    output_dir: str = ""


class DownloadJobRead(BaseModel):
    job_id: str
    url: str
    format: str
    quality: str
    status: str
    title: str = ""
    artist: str = ""
    platform: str = ""
    thumbnail_url: str = ""
    progress_pct: float = 0
    speed: float = 0
    eta: int = 0
    filepath: str = ""
    error: str = ""


class DetectResult(BaseModel):
    platform: str
    valid: bool
    type: str
    title: str = ""
    thumbnail_url: str = ""
    duration: int = 0
    uploader: str = ""


# ---- History ----

class HistoryEntryRead(BaseModel):
    id: str
    title: str
    artist: str
    platform: str
    format: str
    quality: str
    filepath: str
    thumbnail_url: str
    duration: int
    filesize: int
    url: str
    downloaded_at: str


class HistoryPage(BaseModel):
    items: list[HistoryEntryRead]
    total: int
    pages: int


# ---- Player ----

class PlayerLoadRequest(BaseModel):
    filepath: str


class PlayerSeekRequest(BaseModel):
    position: float  # seconds


class PlayerVolumeRequest(BaseModel):
    volume: float  # 0.0 - 1.0


class PlayerStatus(BaseModel):
    is_playing: bool = False
    is_paused: bool = False
    position: float = 0
    duration: float = 0
    volume: float = 0.8
    filepath: str = ""
    title: str = ""
    artist: str = ""
    cover_art_b64: Optional[str] = None  # data URI


# ---- Tagger ----

class TaggerReadRequest(BaseModel):
    filepath: str


class TagsRead(BaseModel):
    filepath: str
    title: str = ""
    artist: str = ""
    album: str = ""
    album_artist: str = ""
    year: str = ""
    genre: str = ""
    track_number: str = ""
    total_tracks: str = ""
    disc_number: str = ""
    bpm: str = ""
    composer: str = ""
    comment: str = ""
    cover_art_b64: Optional[str] = None  # data URI
    filesize: int = 0
    duration: int = 0
    filename: str = ""


class TagsWriteRequest(BaseModel):
    filepath: str
    title: str = ""
    artist: str = ""
    album: str = ""
    album_artist: str = ""
    year: str = ""
    genre: str = ""
    track_number: str = ""
    total_tracks: str = ""
    disc_number: str = ""
    bpm: str = ""
    composer: str = ""
    comment: str = ""
    cover_art_b64: Optional[str] = None


class CoverFromUrlRequest(BaseModel):
    url: str


class RenameRequest(BaseModel):
    filepath: str
    new_name: str


class AutoNameRequest(BaseModel):
    filepath: str


class BatchSaveRequest(BaseModel):
    filepaths: list[str]
    tags: dict[str, str]


class BatchSaveFailure(BaseModel):
    file: str
    error: str


class BatchSaveResult(BaseModel):
    success: list[str]
    failed: list[BatchSaveFailure]
    total: int
    succeeded: int
    failed_count: int


# ---- Converter ----

class QualitySettings(BaseModel):
    audio_bitrate: str = "320k"     # "128k","192k","256k","320k"
    sample_rate: str = "44100"
    video_resolution: str = "original"  # "480","720","1080","original"
    video_codec: str = "h264"
    video_audio_bitrate: str = "192k"


class ConverterStartRequest(BaseModel):
    files: list[str]
    output_format: str          # "mp3","wav","mp4", etc.
    quality: QualitySettings = QualitySettings()
    output_dir: str = ""
    filename_mode: str = "keep"  # "keep"|"suffix"|"custom"
    filename_suffix: str = ""
    filename_pattern: str = "{name}_{format}"
    create_subfolder: bool = False


class ConversionJobRead(BaseModel):
    job_id: str
    input_path: str
    output_path: str = ""
    status: str
    progress_pct: float = 0
    error: str = ""


# ---- Settings ----

class SettingSave(BaseModel):
    settings: dict[str, object]


# ---- Updater ----

class UpdaterStatus(BaseModel):
    ytdlp_current: str
    ytdlp_latest: str
    ytdlp_has_update: bool
    app_current: str
    app_latest: str
    app_has_update: bool
