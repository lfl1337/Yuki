"""
Windows registry autostart handler.
Writes/removes HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_VALUE_NAME = "Yuki"


def _get_exe_path() -> str:
    """Return the path to the current executable or Python script."""
    if getattr(sys, "frozen", False):
        return sys.executable
    # Running as a Python script — wrap with pythonw to avoid console
    script = Path(__file__).parent.parent / "main.py"
    pythonw = Path(sys.executable).parent / "pythonw.exe"
    if pythonw.exists():
        return f'"{pythonw}" "{script}"'
    return f'"{sys.executable}" "{script}"'


def enable_autostart() -> bool:
    """Add Yuki to Windows startup. Returns True on success."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, REG_VALUE_NAME, 0, winreg.REG_SZ, _get_exe_path())
        winreg.CloseKey(key)
        logger.info("Autostart enabled")
        return True
    except PermissionError:
        logger.error("Permission denied enabling autostart")
        return False
    except Exception as exc:
        logger.error("enable_autostart failed: %s", exc)
        return False


def disable_autostart() -> bool:
    """Remove Yuki from Windows startup. Returns True on success."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE
        )
        try:
            winreg.DeleteValue(key, REG_VALUE_NAME)
        except FileNotFoundError:
            pass  # Already removed
        winreg.CloseKey(key)
        logger.info("Autostart disabled")
        return True
    except PermissionError:
        logger.error("Permission denied disabling autostart")
        return False
    except Exception as exc:
        logger.error("disable_autostart failed: %s", exc)
        return False


def is_autostart_enabled() -> bool:
    """Check whether autostart is currently enabled."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, REG_VALUE_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False
