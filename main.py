import json
import time

import requests

from config import BOT_TOKEN, BASE_URL
from core.identity import get_identity
from core.logger import ChitraguptLogger
from core.rbac import RBAC

logger = ChitraguptLogger.get_logger()


def get_updates(offset=None):
    """Long-poll the Telegram Bot API for new updates."""
    params = {"timeout": 30}
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


def send_message(chat_id: int, text: str) -> None:
    """Send a text message to a Telegram chat."""
    logger.debug("Sending message to chat %s: %s", chat_id, text[:80])
    try:
        response = requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text},
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


def handle_kick(rbac, message, user_id):
    """Handle the /kick command.

    Usage: /kick <user_id>
    Requires the 'kick' action permission.
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


def process_update(rbac, update):
    """Dispatch a single Telegram update to the appropriate handler."""
    update_id = update.get("update_id")
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

    if text.startswith("/kick"):
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
