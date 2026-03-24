"""
Yuki — Universal Media Downloader & MP3 Suite
Entry point: loads settings, generates assets, launches the main window.
"""

import sys
import os

# Suppress console output when running as a windowed exe (PyInstaller --windowed)
if sys.platform == "win32" and not sys.stdout:
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")

import ctypes
import ctypes.wintypes

_MUTEX_NAME = "YukiMediaSuite_SingleInstance_Mutex"
_SYNCHRONIZE = 0x100000


def ensure_single_instance():
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    # Try to open an existing mutex — if it succeeds, another instance is alive
    existing = kernel32.OpenMutexW(_SYNCHRONIZE, False, _MUTEX_NAME)
    if existing:
        kernel32.CloseHandle(existing)
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Yuki", "Yuki is already running.")
        root.destroy()
        sys.exit(0)

    # Create owned mutex — bInitialOwner=True so we hold it immediately
    mutex = kernel32.CreateMutexW(None, True, _MUTEX_NAME)
    return mutex  # keep reference alive — OS releases when process exits


_mutex = ensure_single_instance()

import json
import logging
from pathlib import Path

# Bootstrap: ensure project root is on sys.path when running as a script
if getattr(sys, "frozen", False):
    # Running as PyInstaller bundle
    ROOT = Path(sys.executable).parent
else:
    ROOT = Path(__file__).parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import (
    APP_NAME, VERSION, BASE_DIR, DATA_DIR, SETTINGS_FILE, LOG_FILE,
    DEFAULT_SETTINGS, ASSETS_DIR, FFMPEG_PATH,
)


def _setup_logging():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    from core.logger import install as install_logger
    install_logger(LOG_FILE)


def _load_settings() -> dict:
    settings = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            settings.update(saved)
        except Exception as exc:
            logging.warning("Could not load settings: %s — using defaults", exc)
    return settings


def _generate_assets():
    """Generate placeholder assets if they don't exist."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    _gen_placeholder_cover()
    _gen_icon()


def _gen_placeholder_cover():
    cover_path = ASSETS_DIR / "placeholder_cover.png"
    if cover_path.exists():
        return
    try:
        from PIL import Image, ImageDraw, ImageFont
        size = (300, 300)
        img = Image.new("RGB", size, "#1e1e2e")
        draw = ImageDraw.Draw(img)
        # Draw a simple music note glyph
        cx, cy = size[0] // 2, size[1] // 2
        draw.ellipse([cx - 30, cy + 20, cx + 10, cy + 60], fill="#444466")
        draw.rectangle([cx + 8, cy - 40, cx + 18, cy + 40], fill="#444466")
        draw.ellipse([cx + 8, cy - 50, cx + 48, cy - 30], fill="#444466")
        img.save(cover_path, "PNG")
    except Exception as exc:
        logging.warning("Could not generate placeholder cover: %s", exc)


def _gen_icon():
    icon_png = ASSETS_DIR / "icon.png"
    icon_ico = ASSETS_DIR / "icon.ico"
    if icon_ico.exists():
        return
    try:
        from PIL import Image, ImageDraw, ImageFont
        sizes = [256, 128, 64, 48, 32, 16]
        images = []
        for sz in sizes:
            img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # Purple gradient circle
            margin = sz // 8
            draw.ellipse(
                [margin, margin, sz - margin, sz - margin],
                fill="#7C3AED",
            )
            # "Y" letter
            font_size = max(sz // 2, 10)
            try:
                from PIL import ImageFont
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), "Y", font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tx = (sz - tw) // 2 - bbox[0]
            ty = (sz - th) // 2 - bbox[1]
            draw.text((tx, ty), "Y", font=font, fill="white")
            images.append(img)

        images[0].save(str(icon_ico), format="ICO", sizes=[(s, s) for s in sizes])
        images[0].save(str(icon_png), format="PNG")
    except Exception as exc:
        logging.warning("Could not generate icon: %s", exc)


def main():
    import platform
    _setup_logging()
    logger = logging.getLogger("yuki.main")

    logger.info("Single instance check passed")

    # ---- Diagnostic startup block ----
    logger.info("=" * 50)
    logger.info("Yuki v%s starting", VERSION)
    logger.info("OS: Windows %s", platform.version())
    logger.info("Python: %s", sys.version.split()[0])
    logger.info("Install dir: %s", BASE_DIR)
    logger.info("Data dir: %s", DATA_DIR)
    logger.info("ffmpeg: %s", "found" if FFMPEG_PATH.exists() else "MISSING")
    logger.info("=" * 50)

    try:
        settings = _load_settings()
        logger.info("Settings loaded from %s", SETTINGS_FILE)
        logger.info("Download dir: %s", settings.get("default_download_dir"))
        _generate_assets()

        # Apply theme before creating the window
        try:
            import customtkinter as ctk
            theme = settings.get("theme", "dark")
            if theme == "system":
                try:
                    import darkdetect
                    theme = (darkdetect.theme() or "dark").lower()
                except Exception:
                    theme = "dark"
            ctk.set_appearance_mode(theme)
            ctk.set_default_color_theme("blue")
            logger.debug("Theme applied: %s", theme)
        except ImportError as exc:
            logger.critical("Startup failed: customtkinter not installed: %s", exc)
            sys.exit(1)

        from ui.main_window import MainWindow
        from core.auto_updater import AutoUpdater

        app = MainWindow(settings=settings)
        logger.info("Window created, showing UI")

        updater = AutoUpdater()
        updater.check_in_background()

        app.mainloop()

    except Exception as exc:
        logging.getLogger("yuki.main").critical("Startup failed: %s", exc, exc_info=True)
        raise
    finally:
        logger.info("App shutdown initiated")
        if _mutex:
            ctypes.windll.kernel32.ReleaseMutex(_mutex)
            ctypes.windll.kernel32.CloseHandle(_mutex)
        logger.info("App closed cleanly")


if __name__ == "__main__":
    main()
