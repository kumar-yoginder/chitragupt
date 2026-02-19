import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN or ''}"

# Deferred import to avoid circular dependency (logger imports nothing from config).
from core.logger import ChitraguptLogger as _CL  # noqa: E402

_logger = _CL.get_logger()
if BOT_TOKEN:
    _logger.info("Config loaded — BOT_TOKEN is set, BASE_URL ready")
else:
    _logger.warning("Config loaded — BOT_TOKEN is NOT set")
