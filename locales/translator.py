"""
Translation loader and t() function.
Loads locale JSON files and provides key-based lookup with fallback to English.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_LOCALES_DIR = Path(__file__).parent
_current_lang: str = "en"
_strings: dict = {}
_fallback: dict = {}


def load_language(lang_code: str):
    """Load the specified language. Falls back to English on error."""
    global _current_lang, _strings, _fallback

    # Always load English as fallback
    en_path = _LOCALES_DIR / "en.json"
    try:
        with open(en_path, "r", encoding="utf-8") as f:
            _fallback = json.load(f)
    except Exception as exc:
        logger.error("Failed to load English locale: %s", exc)
        _fallback = {}

    if lang_code == "en":
        _strings = _fallback
        _current_lang = "en"
        return

    lang_path = _LOCALES_DIR / f"{lang_code}.json"
    try:
        with open(lang_path, "r", encoding="utf-8") as f:
            _strings = json.load(f)
        _current_lang = lang_code
        logger.info("Loaded language: %s", lang_code)
    except FileNotFoundError:
        logger.warning("Locale file not found for '%s', using English", lang_code)
        _strings = _fallback
        _current_lang = "en"
    except Exception as exc:
        logger.error("Failed to load locale '%s': %s", lang_code, exc)
        _strings = _fallback
        _current_lang = "en"


def t(key: str, **kwargs) -> str:
    """
    Return the translated string for key.
    Supports f-string style placeholders: t("hello", name="World")
    Falls back to English, then to the key itself.
    """
    text = _strings.get(key) or _fallback.get(key) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError) as exc:
            logger.debug("t() format error for key '%s': %s", key, exc)
    return text


def get_current_language() -> str:
    return _current_lang
