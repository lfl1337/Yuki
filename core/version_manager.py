"""
Semantic version manager — reads/writes version.json and syncs config.py VERSION line.
"""

import json
import re
from datetime import date
from pathlib import Path

_VERSION_FILE = Path(__file__).parent.parent / "version.json"
_CONFIG_FILE = Path(__file__).parent.parent / "config.py"


def _read() -> dict:
    try:
        with open(_VERSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": "1.0.0", "build": 1, "build_date": str(date.today()), "changelog": []}


def _write(data: dict):
    with open(_VERSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    _sync_config(data["version"])


def _sync_config(version: str):
    """Update the VERSION = '...' line in config.py."""
    try:
        text = _CONFIG_FILE.read_text(encoding="utf-8")
        new_text = re.sub(r'^VERSION\s*=\s*"[^"]*"', f'VERSION = "{version}"', text, flags=re.MULTILINE)
        _CONFIG_FILE.write_text(new_text, encoding="utf-8")
    except Exception:
        pass


def get_current_version() -> str:
    return _read().get("version", "1.0.0")


def get_version_info() -> dict:
    return _read()


def get_version_string() -> str:
    data = _read()
    return f"{data.get('version', '1.0.0')} (Build {data.get('build', 1)})"


def _bump(index: int):
    data = _read()
    parts = data["version"].split(".")
    while len(parts) < 3:
        parts.append("0")
    parts[index] = str(int(parts[index]) + 1)
    for i in range(index + 1, 3):
        parts[i] = "0"
    data["version"] = ".".join(parts)
    _write(data)
    return data["version"]


def bump_patch() -> str:
    return _bump(2)


def bump_minor() -> str:
    return _bump(1)


def bump_major() -> str:
    return _bump(0)


def increment_build() -> int:
    data = _read()
    data["build"] = data.get("build", 0) + 1
    _write(data)
    return data["build"]


def update_build_date():
    data = _read()
    data["build_date"] = str(date.today())
    _write(data)


def add_changelog_entry(msg: str):
    data = _read()
    entries = data.get("changelog", [])
    entries.insert(0, f"[{date.today()}] {msg}")
    data["changelog"] = entries[:50]
    _write(data)
