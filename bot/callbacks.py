"""Callback-query handlers for inline keyboard interactions.

Processes button presses from SuperAdmin approval flows and the /help menu.
"""

from core.logger import ChitraguptLogger
from core.rbac import RBAC
from bot.telegram import send_message, answer_callback_query

logger = ChitraguptLogger.get_logger()


def handle_callback_query(rbac: RBAC, callback_query: dict) -> None:
    """Dispatch callback queries from inline keyboard buttons."""
    cb_id = callback_query.get("id", "")
    data = callback_query.get("data", "")
    admin_user = callback_query.get("from", {})
    admin_id = admin_user.get("id")
    admin_chat_id = callback_query.get("message", {}).get("chat", {}).get("id")

    if admin_id is None or admin_chat_id is None:
        logger.warning("Callback query missing identity or chat: %s", callback_query)
        answer_callback_query(cb_id, "❌ Could not process.")
        return

    logger.info("Callback query from admin %s: %s", admin_id, data)

    # Handle approval/rejection callbacks
    if ":" in data and data.split(":")[0] in ("approve_member", "promote_mod", "reject"):
        _handle_approval_callback(rbac, cb_id, data, admin_id, admin_chat_id)
        return

    # Handle command callbacks from /help menu
    if data.startswith("/"):
        answer_callback_query(cb_id, f"Use {data} in the chat.")
        return

    answer_callback_query(cb_id)


def _handle_approval_callback(
    rbac: RBAC, cb_id: str, data: str, admin_id: int, admin_chat_id: int
) -> None:
    """Process approve/promote/reject callbacks for user registration."""
    action, _, target_id_str = data.partition(":")

    try:
        target_id = int(target_id_str)
    except ValueError:
        logger.error("Invalid target_id in callback data: %s", data)
        answer_callback_query(cb_id, "❌ Invalid user data.")
        return

    # Permission gate — only users with manage_users (or wildcard) may act
    if not rbac.has_permission(admin_id, "manage_users"):
        logger.warning("Unauthorised approval attempt by user %s", admin_id)
        answer_callback_query(cb_id, "⛔ You do not have permission to manage users.")
        return

    if action == "approve_member":
        rbac.set_user_level(target_id, 10)
        answer_callback_query(cb_id, f"✅ User {target_id} approved as Member.")
        send_message(admin_chat_id, f"✅ User {target_id} has been approved as Member (Level 10).")
        send_message(target_id, "🎉 Your access has been approved! You are now a Member.")
        logger.info("Admin %s approved user %s as Member", admin_id, target_id)

    elif action == "promote_mod":
        rbac.set_user_level(target_id, 50)
        answer_callback_query(cb_id, f"🛡️ User {target_id} promoted to Moderator.")
        send_message(admin_chat_id, f"🛡️ User {target_id} has been promoted to Moderator (Level 50).")
        send_message(target_id, "🎉 You have been promoted to Moderator!")
        logger.info("Admin %s promoted user %s to Moderator", admin_id, target_id)

    elif action == "reject":
        answer_callback_query(cb_id, f"❌ User {target_id} rejected.")
        send_message(admin_chat_id, f"❌ User {target_id} has been rejected.")
        send_message(target_id, "❌ Your access request has been rejected by an admin.")
        logger.info("Admin %s rejected user %s", admin_id, target_id)
