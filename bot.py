import os
import time

import requests

from chitragupt_iam import ChitraguptIAM

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN or ''}"


def get_updates(offset=None):
    """Long-poll the Telegram Bot API for new updates."""
    params = {"timeout": 30}
    if offset is not None:
        params["offset"] = offset
    try:
        response = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=40)
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


def handle_promote(iam, message, entity_id):
    """Handle the /promote command (SuperAdmin only).

    Usage: /promote <user_id> <level>
    """
    chat_id = message["chat"]["id"]

    if not iam.can_perform(entity_id, "promote"):
        send_message(chat_id, "⛔ Only a SuperAdmin (Level 100) can promote users.")
        return

    parts = message.get("text", "").split()
    if len(parts) < 3:
        send_message(chat_id, "Usage: /promote <user_id> <level>")
        return

    try:
        target_id = int(parts[1])
        new_level = int(parts[2])
    except ValueError:
        send_message(chat_id, "❌ Invalid arguments. user_id and level must be integers.")
        return

    if new_level >= 100:
        send_message(chat_id, "❌ Cannot promote to SuperAdmin level (100) or above.")
        return

    iam.update_entity_level(target_id, new_level)
    send_message(chat_id, f"✅ Entity {target_id} promoted to level {new_level}.")


def process_update(iam, update):
    """Dispatch a single Telegram update to the appropriate handler."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    entity_id = iam.identify_entity(update)
    if entity_id is None:
        return

    text = message.get("text", "")
    if text.startswith("/promote"):
        handle_promote(iam, message, entity_id)


def main():
    if not BOT_TOKEN:
        raise EnvironmentError("BOT_TOKEN environment variable is not set or is empty.")

    iam = ChitraguptIAM()
    offset = None

    print("Chitragupt bot is running. Polling for updates...")
    while True:
        data = get_updates(offset)
        if not data.get("ok"):
            time.sleep(5)
            continue

        for update in data.get("result", []):
            process_update(iam, update)
            offset = update["update_id"] + 1


if __name__ == "__main__":
    main()
