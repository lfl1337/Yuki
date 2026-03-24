"""
Yuki backend entry point.
Usage: python run.py [--data-dir <path>]
In production (Tauri sidecar): called with --data-dir %APPDATA%\\Yuki
"""

import argparse
import logging
import os
import sys
from pathlib import Path


def _parse_args():
    parser = argparse.ArgumentParser(description="Yuki backend")
    parser.add_argument(
        "--data-dir",
        default="",
        help="Path to user data directory (default: %%APPDATA%%\\Yuki)",
    )
    return parser.parse_args()


def _default_data_dir() -> str:
    appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return str(Path(appdata) / "Yuki")


def main():
    args = _parse_args()
    data_dir = args.data_dir or _default_data_dir()

    # Make data dir available to config.py before it is imported
    os.environ["YUKI_DATA_DIR"] = data_dir
    Path(data_dir).mkdir(parents=True, exist_ok=True)

    # Setup logging before importing FastAPI app
    from app.logger import setup_logging
    log_file = Path(data_dir) / "yuki-backend.log"
    setup_logging(log_file)

    logger = logging.getLogger("yuki.run")
    logger.info("=" * 50)
    logger.info("Yuki Backend v2.0.3 starting")
    logger.info("Data dir: %s", data_dir)
    logger.info("Python: %s", sys.version.split()[0])

    from app.utils.ports import find_free_port
    from app.config import settings

    port = find_free_port(start=settings.port)
    settings.port = port

    # Port file goes to %APPDATA%\Yuki — always the same location so Tauri
    # can find it regardless of which data_dir the sidecar receives.
    _appdata = os.environ.get("APPDATA", "") or str(Path.home() / "AppData" / "Roaming")
    _port_dir = Path(_appdata) / "Yuki"
    _port_dir.mkdir(parents=True, exist_ok=True)
    runtime_port_file = _port_dir / ".runtime_port"
    runtime_port_file.write_text(str(port), encoding="utf-8")
    logger.info("Backend port: %d (written to %s)", port, runtime_port_file)

    import uvicorn

    try:
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",   # local only — never 0.0.0.0
            port=port,
            log_level="warning",   # uvicorn's own logs muted; we use our logger
            access_log=False,
        )
    finally:
        try:
            runtime_port_file.unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass
        logger.info("Backend stopped")


if __name__ == "__main__":
    main()
