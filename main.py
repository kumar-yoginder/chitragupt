import time

import requests

from config import BOT_TOKEN, BASE_URL
from core.identity import get_identity
from core.rbac import RBAC


def get_updates(offset=None):
    """Long-poll the Telegram Bot API for new updates."""
    params = {"timeout": 30}
    if offset is not None:
        params["offset"] = offset
    try:
        response = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=35)
        return response.json()
    except requests.RequestException as exc:
        print(f"[getUpdates error] {exc}")
        return {"ok": False, "result": []}


def send_message(chat_id, text):
    """Send a text message to a Telegram chat."""
    try:
        requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
    except requests.RequestException as exc:
        print(f"[sendMessage error] {exc}")


def handle_kick(rbac, message, user_id):
    """Handle the /kick command.

    Usage: /kick <user_id>
    Requires the 'kick' action permission.
    """
    chat_id = message["chat"]["id"]

    if not rbac.has_permission(user_id, "kick"):
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
        print(f"[kickChatMember error] {exc}")
        send_message(chat_id, "❌ Failed to reach Telegram API.")
        return

    if result.get("ok"):
        send_message(chat_id, f"✅ User {target_id} has been kicked.")
    else:
        description = result.get("description", "Unknown error")
        send_message(chat_id, f"❌ Could not kick user: {description}")


def process_update(rbac, update):
    """Dispatch a single Telegram update to the appropriate handler."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    user_id = get_identity(update)
    if user_id is None:
        return

    text = message.get("text", "")
    if text.startswith("/kick"):
        handle_kick(rbac, message, user_id)


def main():
    if not BOT_TOKEN:
        raise EnvironmentError("BOT_TOKEN environment variable is not set or is empty.")

    rbac = RBAC()
    offset = None

    print("Chitragupt bot is running. Polling for updates...")
    while True:
        data = get_updates(offset)
        if not data.get("ok"):
            time.sleep(5)
            continue

        for update in data.get("result", []):
            process_update(rbac, update)
            offset = update["update_id"] + 1


if __name__ == "__main__":
    main()
