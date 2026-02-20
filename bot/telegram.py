"""Low-level Telegram Bot API helpers.

Thin async wrappers around ``requests`` for polling updates, sending messages,
and acknowledging callback queries.  All blocking I/O is offloaded via
:func:`asyncio.to_thread` so the event loop is never blocked.
"""

import asyncio
import json

import requests

from config import BASE_URL, BOT_TOKEN
from sdk.models import File as TelegramFile
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
            logger.error("getUpdates JSON decode error", extra={"api_endpoint": "getUpdates", "error": str(exc)})
            return {"ok": False, "result": []}
    except requests.RequestException as exc:
        logger.error("getUpdates request error", extra={"api_endpoint": "getUpdates", "error": str(exc)})
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
    logger.debug("Sending message", extra={"chat_id": chat_id, "api_endpoint": "sendMessage", "text_preview": text[:80]})
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
            logger.warning("sendMessage Telegram error", extra={"chat_id": chat_id, "api_endpoint": "sendMessage", "api_response": data})
        else:
            logger.info("Message sent", extra={"chat_id": chat_id, "api_endpoint": "sendMessage"})
    except requests.HTTPError as exc:
        logger.error("sendMessage HTTP error", extra={"chat_id": chat_id, "api_endpoint": "sendMessage", "status_code": exc.response.status_code, "error": str(exc)})
    except requests.RequestException as exc:
        logger.error("sendMessage request error", extra={"chat_id": chat_id, "api_endpoint": "sendMessage", "error": str(exc)})


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
                logger.debug("deleteMessages batch ok", extra={"chat_id": chat_id, "api_endpoint": "deleteMessages", "batch_size": len(batch)})
            else:
                logger.warning("deleteMessages batch failed", extra={"chat_id": chat_id, "api_endpoint": "deleteMessages", "api_response": data})
        except requests.RequestException as exc:
            logger.error("deleteMessages request error", extra={"chat_id": chat_id, "api_endpoint": "deleteMessages", "error": str(exc)})
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
        logger.error("answerCallbackQuery request error", extra={"api_endpoint": "answerCallbackQuery", "callback_query_id": callback_query_id, "error": str(exc)})


# ── File download helpers ────────────────────────────────────────────────────


async def get_file_info(file_id: str) -> TelegramFile | None:
    """Resolve a Telegram ``file_id`` to a :class:`~sdk.models.File` model.

    Calls the ``getFile`` API and parses the result into a Pydantic model.
    Returns ``None`` when the API call fails or Telegram returns an error.
    """
    try:
        resp = await make_request(
            "get",
            f"{BASE_URL}/getFile",
            params={"file_id": file_id},
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            return TelegramFile(**data["result"])
        logger.warning("getFile failed", extra={"api_endpoint": "getFile", "file_id": file_id, "api_response": data})
        return None
    except (requests.RequestException, json.JSONDecodeError) as exc:
        logger.error("getFile request error", extra={"api_endpoint": "getFile", "file_id": file_id, "error": str(exc)})
        return None


async def download_file(telegram_file_path: str) -> bytes:
    """Download raw bytes from the Telegram file CDN.

    Args:
        telegram_file_path: The ``file_path`` field from a :class:`~sdk.models.File`.

    Returns:
        The file content as raw bytes.

    Raises:
        requests.HTTPError: If the HTTP response status is not 2xx.
        requests.RequestException: On transport-level failures.
    """
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{telegram_file_path}"
    resp = await make_request("get", url, timeout=30)
    resp.raise_for_status()
    return resp.content
