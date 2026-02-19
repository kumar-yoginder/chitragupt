def get_identity(update):
    """Extract entity ID from a Telegram update.

    Returns the sender_chat ID (a negative group ID) for Anonymous Admins and
    channels, or the from.id for regular users.
    """
    message = (
        update.get("message")
        or update.get("edited_message")
        or update.get("channel_post")
    )
    if not message:
        return None

    # Anonymous admins post as the group itself; sender_chat.id is negative.
    sender_chat = message.get("sender_chat")
    if sender_chat:
        return sender_chat.get("id")

    from_user = message.get("from")
    if from_user:
        return from_user.get("id")

    return None
