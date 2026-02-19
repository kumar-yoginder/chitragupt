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
