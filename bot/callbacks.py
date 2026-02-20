"""Callback-query handlers for inline keyboard interactions.

Processes button presses from SuperAdmin approval flows and the /help
command menu.  When a user taps a command button from /help, the
corresponding handler is invoked directly — no need to re-type the command.
"""

from core.logger import ChitraguptLogger
from core.rbac import RBAC
from bot.registry import registry
from bot.telegram import answer_callback_query, send_message

logger = ChitraguptLogger.get_logger()


def _build_synthetic_message(callback_query: dict, text: str) -> dict:
    """Build a minimal message dict from a callback query so command
    handlers can be invoked as if the user had typed the command."""
    cb_message = callback_query.get("message", {})
    return {
        "chat": cb_message.get("chat", {}),
        "from": callback_query.get("from", {}),
        "message_id": cb_message.get("message_id", 0),
        "text": text,
    }


async def handle_callback_query(rbac: RBAC, callback_query: dict) -> None:
    """Dispatch callback queries from inline keyboard buttons."""
    cb_id = callback_query.get("id", "")
    data = callback_query.get("data", "")
    user = callback_query.get("from", {})
    user_id = user.get("id")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")

    if user_id is None or chat_id is None:
        logger.warning("Callback query missing identity or chat", extra={"callback_query": callback_query})
        await answer_callback_query(cb_id, "❌ Could not process.")
        return

    logger.info("Callback query received", extra={"user_id": user_id, "chat_id": chat_id, "callback_data": data})

    # ── Approval / rejection flow (SuperAdmin buttons) ───────────────────
    if ":" in data and data.split(":")[0] in ("approve_member", "promote_mod", "reject"):
        await _handle_approval_callback(rbac, cb_id, data, user_id, chat_id)
        return

    # ── /help menu command buttons ───────────────────────────────────────
    if data.startswith("/"):
        await _handle_command_callback(rbac, cb_id, data, callback_query, user_id)
        return

    # Fallback — unknown callback
    logger.debug("Unknown callback data", extra={"user_id": user_id, "callback_data": data})
    await answer_callback_query(cb_id)


async def _handle_command_callback(
    rbac: RBAC,
    cb_id: str,
    command: str,
    callback_query: dict,
    user_id: int,
) -> None:
    """Execute the command handler that corresponds to an inline-button tap.

    A synthetic message is built from the callback query so that each
    handler receives the same interface it would from a regular text message.
    Uses the shared :data:`bot.registry.registry` for dispatch so new
    commands are automatically available without editing this module.
    """
    message = _build_synthetic_message(callback_query, command)
    chat_id = message["chat"].get("id")

    # Acknowledge the button press immediately so the spinner disappears.
    await answer_callback_query(cb_id, f"Running {command}…")

    if not await registry.dispatch(command, rbac, message, user_id):
        logger.debug("No handler mapped for command callback", extra={"command": command, "user_id": user_id})
        await send_message(chat_id, f"⚠️ Unknown command: {command}")


async def _handle_approval_callback(
    rbac: RBAC, cb_id: str, data: str, admin_id: int, admin_chat_id: int
) -> None:
    """Process approve/promote/reject callbacks for user registration."""
    action, _, target_id_str = data.partition(":")

    try:
        target_id = int(target_id_str)
    except ValueError:
        logger.error("Invalid target_id in callback data", extra={"callback_data": data, "admin_id": admin_id})
        await answer_callback_query(cb_id, "❌ Invalid user data.")
        return

    # Permission gate — only users with manage_users (or wildcard) may act
    if not rbac.has_permission(admin_id, "manage_users"):
        logger.warning("Unauthorised approval attempt", extra={"admin_id": admin_id, "action": "manage_users", "callback_data": data})
        await answer_callback_query(cb_id, "⛔ You do not have permission to manage users.")
        return

    if action == "approve_member":
        await rbac.set_user_level(target_id, 10)
        await answer_callback_query(cb_id, f"✅ User {target_id} approved as Member.")
        await send_message(admin_chat_id, f"✅ User {target_id} has been approved as Member (Level 10).")
        await send_message(target_id, "🎉 Your access has been approved! You are now a Member.")
        logger.info("Admin approved user as Member", extra={"admin_id": admin_id, "target_id": target_id, "action": "approve_member", "new_level": 10})

    elif action == "promote_mod":
        await rbac.set_user_level(target_id, 50)
        await answer_callback_query(cb_id, f"🛡️ User {target_id} promoted to Moderator.")
        await send_message(admin_chat_id, f"🛡️ User {target_id} has been promoted to Moderator (Level 50).")
        await send_message(target_id, "🎉 You have been promoted to Moderator!")
        logger.info("Admin promoted user to Moderator", extra={"admin_id": admin_id, "target_id": target_id, "action": "promote_mod", "new_level": 50})

    elif action == "reject":
        await answer_callback_query(cb_id, f"❌ User {target_id} rejected.")
        await send_message(admin_chat_id, f"❌ User {target_id} has been rejected.")
        await send_message(target_id, "❌ Your access request has been rejected by an admin.")
        logger.info("Admin rejected user", extra={"admin_id": admin_id, "target_id": target_id, "action": "reject"})
