"""Application configuration — environment variables and derived constants.

Loads ``BOT_TOKEN``, ``SUPER_ADMINS``, and ``EXIFTOOL_PATH`` from the
environment via ``python-dotenv``.  All values are resolved at import time
so other modules can ``from config import …`` without repeated lookups.
"""

# ── stdlib ───────────────────────────────────────────────────────────────────
import os
import shutil

# ── third-party ──────────────────────────────────────────────────────────────
from dotenv import load_dotenv

# ── core ─────────────────────────────────────────────────────────────────────
from core.logger import ChitraguptLogger

# ── Environment bootstrap ────────────────────────────────────────────────────
load_dotenv()

# ── Logger (used for startup diagnostics at the bottom of this module) ───────
logger = ChitraguptLogger.get_logger()


# ── Helper functions (private) ───────────────────────────────────────────────


def _parse_super_admins(raw: str | None) -> list[int]:
    """Parse a comma-separated string of Telegram user IDs into a list of ints.

    Handles single IDs (e.g. ``"755764114"``) and comma-separated lists
    (e.g. ``"755764114,12345678"``).  Invalid tokens are silently skipped.
    """
    if not raw:
        return []
    result: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if token:
            try:
                result.append(int(token))
            except ValueError:
                pass  # skip non-numeric tokens
    return result


def _resolve_exiftool_path() -> str:
    """Return the absolute path to the ExifTool binary.

    Resolution order:
    1. ``EXIFTOOL_PATH`` environment variable (explicit override).
    2. ``exiftool`` on ``PATH`` (works if the user added it).
    3. Well-known Windows install location under ``%LOCALAPPDATA%``.
    """
    from_env = os.environ.get("EXIFTOOL_PATH")
    if from_env and os.path.isfile(from_env):
        return from_env

    on_path = shutil.which("exiftool")
    if on_path:
        return on_path

    # Well-known Windows install location (winget / installer default)
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        candidate = os.path.join(local_app, "Programs", "ExifTool", "ExifTool.exe")
        if os.path.isfile(candidate):
            return candidate

    # Fallback — let the caller handle "not found" at runtime
    return "exiftool"


# ── Public constants ─────────────────────────────────────────────────────────

BOT_TOKEN: str | None = os.environ.get("BOT_TOKEN")
BASE_URL: str = f"https://api.telegram.org/bot{BOT_TOKEN or ''}"
SUPER_ADMINS: list[int] = _parse_super_admins(os.environ.get("SUPER_ADMINS"))
EXIFTOOL_PATH: str = _resolve_exiftool_path()


# ── Startup diagnostics ─────────────────────────────────────────────────────

if BOT_TOKEN:
    logger.info("Config loaded — BOT_TOKEN is set, BASE_URL ready")
else:
    logger.warning("Config loaded — BOT_TOKEN is NOT set")

if SUPER_ADMINS:
    logger.info("SUPER_ADMINS loaded", extra={"super_admins": SUPER_ADMINS})
else:
    logger.warning("No SUPER_ADMINS configured in environment")

logger.info("EXIFTOOL_PATH resolved", extra={"exiftool_path": EXIFTOOL_PATH})
