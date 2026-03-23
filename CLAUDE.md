# Yuki v2 — Project Context for Claude

## Architecture

Yuki v2 is a Windows media downloader/player/editor built with:

- **Tauri 2** shell (Rust) — window, sidecar management
- **React 18 + TypeScript** frontend — Vite on port 1421, Tailwind CSS
- **FastAPI + Python** backend — sidecar on port 9001, SQLite via SQLAlchemy async
- **yt-dlp, spotdl, ffmpeg, mutagen, pygame** — all Python libs, no native Rust equivalents

This is the same architecture as `C:\Projekte\Hime\app\`. When in doubt, check Hime for patterns.

---

## Directory structure

```
C:\Projekte\yuki\
├── VERSION                     ← single source of truth (2.0.0)
├── CLAUDE.md
├── dev.bat                     ← starts backend + Tauri dev (run this for dev)
├── .gitignore
│
├── backend/
│   ├── run.py                  ← entry point: --data-dir arg, finds free port, writes .runtime_port
│   ├── pyproject.toml          ← uv deps
│   ├── .runtime_port           ← written at startup (gitignored)
│   └── app/
│       ├── main.py             ← FastAPI + lifespan, routers at /api/v1
│       ├── config.py           ← Settings(BaseSettings), YUKI_ prefix
│       ├── database.py         ← async SQLAlchemy + aiosqlite, init_db(), legacy JSON migration
│       ├── models.py           ← HistoryEntry, Setting ORM models
│       ├── schemas.py          ← all Pydantic request/response schemas
│       ├── logger.py           ← RotatingFileHandler + in-memory deque
│       ├── middleware/
│       │   ├── audit.py        ← logs all requests
│       │   └── rate_limit.py   ← slowapi limiter
│       ├── routers/
│       │   ├── download.py     ← /download/* + SSE stream
│       │   ├── history.py      ← /history/* + CSV export
│       │   ├── player.py       ← /player/* + SSE stream
│       │   ├── tagger.py       ← /tagger/*
│       │   ├── converter.py    ← /converter/* + SSE stream
│       │   ├── updater.py      ← /updater/*
│       │   └── settings_router.py ← /settings
│       ├── services/
│       │   ├── detector.py     ← platform regex (verbatim from core/detector.py)
│       │   ├── tagger.py       ← MP3Tagger (verbatim from core/tagger.py)
│       │   ├── player_engine.py ← AudioPlayer (verbatim from core/player.py)
│       │   ├── player.py       ← async wrapper + SSE generator
│       │   ├── downloader.py   ← yt-dlp download manager with threading.Semaphore(3)
│       │   ├── spotify.py      ← spotdl subprocess wrapper
│       │   ├── converter.py    ← ffmpeg asyncio.Semaphore(2) + progress parsing
│       │   ├── autostart.py    ← Windows registry HKCU Run (verbatim from core/autostart.py)
│       │   └── auto_updater.py ← GitHub release check + .bat-based install
│       └── utils/
│           └── ports.py        ← find_free_port(start=9001)
│
├── frontend/
│   ├── package.json            ← React 18, react-router-dom, zustand, i18next, lucide-react, tailwind
│   ├── vite.config.ts          ← port 1421, /api proxy → reads .runtime_port on every request
│   ├── tailwind.config.js      ← accent #7C6FCD, bg-primary #09090b
│   └── src/
│       ├── App.tsx             ← StartupSplash → AppShell (Sidebar + Routes + PlayerBar + Settings)
│       ├── store.ts            ← Zustand: backendOnline, activeTab, playerState, settingsOpen
│       ├── i18n.ts             ← react-i18next, 7 locales (en/de/tr/ja/fr/es/it)
│       ├── api/                ← all API modules (client.ts + per-domain files)
│       ├── components/
│       │   ├── Sidebar.tsx     ← 180px, 雪 logo, kanji nav (載/歴/編/換)
│       │   ├── PlayerBar.tsx   ← 72px bottom bar, SSE /player/stream
│       │   ├── QueueItem.tsx   ← per-download progress row
│       │   ├── HistoryCard.tsx ← thumbnail + action buttons
│       │   ├── PreviewCard.tsx ← URL metadata preview
│       │   └── Settings.tsx    ← modal with 4 sections
│       ├── views/
│       │   ├── Downloader.tsx  ← URL input, detect, preview, queue (SSE)
│       │   ├── History.tsx     ← search, filter pills, paginated cards
│       │   ├── Editor.tsx      ← two-column tag editor, cover art
│       │   └── Converter.tsx   ← drag & drop, format options, progress (SSE)
│       └── locales/            ← en/de/tr/ja/fr/es/it.json (nested i18next format)
│
├── scripts/
│   ├── bump_version.py         ← bumps VERSION + all 6 version references
│   ├── build_backend.py        ← PyInstaller → frontend/src-tauri/binaries/
│   └── release.py             ← full pipeline: check git → build backend → tauri build
│
└── legacy_customtkinter.zip    ← archived v1 source (gitignored)
```

---

## Dev startup

```bash
# Option A: double-click dev.bat
# Option B: manual
cd C:\Projekte\yuki\backend
uv run python run.py
# in another terminal:
cd C:\Projekte\yuki\frontend
npm run dev:frontend
```

Frontend: http://localhost:1421
Backend health: http://localhost:9001/health
Port file: `backend/.runtime_port`

---

## Key ports and identifiers

| Item | Value |
|------|-------|
| Backend default port | 9001 |
| Vite dev port | 1421 |
| App identifier | `app.yuki.media` |
| APPDATA folder | `%APPDATA%\Yuki` |
| Backend env prefix | `YUKI_` |
| Sidecar binary name | `yuki-backend-x86_64-pc-windows-msvc.exe` |

---

## Important implementation notes

### SSE streams
Three SSE endpoints push data every 500ms:
- `/api/v1/download/stream` — active download jobs
- `/api/v1/player/stream` — player position + state
- `/api/v1/converter/stream` — active conversion jobs

Frontend connects with `new EventSource(url)` and reconnects on error.

### pygame threading
`pygame.mixer` is synchronous. All player calls use `asyncio.to_thread()` at the router level. The `AudioPlayer` class in `services/player_engine.py` is unchanged from the legacy app.

### Download → DB bridge
Download threads (Python threading) need to write to the async SQLAlchemy DB. This uses `asyncio.run_coroutine_threadsafe(coro, loop)` where `loop` is stored during FastAPI lifespan startup via `services.downloader.set_event_loop(asyncio.get_event_loop())`.

### spotdl
No stable Python API — use subprocess. The `spotify.py` service runs `spotdl` as a subprocess and parses stdout for progress.

### ffmpeg path resolution
Config.py checks:
1. `sys._MEIPASS/ffmpeg/ffmpeg.exe` (PyInstaller frozen)
2. `<project_root>/ffmpeg/ffmpeg.exe` (dev)
3. Falls back to empty string (system PATH)

---

## Build pipeline

```bash
# Build backend sidecar
python scripts/build_backend.py

# Full release (backend + Tauri installer)
python scripts/release.py

# Bump version
python scripts/bump_version.py 2.1.0 --tag
```

The NSIS installer ends up at:
`frontend/src-tauri/target/release/bundle/nsis/Yuki_2.0.0_x64-setup.exe`

---

## Legacy migration

- Legacy CustomTkinter code archived in `legacy_customtkinter.zip`
- On first run with existing `%APPDATA%\Yuki`, `init_db()` reads:
  - `history.json` → inserts into SQLite `history` table
  - `settings.json` → inserts into SQLite `settings` table
  - Renames originals to `.legacy`
- Legacy port files and data dirs: `%APPDATA%\Yuki\` (same location, same data_dir)

---

## Design tokens

```
accent:     #7C6FCD (purple)
accent-hover: #9080D8
bg-primary:   #09090b (zinc-950)
bg-secondary: #18181b (zinc-900)
bg-card:      #27272a (zinc-800)
bg-elevated:  #3f3f46 (zinc-700)
border:       #52525b (zinc-600)
```

Kanji nav icons: 載 (Downloader) · 歴 (History) · 編 (Editor) · 換 (Converter)
Logo: 雪 (snow) — large purple
Window: 1100×720, min 800×600
