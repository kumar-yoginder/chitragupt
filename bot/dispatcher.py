"""Update dispatcher and main polling loop.

Routes each incoming Telegram update to the appropriate handler in
:mod:`bot.handlers` or :mod:`bot.callbacks`.
"""

import time

from config import BOT_TOKEN
from core.identity import get_identity
from core.logger import ChitraguptLogger
from core.rbac import RBAC
from bot.telegram import get_updates
from bot.handlers import (
    handle_start,
    handle_help,
    handle_status,
    handle_stop,
    handle_kick,
)
from bot.callbacks import handle_callback_query

logger = ChitraguptLogger.get_logger()


def process_update(rbac: RBAC, update: dict) -> None:
    """Dispatch a single Telegram update to the appropriate handler."""
    update_id = update.get("update_id")

    # Handle callback queries (inline button presses) first
    callback_query = update.get("callback_query")
    if callback_query:
        logger.debug("Processing callback_query in update %s", update_id)
        handle_callback_query(rbac, callback_query)
        return

    message = (
        update.get("message")
        or update.get("edited_message")
        or update.get("channel_post")
        or update.get("edited_channel_post")
    )
    if not message:
        logger.debug("Update %s has no message — skipping", update_id)
        return

    user_id = get_identity(update)
    if user_id is None:
        logger.debug("Update %s — could not resolve identity, skipping", update_id)
        return

    text = message.get("text", "")
    logger.debug("Processing update %s from user %s: %s", update_id, user_id, text[:80])

    if text.startswith("/start"):
        handle_start(rbac, message, user_id)
    elif text.startswith("/help"):
        handle_help(rbac, message, user_id)
    elif text.startswith("/status"):
        handle_status(rbac, message, user_id)
    elif text.startswith("/stop") or text.startswith("/exit"):
        handle_stop(message, user_id)
    elif text.startswith("/kick"):
        handle_kick(rbac, message, user_id)
    else:
        logger.debug("No command matched for update %s", update_id)


def run() -> None:
    """Start the long-polling loop.

    Raises:
        EnvironmentError: If ``BOT_TOKEN`` is not set.
    """
    if not BOT_TOKEN:
        raise EnvironmentError("BOT_TOKEN environment variable is not set or is empty.")

    rbac = RBAC()
    offset: int | None = None

    logger.info("Chitragupt bot is running. Polling for updates...")
    while True:
        data = get_updates(offset)
        if not data.get("ok"):
            logger.warning("getUpdates returned ok=false, retrying in 5 s")
            time.sleep(5)
            continue

        updates = data.get("result", [])
        if updates:
            logger.debug("Received %d update(s)", len(updates))
        for update in updates:
            process_update(rbac, update)
            offset = update["update_id"] + 1
