"""Low-level Telegram Bot API helpers.

Thin async wrappers around ``requests`` for polling updates, sending messages,
and acknowledging callback queries.  All blocking I/O is offloaded via
:func:`asyncio.to_thread` so the event loop is never blocked.
"""

import asyncio
import json

import requests

from config import BASE_URL
from core.logger import ChitraguptLogger

logger = ChitraguptLogger.get_logger()


async def make_request(method: str, url: str, **kwargs: object) -> requests.Response:
    """Run a :mod:`requests` call inside a thread to keep the event loop free.

    *method* is the HTTP verb (``"get"``, ``"post"``, …).
    """
    func = getattr(requests, method.lower())
    return await asyncio.to_thread(func, url, **kwargs)


async def get_updates(offset: int | None = None) -> dict:
    """Long-poll the Telegram Bot API for new updates."""
    params: dict = {"timeout": 30}
    if offset is not None:
        params["offset"] = offset
    try:
        response = await make_request("get", f"{BASE_URL}/getUpdates", params=params, timeout=35)
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            logger.error("getUpdates JSON decode error: %s", exc)
            return {"ok": False, "result": []}
    except requests.RequestException as exc:
        logger.error("getUpdates error: %s", exc)
        return {"ok": False, "result": []}


async def send_message(
    chat_id: int,
    text: str,
    reply_markup: dict | None = None,
    parse_mode: str | None = None,
) -> None:
    """Send a text message to a Telegram chat.

    Optionally include an InlineKeyboardMarkup via *reply_markup* and/or
    a *parse_mode* (``"Markdown"``, ``"MarkdownV2"``, ``"HTML"``).
    """
    logger.debug("Sending message to chat %s: %s", chat_id, text[:80])
    payload: dict = {"chat_id": chat_id, "text": text}
    if parse_mode is not None:
        payload["parse_mode"] = parse_mode
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    try:
        response = await make_request(
            "post",
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


async def delete_message(chat_id: int, message_id: int) -> bool:
    """Delete a single message.  Returns True on success, False otherwise."""
    try:
        response = await make_request(
            "post",
            f"{BASE_URL}/deleteMessage",
            json={"chat_id": chat_id, "message_id": message_id},
            timeout=10,
        )
        data = response.json()
        return data.get("ok", False)
    except requests.RequestException:
        return False


async def delete_messages(chat_id: int, message_ids: list[int]) -> int:
    """Bulk-delete messages using Telegram's ``deleteMessages`` endpoint.

    The API accepts 1–100 IDs per call.  If more than 100 are passed they
    are sent in consecutive batches.  Returns the total number of messages
    the API confirmed as deleted.
    """
    if not message_ids:
        return 0

    deleted = 0
    # Telegram allows at most 100 message IDs per request.
    batch_size = 100
    for start in range(0, len(message_ids), batch_size):
        batch = message_ids[start : start + batch_size]
        try:
            response = await make_request(
                "post",
                f"{BASE_URL}/deleteMessages",
                json={"chat_id": chat_id, "message_ids": batch},
                timeout=10,
            )
            data = response.json()
            if data.get("ok"):
                deleted += len(batch)
                logger.debug("deleteMessages ok for %d IDs in chat %s", len(batch), chat_id)
            else:
                logger.warning("deleteMessages failed for chat %s: %s", chat_id, data)
        except requests.RequestException as exc:
            logger.error("deleteMessages error for chat %s: %s", chat_id, exc)
    return deleted


async def answer_callback_query(callback_query_id: str, text: str | None = None) -> None:
    """Acknowledge a callback query so the spinner disappears for the user."""
    payload: dict = {"callback_query_id": callback_query_id}
    if text is not None:
        payload["text"] = text
    try:
        response = await make_request(
            "post",
            f"{BASE_URL}/answerCallbackQuery",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("answerCallbackQuery error: %s", exc)
