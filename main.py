"""
Yuki — Universal Media Downloader & MP3 Suite
Entry point: loads settings, generates assets, launches the main window.
"""

import sys
import os
import tempfile
import msvcrt


def ensure_single_instance():
    lock_file = os.path.join(tempfile.gettempdir(), "yuki.lock")
    try:
        fp = open(lock_file, "w")
        msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
        return fp  # keep reference alive — lock released when process exits
    except (IOError, OSError):
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Yuki", "Yuki is already running.")
        root.destroy()
        sys.exit(0)


_lock = ensure_single_instance()  # module-level so it stays alive for the process lifetime

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
    APP_NAME, VERSION, DATA_DIR, SETTINGS_FILE, LOG_FILE,
    DEFAULT_SETTINGS, ASSETS_DIR,
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
    _setup_logging()
    logger = logging.getLogger("yuki.main")
    logger.info("Starting %s v%s", APP_NAME, VERSION)

    settings = _load_settings()
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
    except ImportError as exc:
        logger.error("customtkinter not installed: %s", exc)
        sys.exit(1)

    from ui.main_window import MainWindow
    from core.auto_updater import AutoUpdater

    app = MainWindow(settings=settings)

    updater = AutoUpdater()
    updater.check_in_background()

    app.mainloop()

    logger.info("Yuki exited cleanly")


if __name__ == "__main__":
    main()
