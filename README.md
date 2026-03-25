# Yuki — Media Suite

![Version](https://img.shields.io/badge/version-3.0.0-7C6FCD)
![Platform](https://img.shields.io/badge/platform-Windows-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Download music and videos from YouTube, Spotify, TikTok, Instagram and 1000+ other platforms.
Edit MP3 tags, convert between formats, and listen directly in the app — no Python or runtime required.

---

## Installation

Download the latest installer from [Releases](https://github.com/lfl1337/Yuki/releases) and run it.
No Python, no Node, no additional runtimes needed.

**System requirements:** Windows 10 or later (x64)

---

## Features

**Downloader**
- Supports YouTube, Spotify, TikTok, Instagram, SoundCloud, Twitter/X, Twitch, Reddit, Vimeo and everything yt-dlp covers (1000+ sites)
- MP3 / MP4 with quality selection
- Up to 3 concurrent downloads
- Download queue with live progress and history

**Tag Editor**
- Edit title, artist, album, year, genre, track number
- Embed and replace cover art
- Batch edit multiple files at once

**Converter**
- Convert between MP3, WAV, FLAC, OGG, AAC, MP4, MKV and more
- Drag and drop files, live progress

**Player**
- Built-in audio playback with seek and volume control

**General**
- Dark and light theme
- 7 languages: English, German, Turkish, Japanese, French, Spanish, Italian
- Auto-updates

---

## Architecture

Yuki v3 is a desktop app built on:

| Layer | Technology |
|---|---|
| Shell | Tauri 2 (Rust) |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Backend | FastAPI + Python (sidecar process) |
| Database | SQLite via SQLAlchemy async |
| Media | yt-dlp, spotdl, ffmpeg, mutagen, pygame |

The backend runs as a local sidecar on port 9001 and is fully bundled — no separate installation needed.

---

## Developer Setup

**Prerequisites:** [Node.js](https://nodejs.org), [uv](https://github.com/astral-sh/uv), [Rust](https://rustup.rs), ffmpeg (`ffmpeg.exe` / `ffprobe.exe` in `ffmpeg/`)

```bash
git clone https://github.com/lfl1337/Yuki.git
cd Yuki

# Start backend
cd backend
uv run python run.py

# Start frontend (separate terminal)
cd frontend
npm install
npm run dev:frontend
```

Frontend: `http://localhost:1421` — Backend health: `http://localhost:9001/health`

Or double-click `dev.bat` to start both at once.

---

## Build

```bash
# Bump version across all files
python scripts/bump_version.py 3.0.0

# Build backend sidecar (PyInstaller)
python scripts/build_backend.py

# Build Tauri installer
cd frontend
npm run tauri
```

Output: `frontend/src-tauri/target/release/bundle/nsis/Yuki_3.0.0_x64-setup.exe`

> **Note:** `RC.EXE` from the Windows SDK must be in your PATH during the Tauri build.
> Usually found at `C:\Program Files (x86)\Windows Kits\10\bin\<version>\x64\`.

---

## Author

ninym
