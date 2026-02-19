import json
import time

import requests

from config import BOT_TOKEN, BASE_URL
from core.identity import get_identity
from core.logger import ChitraguptLogger
from core.rbac import RBAC

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


def get_updates(offset: int | None = None) -> dict:
    """Long-poll the Telegram Bot API for new updates."""
    params: dict = {"timeout": 30}
    if offset is not None:
        params["offset"] = offset
    try:
        response = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=35)
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            logger.error("getUpdates JSON decode error: %s", exc)
            return {"ok": False, "result": []}
    except requests.RequestException as exc:
        logger.error("getUpdates error: %s", exc)
        return {"ok": False, "result": []}


def send_message(chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    """Send a text message to a Telegram chat.

    Optionally include an InlineKeyboardMarkup via *reply_markup*.
    """
    logger.debug("Sending message to chat %s: %s", chat_id, text[:80])
    payload: dict = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    try:
        response = requests.post(
            f"{BASE_URL}/sendMessage",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            logger.warning("sendMessage Telegram error: %s", data)
        else:
            logger.info("Message sent to chat %s", chat_id)
    except requests.HTTPError as exc:
        logger.error("sendMessage HTTP error: %s (status=%s)", exc, exc.response.status_code)
    except requests.RequestException as exc:
        logger.error("sendMessage error: %s", exc)


def answer_callback_query(callback_query_id: str, text: str | None = None) -> None:
    """Acknowledge a callback query so the spinner disappears for the user."""
    payload: dict = {"callback_query_id": callback_query_id}
    if text is not None:
        payload["text"] = text
    try:
        response = requests.post(
            f"{BASE_URL}/answerCallbackQuery",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("answerCallbackQuery error: %s", exc)


# ── Command handlers ─────────────────────────────────────────────────────────


def handle_start(rbac: RBAC, message: dict, user_id: int) -> None:
    """Handle /start — register the user as Guest and alert SuperAdmins."""
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    display_name = from_user.get("first_name", str(user_id))
    logger.info("User %s invoked /start in chat %s", user_id, chat_id)

    existing = rbac.users.get(str(user_id))
    if existing is not None:
        role_name = rbac.get_role_name(user_id)
        send_message(chat_id, f"👋 Welcome back, {display_name}! Your current role is *{role_name}*.")
        logger.info("Returning user %s (role=%s) invoked /start", user_id, role_name)
        return

    # Register as Guest (level 0)
    rbac.set_user_level(user_id, 0, name=display_name)
    send_message(
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
        send_message(admin_id, alert_text, reply_markup=markup)
        logger.info("Sent approval alert for user %s to admin %s", user_id, admin_id)


def handle_help(rbac: RBAC, message: dict, user_id: int) -> None:
    """Handle /help — show commands the user is permitted to use as inline buttons."""
    chat_id = message["chat"]["id"]
    logger.info("User %s invoked /help in chat %s", user_id, chat_id)

    buttons: list[list[dict]] = []
    for cmd, info in COMMAND_PERMISSIONS.items():
        if rbac.has_permission(user_id, info["action"]):
            buttons.append([{"text": f"{cmd} — {info['description']}", "callback_data": cmd}])

    if not buttons:
        send_message(chat_id, "⛔ You have no available commands.")
        return

    markup = {"inline_keyboard": buttons}
    send_message(chat_id, "📖 Available commands (tap to use):", reply_markup=markup)


def handle_status(rbac: RBAC, message: dict, user_id: int) -> None:
    """Handle /status — show the user's rank level and permissions."""
    chat_id = message["chat"]["id"]
    logger.info("User %s invoked /status in chat %s", user_id, chat_id)

    level = rbac.get_user_level(user_id)
    role_name = rbac.get_role_name(user_id)
    actions = rbac.get_user_actions(user_id)
    actions_str = ", ".join(actions) if actions else "None"

    send_message(
        chat_id,
        f"📊 Your status:\n"
        f"• Role: {role_name}\n"
        f"• Level: {level}\n"
        f"• Permissions: {actions_str}",
    )


def handle_stop(message: dict, user_id: int) -> None:
    """Handle /stop and /exit — session termination."""
    chat_id = message["chat"]["id"]
    logger.info("User %s invoked /stop or /exit in chat %s", user_id, chat_id)
    send_message(chat_id, "👋 Session ended. Use /start to begin again.")


def handle_kick(rbac: RBAC, message: dict, user_id: int) -> None:
    """Handle the /kick command.

    Usage: /kick <user_id>
    Requires the 'kick_user' action permission.
    """
    chat_id = message["chat"]["id"]
    logger.info("User %s invoked /kick in chat %s", user_id, chat_id)

    if not rbac.has_permission(user_id, "kick_user"):
        logger.warning("Unauthorised /kick attempt by user %s in chat %s", user_id, chat_id)
        send_message(chat_id, "⛔ You do not have permission to kick users.")
        return

    parts = message.get("text", "").split()
    if len(parts) < 2:
        send_message(chat_id, "Usage: /kick <user_id>")
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        send_message(chat_id, "❌ Invalid user_id. It must be an integer.")
        return

    try:
        response = requests.post(
            f"{BASE_URL}/kickChatMember",
            json={"chat_id": chat_id, "user_id": target_id},
            timeout=10,
        )
        result = response.json()
    except requests.RequestException as exc:
        logger.error("kickChatMember error: %s", exc)
        send_message(chat_id, "❌ Failed to reach Telegram API.")
        return

    if result.get("ok"):
        logger.info("User %s kicked target %s in chat %s", user_id, target_id, chat_id)
        send_message(chat_id, f"✅ User {target_id} has been kicked.")
    else:
        description = result.get("description", "Unknown error")
        logger.warning("Kick failed for target %s in chat %s: %s", target_id, chat_id, description)
        send_message(chat_id, f"❌ Could not kick user: {description}")


# ── Callback query handler ───────────────────────────────────────────────────


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


# ── Update dispatcher ────────────────────────────────────────────────────────


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


def main():
    if not BOT_TOKEN:
        raise EnvironmentError("BOT_TOKEN environment variable is not set or is empty.")

    rbac = RBAC()
    offset = None

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


if __name__ == "__main__":
    main()
