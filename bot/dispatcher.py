"""Update dispatcher and main polling loop.

Routes each incoming Telegram update to the appropriate handler in
:mod:`bot.handlers` or :mod:`bot.callbacks`.  The loop uses ``asyncio``
to process updates in parallel — long-running tasks (API calls, DB writes)
never block the bot from receiving new messages.
"""

import asyncio

import config
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
    handle_clear,
    handle_metadata,
    handle_metadata_upload,
    _pending_metadata,
    _extract_user_metadata,
)
from bot.callbacks import handle_callback_query

logger = ChitraguptLogger.get_logger()


async def process_update(rbac: RBAC, update: dict) -> None:
    """Dispatch a single Telegram update to the appropriate handler."""
    update_id = update.get("update_id")

    # Handle callback queries (inline button presses) first
    callback_query = update.get("callback_query")
    if callback_query:
        logger.debug("Processing callback_query in update %s", update_id)
        await handle_callback_query(rbac, callback_query)
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

    # ── SUPER_ADMIN metadata sync ────────────────────────────────────────
    super_admins: list[int] = getattr(config, "SUPER_ADMINS", [])
    if user_id in super_admins:
        from_user = message.get("from") or message.get("sender_chat") or {}
        display_name = from_user.get("first_name", str(user_id))
        meta = _extract_user_metadata(from_user)
        await rbac.sync_super_admin(user_id, display_name, **meta)

    text = message.get("text", "")
    logger.debug("Processing update %s from user %s: %s", update_id, user_id, text[:80])

    if text.startswith("/start"):
        await handle_start(rbac, message, user_id)
    elif text.startswith("/help"):
        await handle_help(rbac, message, user_id)
    elif text.startswith("/status"):
        await handle_status(rbac, message, user_id)
    elif text.startswith("/stop") or text.startswith("/exit"):
        await handle_stop(message, user_id)
    elif text.startswith("/kick"):
        await handle_kick(rbac, message, user_id)
    elif text.startswith("/clear"):
        await handle_clear(message, user_id)
    elif text.startswith("/metadata"):
        await handle_metadata(rbac, message, user_id)
    elif user_id in _pending_metadata and (message.get("photo") or message.get("document")):
        await handle_metadata_upload(rbac, message, user_id)
    else:
        logger.debug("No command matched for update %s", update_id)


async def run() -> None:
    """Start the async long-polling loop.

    Each update is spawned as an independent :func:`asyncio.create_task` so
    the loop immediately proceeds to fetch the next batch.

    Raises:
        EnvironmentError: If ``BOT_TOKEN`` is not set.
    """
    if not BOT_TOKEN:
        raise EnvironmentError("BOT_TOKEN environment variable is not set or is empty.")

    rbac = RBAC()
    offset: int | None = None

    logger.info("Chitragupt bot is running. Polling for updates (async)...")
    while True:
        data = await get_updates(offset)
        if not data.get("ok"):
            logger.warning("getUpdates returned ok=false, retrying in 5 s")
            await asyncio.sleep(5)
            continue

        updates = data.get("result", [])
        if updates:
            logger.debug("Received %d update(s)", len(updates))
        for update in updates:
            asyncio.create_task(process_update(rbac, update))
            offset = update["update_id"] + 1
