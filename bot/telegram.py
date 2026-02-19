"""Low-level Telegram Bot API helpers.

Thin wrappers around ``requests`` for polling updates, sending messages,
and acknowledging callback queries.
"""

import json

import requests

from config import BASE_URL
from core.logger import ChitraguptLogger

logger = ChitraguptLogger.get_logger()


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
