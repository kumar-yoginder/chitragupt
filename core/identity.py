from core.logger import ChitraguptLogger

logger = ChitraguptLogger.get_logger()


def get_identity(update: dict) -> int | None:
    """Extract entity ID from a Telegram update.

    Handles both message-based updates and callback_query updates.
    Returns the sender_chat ID (a negative group ID) for Anonymous Admins and
    channels, or the from.id for regular users.
    """
    # ── callback_query updates ───────────────────────────────────────────
    callback_query = update.get("callback_query")
    if callback_query:
        # Anonymous Admin: identity lives in the embedded message's sender_chat
        cb_message = callback_query.get("message", {})
        sender_chat = cb_message.get("sender_chat")
        if sender_chat:
            identity = sender_chat.get("id")
            logger.info("Resolved callback anonymous identity", extra={"identity": identity, "source": "sender_chat"})
            return identity

        from_user = callback_query.get("from")
        if from_user:
            identity = from_user.get("id")
            logger.info("Resolved callback user identity", extra={"identity": identity, "source": "from"})
            return identity

    # ── message-based updates ────────────────────────────────────────────
    message = (
        update.get("message")
        or update.get("edited_message")
        or update.get("channel_post")
        or update.get("edited_channel_post")
    )
    if not message:
        logger.debug("No message object found in update", extra={"update_id": update.get("update_id")})
        return None

    # Anonymous admins post as the group itself; sender_chat.id is negative.
    sender_chat = message.get("sender_chat")
    if sender_chat:
        identity = sender_chat.get("id")
        logger.info("Resolved anonymous/channel identity", extra={"identity": identity, "source": "sender_chat"})
        return identity

    from_user = message.get("from")
    if from_user:
        identity = from_user.get("id")
        logger.info("Resolved user identity", extra={"identity": identity, "source": "from"})
        return identity

    logger.warning("Could not resolve identity from update", extra={"update_id": update.get("update_id")})
    return None
