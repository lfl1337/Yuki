#!/usr/bin/env python3
"""
Build the Yuki Python backend into a single-file executable for Tauri sidecar.

Output: frontend/src-tauri/binaries/yuki-backend-x86_64-pc-windows-msvc.exe

Usage:
    cd C:\Projekte\yuki
    uv run python scripts/build_backend.py
"""

import subprocess
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
BACKEND = ROOT / "backend"
OUTPUT_DIR = ROOT / "frontend" / "src-tauri" / "binaries"
BINARY_NAME = "yuki-backend-x86_64-pc-windows-msvc"
OUTPUT = OUTPUT_DIR / f"{BINARY_NAME}.exe"

HIDDEN_IMPORTS = [
    "app",
    "app.main",
    "app.config",
    "app.database",
    "app.models",
    "app.schemas",
    "app.logger",
    "app.routers",
    "app.routers.download",
    "app.routers.history",
    "app.routers.player",
    "app.routers.tagger",
    "app.routers.converter",
    "app.routers.updater",
    "app.routers.settings_router",
    "app.routers.system",
    "app.services.detector",
    "app.services.downloader",
    "app.services.player",
    "app.services.player_engine",
    "app.services.tagger",
    "app.services.converter",
    "app.services.spotify",
    "app.services.autostart",
    "app.services.auto_updater",
    "app.middleware.audit",
    "app.middleware.rate_limit",
    "app.utils.ports",
    # uvicorn internals
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    # heavy deps
    "yt_dlp",
    "yt_dlp.extractor",
    "mutagen",
    "mutagen.id3",
    "mutagen.mp3",
    "mutagen.mp4",
    "mutagen.flac",
    "mutagen.ogg",
    "mutagen.oggvorbis",
    "pygame",
    "pygame.mixer",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "sqlalchemy",
    "sqlalchemy.dialects.sqlite",
    "aiosqlite",
    "anyio",
    "anyio._backends._asyncio",
    "email.mime.multipart",
    "email.mime.text",
]

COLLECT_ALL = [
    "pydantic",
    "pydantic_settings",
    "yt_dlp",
]

EXCLUDE_MODULES = [
    # GUI toolkits — never needed in a headless server
    "tkinter", "_tkinter", "tcl", "tk",
    # Testing frameworks
    "unittest", "test", "tests", "doctest",
    # Package management — not needed at runtime
    "distutils", "setuptools", "pip", "ensurepip",
    # Legacy/unused stdlib
    "lib2to3", "idlelib", "pydoc_data", "turtledemo", "turtle",
    "antigravity", "this",
    # Server-side HTTP — Yuki is a client
    "xmlrpc", "ftplib", "cgi", "cgitb",
    # Curses — Windows terminal library (not used)
    "curses", "_curses",
]


def main() -> None:
    print("Building Yuki backend…")
    print(f"  Source:  {BACKEND}")
    print(f"  Output:  {OUTPUT}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Must use 64-bit Hime conda Python — uv's sys.executable may differ
    PYTHON = Path(r"C:\Projekte\Hime\Conda\python.exe")
    if not PYTHON.exists():
        print(f"ERROR: expected 64-bit Python not found at {PYTHON}")
        sys.exit(1)

    # Build pyinstaller command
    cmd = [
        str(PYTHON), "-m", "PyInstaller",
        "--onefile",
        "--target-arch", "x86_64",
        "--name", BINARY_NAME,
        "--distpath", str(OUTPUT_DIR),
        "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--specpath", str(ROOT / "build" / "pyinstaller"),
        "--noconfirm",
        "--log-level", "WARN",
        "--clean",
    ]

    # Hidden imports
    for imp in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", imp]

    # Collect all
    for pkg in COLLECT_ALL:
        cmd += ["--collect-all", pkg]

    # Exclude unused modules to reduce bundle size
    for mod in EXCLUDE_MODULES:
        cmd += ["--exclude-module", mod]

    # Add data: ffmpeg binaries (relative to BACKEND dir)
    ffmpeg_dir = ROOT / "ffmpeg"
    if ffmpeg_dir.exists():
        cmd += ["--add-data", f"{ffmpeg_dir};ffmpeg"]
        print(f"  ffmpeg:  bundling from {ffmpeg_dir}")
    else:
        print(f"  WARNING: ffmpeg/ not found at {ffmpeg_dir} — binary will not include ffmpeg")

    cmd.append(str(BACKEND / "run.py"))

    print("\nRunning PyInstaller…")
    result = subprocess.run(cmd, cwd=BACKEND)

    if result.returncode != 0:
        print("\nBuild FAILED.")
        sys.exit(1)

    if OUTPUT.exists():
        size_mb = OUTPUT.stat().st_size / 1024 / 1024
        print(f"\nBuild SUCCESS: {OUTPUT} ({size_mb:.1f} MB)")
    else:
        print(f"\nWARNING: expected output not found at {OUTPUT}")


if __name__ == "__main__":
    main()
