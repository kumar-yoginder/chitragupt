import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN or ''}"


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


SUPER_ADMINS: list[int] = _parse_super_admins(os.environ.get("SUPER_ADMINS"))


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

    # Try bare name (works when exiftool is on PATH)
    import shutil
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


EXIFTOOL_PATH: str = _resolve_exiftool_path()

# Deferred import to avoid circular dependency (logger imports nothing from config).
from core.logger import ChitraguptLogger as _CL  # noqa: E402

_logger = _CL.get_logger()
if BOT_TOKEN:
    _logger.info("Config loaded — BOT_TOKEN is set, BASE_URL ready")
else:
    _logger.warning("Config loaded — BOT_TOKEN is NOT set")

if SUPER_ADMINS:
    _logger.info("SUPER_ADMINS loaded: %s", SUPER_ADMINS)
else:
    _logger.warning("No SUPER_ADMINS configured in environment")

_logger.info("EXIFTOOL_PATH resolved to: %s", EXIFTOOL_PATH)
