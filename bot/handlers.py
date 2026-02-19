"""Command handlers for Chitragupt bot.

Each public function handles a single Telegram slash-command and is invoked
by the dispatcher in :mod:`bot.dispatcher`.
"""

from config import BASE_URL
from core.logger import ChitraguptLogger
from core.rbac import RBAC
from bot.telegram import send_message, make_request

logger = ChitraguptLogger.get_logger()

# ── Command definitions (slug → description) used by /help ───────────────────
COMMAND_PERMISSIONS: dict[str, dict[str, str]] = {
    "/start":  {"action": "view_help",    "description": "Register and request access"},
    "/help":   {"action": "view_help",    "description": "Show available commands"},
    "/status": {"action": "view_help",    "description": "View your rank and permissions"},
    "/kick":   {"action": "kick_user",    "description": "Kick a user from the chat"},
    "/stop":   {"action": "view_help",    "description": "End your session"},
    "/exit":   {"action": "view_help",    "description": "End your session"},
}


async def handle_start(rbac: RBAC, message: dict, user_id: int) -> None:
    """Handle /start — register the user as Guest and alert SuperAdmins."""
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    display_name = from_user.get("first_name", str(user_id))
    logger.info("User %s invoked /start in chat %s", user_id, chat_id)

    existing = rbac.users.get(str(user_id))
    if existing is not None:
        role_name = rbac.get_role_name(user_id)
        await send_message(chat_id, f"👋 Welcome back, {display_name}! Your current role is *{role_name}*.")
        logger.info("Returning user %s (role=%s) invoked /start", user_id, role_name)
        return

    # Collect rich metadata from the from-object
    meta = _extract_user_metadata(from_user)

    # Register as Guest (level 0)
    await rbac.set_user_level(user_id, 0, name=display_name, **meta)
    await send_message(
        chat_id,
        f"👋 Welcome, {display_name}! You have been registered as a Guest.\n"
        "⏳ Your access is pending admin approval.",
    )
    logger.info("New user %s registered as Guest", user_id)

    # Alert all SuperAdmins
    markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve (Member)", "callback_data": f"approve_member:{user_id}"},
                {"text": "🛡️ Promote (Mod)", "callback_data": f"promote_mod:{user_id}"},
            ],
            [
                {"text": "❌ Reject", "callback_data": f"reject:{user_id}"},
            ],
        ]
    }
    alert_text = (
        f"🆕 New user registration:\n"
        f"Name: {display_name}\n"
        f"User ID: {user_id}\n\n"
        "Please approve or reject this user."
    )
    for admin_id in rbac.get_superadmins():
        await send_message(admin_id, alert_text, reply_markup=markup)
        logger.info("Sent approval alert for user %s to admin %s", user_id, admin_id)


async def handle_help(rbac: RBAC, message: dict, user_id: int) -> None:
    """Handle /help — show commands the user is permitted to use as inline buttons."""
    chat_id = message["chat"]["id"]
    logger.info("User %s invoked /help in chat %s", user_id, chat_id)

    buttons: list[list[dict]] = []
    for cmd, info in COMMAND_PERMISSIONS.items():
        if rbac.has_permission(user_id, info["action"]):
            buttons.append([{"text": f"{cmd} — {info['description']}", "callback_data": cmd}])

    if not buttons:
        await send_message(chat_id, "⛔ You have no available commands.")
        return

    markup = {"inline_keyboard": buttons}
    await send_message(chat_id, "📖 Available commands (tap to use):", reply_markup=markup)


async def handle_status(rbac: RBAC, message: dict, user_id: int) -> None:
    """Handle /status — show the user's rank level and permissions."""
    chat_id = message["chat"]["id"]
    logger.info("User %s invoked /status in chat %s", user_id, chat_id)

    level = rbac.get_user_level(user_id)
    role_name = rbac.get_role_name(user_id)
    actions = rbac.get_user_actions(user_id)
    actions_str = ", ".join(actions) if actions else "None"

    await send_message(
        chat_id,
        f"📊 Your status:\n"
        f"• Role: {role_name}\n"
        f"• Level: {level}\n"
        f"• Permissions: {actions_str}",
    )


async def handle_stop(message: dict, user_id: int) -> None:
    """Handle /stop and /exit — session termination."""
    chat_id = message["chat"]["id"]
    logger.info("User %s invoked /stop or /exit in chat %s", user_id, chat_id)
    await send_message(chat_id, "👋 Session ended. Use /start to begin again.")


async def handle_kick(rbac: RBAC, message: dict, user_id: int) -> None:
    """Handle the /kick command.

    Usage: /kick <user_id>
    Requires the 'kick_user' action permission.
    """
    chat_id = message["chat"]["id"]
    logger.info("User %s invoked /kick in chat %s", user_id, chat_id)

    if not rbac.has_permission(user_id, "kick_user"):
        logger.warning("Unauthorised /kick attempt by user %s in chat %s", user_id, chat_id)
        await send_message(chat_id, "⛔ You do not have permission to kick users.")
        return

    parts = message.get("text", "").split()
    if len(parts) < 2:
        await send_message(chat_id, "Usage: /kick <user_id>")
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await send_message(chat_id, "❌ Invalid user_id. It must be an integer.")
        return

    try:
        response = await make_request(
            "post",
            f"{BASE_URL}/kickChatMember",
            json={"chat_id": chat_id, "user_id": target_id},
            timeout=10,
        )
        result = response.json()
    except Exception as exc:
        logger.error("kickChatMember error: %s", exc)
        await send_message(chat_id, "❌ Failed to reach Telegram API.")
        return

    if result.get("ok"):
        logger.info("User %s kicked target %s in chat %s", user_id, target_id, chat_id)
        await send_message(chat_id, f"✅ User {target_id} has been kicked.")
    else:
        description = result.get("description", "Unknown error")
        logger.warning("Kick failed for target %s in chat %s: %s", target_id, chat_id, description)
        await send_message(chat_id, f"❌ Could not kick user: {description}")


def _extract_user_metadata(from_user: dict) -> dict:
    """Extract rich metadata fields from a Telegram ``from`` object."""
    meta: dict = {}
    for key in ("username", "first_name", "last_name", "language_code", "is_premium"):
        val = from_user.get(key)
        if val is not None:
            meta[key] = val
    return meta
