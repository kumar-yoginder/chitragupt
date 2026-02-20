"""Update dispatcher and main polling loop.

Routes each incoming Telegram update to the appropriate handler in
:mod:`bot.handlers` or :mod:`bot.callbacks`.  The loop uses ``asyncio``
to process updates in parallel — long-running tasks (API calls, DB writes)
never block the bot from receiving new messages.
"""

import asyncio

from pydantic import ValidationError

from config import BOT_TOKEN, SUPER_ADMINS
from sdk.models import Update
from core.identity import get_identity
from core.logger import ChitraguptLogger
from core.rbac import RBAC
from bot.registry import registry
from bot.telegram import get_updates

# Import handlers module so @registry.register decorators execute.
import bot.handlers as _handlers  # noqa: F401
from bot.callbacks import handle_callback_query
from bot.handlers import _extract_user_metadata, _PENDING_METADATA, handle_metadata_upload

logger = ChitraguptLogger.get_logger()


async def process_update(rbac: RBAC, update: dict) -> None:
    """Dispatch a single Telegram update to the appropriate handler.

    Identity is resolved via :func:`core.identity.get_identity` **before**
    any handler dispatch — including callback queries — so the canonical
    identity function is always the single entry point.
    """
    update_id = update.get("update_id")

    # ── Resolve identity first (core layer, works with raw dict) ─────────
    user_id = get_identity(update)
    if user_id is None:
        logger.debug("Could not resolve identity, skipping", extra={"update_id": update_id})
        return

    # ── Parse raw dict into SDK Update model for typed access ────────────
    try:
        sdk_update = Update.model_validate(update)
    except ValidationError as exc:
        logger.warning("Failed to parse update into SDK model", extra={"update_id": update_id, "error": str(exc)})
        return

    # ── Callback queries (inline button presses) ─────────────────────────
    if sdk_update.callback_query:
        logger.debug("Processing callback_query", extra={"update_id": update_id})
        await handle_callback_query(rbac, sdk_update.callback_query, user_id)
        return

    # ── Message-based updates ────────────────────────────────────────────
    message = (
        sdk_update.message
        or sdk_update.edited_message
        or sdk_update.channel_post
        or sdk_update.edited_channel_post
    )
    if not message:
        logger.debug("Update has no message — skipping", extra={"update_id": update_id})
        return

    # ── SUPER_ADMIN metadata sync ────────────────────────────────────────
    if user_id in SUPER_ADMINS:
        entity = message.from_field or message.sender_chat
        display_name = getattr(entity, "first_name", None) or str(user_id)
        meta = _extract_user_metadata(entity)
        await rbac.sync_super_admin(user_id, display_name, **meta)

    text = message.text or ""
    logger.debug("Processing update", extra={"update_id": update_id, "user_id": user_id, "text": text[:80]})

    # ── Registry-based command dispatch ──────────────────────────────────
    command = text.split()[0].split("@")[0] if text.startswith("/") else ""
    if command and await registry.dispatch(command, rbac, message, user_id):
        return

    # ── Non-command handlers (file uploads, etc.) ────────────────────────
    if user_id in _PENDING_METADATA and (message.photo or message.document):
        await handle_metadata_upload(rbac, message, user_id)
    else:
        logger.debug("No command matched", extra={"update_id": update_id, "user_id": user_id})


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
            logger.warning("getUpdates returned ok=false, retrying in 5 s", extra={"api_endpoint": "getUpdates"})
            await asyncio.sleep(5)
            continue

        updates = data.get("result", [])
        if updates:
            logger.debug("Received updates", extra={"count": len(updates)})
        for update in updates:
            asyncio.create_task(process_update(rbac, update))
            offset = update["update_id"] + 1
