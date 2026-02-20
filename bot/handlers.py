"""Command handlers for Chitragupt bot.

Each public function handles a single Telegram slash-command and is invoked
by the dispatcher in :mod:`bot.dispatcher`.
"""

import asyncio
import contextlib
import json
import os
from typing import AsyncIterator

from config import BASE_URL, EXIFTOOL_PATH
from sdk.models import Chat, Document, Message, PhotoSize, User
from core.logger import ChitraguptLogger
from core.rbac import RBAC, USER_META_KEYS
from bot.registry import registry
from bot.telegram import (
    delete_message, delete_messages, download_file,
    get_file_info, make_request, send_message,
)

logger = ChitraguptLogger.get_logger()

# ── Conversation state: users awaiting image upload for /metadata ────────────
_PENDING_METADATA: set[int] = set()


@registry.register("/start", action="view_help",
                    description="Register and request access")
async def handle_start(rbac: RBAC, message: Message, user_id: int) -> None:
    """Handle /start — register the user as Guest and alert SuperAdmins."""
    chat_id = message.chat.id
    from_user = message.from_field
    display_name = from_user.first_name if from_user else str(user_id)
    logger.info("User invoked /start", extra={"user_id": user_id, "chat_id": chat_id, "command": "/start"})

    existing = rbac.users.get(str(user_id))
    if existing is not None:
        role_name = rbac.get_role_name(user_id)
        await send_message(chat_id, f"👋 Welcome back, {display_name}! Your current role is *{role_name}*.")
        logger.info("Returning user invoked /start", extra={"user_id": user_id, "role": role_name, "command": "/start"})
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
    logger.info("New user registered as Guest", extra={"user_id": user_id, "role": "Guest", "level": 0})

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
        logger.info("Sent approval alert", extra={"user_id": user_id, "admin_id": admin_id, "action": "approval_alert"})


@registry.register("/help", action="view_help",
                    description="Show available commands")
async def handle_help(rbac: RBAC, message: Message, user_id: int) -> None:
    """Handle /help — show commands the user is permitted to use as inline buttons."""
    chat_id = message.chat.id
    logger.info("User invoked /help", extra={"user_id": user_id, "chat_id": chat_id, "command": "/help"})

    buttons: list[list[dict]] = []
    for cmd, entry in registry.entries().items():
        if rbac.has_permission(user_id, entry.action):
            buttons.append([{"text": f"{cmd} — {entry.description}", "callback_data": cmd}])

    if not buttons:
        await send_message(chat_id, "⛔ You have no available commands.")
        return

    markup = {"inline_keyboard": buttons}
    await send_message(chat_id, "📖 Available commands (tap to use):", reply_markup=markup)


@registry.register("/status", action="view_help",
                    description="View your rank and permissions")
async def handle_status(rbac: RBAC, message: Message, user_id: int) -> None:
    """Handle /status — show the user's rank level and permissions."""
    chat_id = message.chat.id
    logger.info("User invoked /status", extra={"user_id": user_id, "chat_id": chat_id, "command": "/status"})

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


@registry.register("/stop", action="view_help",
                    description="End your session", needs_rbac=False)
@registry.register("/exit", action="view_help",
                    description="End your session", needs_rbac=False)
async def handle_stop(message: Message, user_id: int) -> None:
    """Handle /stop and /exit — session termination."""
    chat_id = message.chat.id
    logger.info("User invoked /stop or /exit", extra={"user_id": user_id, "chat_id": chat_id, "command": "/stop"})
    await send_message(chat_id, "👋 Session ended. Use /start to begin again.")


@registry.register("/kick", action="kick_user",
                    description="Kick a user from the chat")
async def handle_kick(rbac: RBAC, message: Message, user_id: int) -> None:
    """Handle the /kick command.

    Usage: /kick <user_id>
    Requires the 'kick_user' action permission.
    """
    chat_id = message.chat.id
    logger.info("User invoked /kick", extra={"user_id": user_id, "chat_id": chat_id, "command": "/kick"})

    if not rbac.has_permission(user_id, "kick_user"):
        logger.warning("Unauthorised /kick attempt", extra={"user_id": user_id, "chat_id": chat_id, "command": "/kick", "action": "kick_user"})
        await send_message(chat_id, "⛔ You do not have permission to kick users.")
        return

    parts = (message.text or "").split()
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
        logger.error("kickChatMember API error", extra={"user_id": user_id, "chat_id": chat_id, "command": "/kick", "error": str(exc)})
        await send_message(chat_id, "❌ Failed to reach Telegram API.")
        return

    if result.get("ok"):
        logger.info("User kicked successfully", extra={"user_id": user_id, "target_id": target_id, "chat_id": chat_id, "command": "/kick", "result": "ok"})
        await send_message(chat_id, f"✅ User {target_id} has been kicked.")
    else:
        description = result.get("description", "Unknown error")
        logger.warning("Kick failed", extra={"user_id": user_id, "target_id": target_id, "chat_id": chat_id, "command": "/kick", "error": description, "api_response": result})
        await send_message(chat_id, f"❌ Could not kick user: {description}")


@registry.register("/clear", action="view_help",
                    description="Clear chat history with the bot", needs_rbac=False)
async def handle_clear(message: Message, user_id: int) -> None:
    """Handle /clear — bulk-delete all messages from current down to 1.

    Builds the full range of message IDs (current_msg_id → 1) and sends
    them to Telegram's ``deleteMessages`` endpoint in batches of 100.
    """
    chat_id = message.chat.id
    current_msg_id = message.message_id
    logger.info("User invoked /clear", extra={"user_id": user_id, "chat_id": chat_id, "command": "/clear", "message_id": current_msg_id})

    if not current_msg_id:
        await send_message(chat_id, "❌ Could not determine message range.")
        return

    # Build the full list of message IDs from current down to 1.
    msg_ids = list(range(current_msg_id, 0, -1))

    deleted = await delete_messages(chat_id, msg_ids)

    logger.info("Cleared messages", extra={"user_id": user_id, "chat_id": chat_id, "command": "/clear", "deleted_count": deleted})
    await send_message(chat_id, f"🧹 Cleared {deleted} message(s).")


# ── /metadata command & image processing ─────────────────────────────────────


class ExifToolRunner:
    """OOP wrapper around the ExifTool CLI for async EXIF metadata extraction.

    Encapsulates subprocess execution, JSON parsing, and noisy-key stripping
    so that callers deal only with a clean ``dict``.
    """

    _STRIP_KEYS: frozenset[str] = frozenset({"ExifToolVersion", "Directory", "SourceFile"})
    """Internal ExifTool keys stripped from every result."""

    TELEGRAM_MSG_LIMIT: int = 4096
    """Maximum characters Telegram allows in a single message."""

    def __init__(self, exiftool_path: str) -> None:
        self._path = exiftool_path

    async def extract(self, file_path: str) -> dict:
        """Run ExifTool on *file_path* and return the cleaned metadata dict.

        Uses ``asyncio.create_subprocess_exec`` so the event loop is never
        blocked.  The ``-j`` flag produces JSON output.

        Raises:
            RuntimeError: If ExifTool exits with a non-zero return code.
            json.JSONDecodeError: If ExifTool output is not valid JSON.
        """
        proc = await asyncio.create_subprocess_exec(
            self._path, "-j", file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode().strip()
            raise RuntimeError(f"ExifTool failed (rc={proc.returncode}): {error_msg}")

        data = json.loads(stdout.decode())
        result = data[0] if isinstance(data, list) and data else {}

        for key in self._STRIP_KEYS:
            result.pop(key, None)

        logger.info("ExifTool extraction complete", extra={"file_path": file_path, "key_count": len(result), "metadata": result})
        return result

    @staticmethod
    def format_response(metadata: dict) -> str:
        """Format *metadata* as a Telegram-safe Markdown JSON code block.

        Truncates the output if it exceeds Telegram's 4096-character message
        limit.
        """
        formatted = json.dumps(metadata, indent=2, ensure_ascii=False)
        code_block = f"```json\n{formatted}\n```"
        if len(code_block) > ExifToolRunner.TELEGRAM_MSG_LIMIT:
            max_len = ExifToolRunner.TELEGRAM_MSG_LIMIT - len("```json\n\n… (truncated)\n```")
            code_block = f"```json\n{formatted[:max_len]}\n… (truncated)\n```"
        return code_block


# Module-level singleton — one ExifTool runner for the whole process.
_EXIFTOOL = ExifToolRunner(EXIFTOOL_PATH)


@contextlib.asynccontextmanager
async def _temp_file(directory: str, filename: str) -> AsyncIterator[str]:
    """Async context manager that yields a temp-file path and cleans up on exit.

    The directory is created if it does not exist.  The file is deleted in a
    background thread to avoid blocking the event loop.
    """
    await asyncio.to_thread(os.makedirs, directory, exist_ok=True)
    path = os.path.join(directory, filename)
    try:
        yield path
    finally:
        if os.path.exists(path):
            try:
                await asyncio.to_thread(os.remove, path)
                logger.debug("Cleaned up temp file", extra={"path": path})
            except OSError as exc:
                logger.error("Failed to clean up temp file", extra={"path": path, "error": str(exc)})


def _resolve_file_id(message: Message) -> str | None:
    """Extract the ``file_id`` from a message containing a photo or document.

    Uses typed SDK :class:`~sdk.models.PhotoSize` and :class:`~sdk.models.Document`
    attributes from the :class:`~sdk.models.Message` model directly.
    """
    if message.photo:
        return message.photo[-1].file_id
    if message.document:
        return message.document.file_id
    return None


@registry.register("/metadata", action="extract_metadata",
                    description="Extract EXIF metadata from an image")
async def handle_metadata(rbac: RBAC, message: Message, user_id: int) -> None:
    """Handle /metadata — prompt the user to upload an image for EXIF extraction."""
    chat_id = message.chat.id
    logger.info("User invoked /metadata", extra={"user_id": user_id, "chat_id": chat_id, "command": "/metadata"})

    if not rbac.has_permission(user_id, "extract_metadata"):
        logger.warning("Unauthorised /metadata attempt", extra={"user_id": user_id, "chat_id": chat_id, "command": "/metadata", "action": "extract_metadata"})
        await send_message(chat_id, "⛔ You do not have permission to extract metadata.")
        return

    _PENDING_METADATA.add(user_id)
    await send_message(
        chat_id,
        "📸 Please upload an image (as a photo or uncompressed document) "
        "to extract its EXIF metadata.",
    )


async def handle_metadata_upload(rbac: RBAC, message: Message, user_id: int) -> None:
    """Process a photo/document upload for EXIF metadata extraction.

    Orchestrates the pipeline: permission check → file-ID resolution →
    Telegram file download → ExifTool extraction → formatted response.
    Each step delegates to a dedicated helper or class method.
    """
    chat_id = message.chat.id

    if user_id not in _PENDING_METADATA:
        return
    _PENDING_METADATA.discard(user_id)

    # Re-check permission (belt-and-suspenders)
    if not rbac.has_permission(user_id, "extract_metadata"):
        await send_message(chat_id, "⛔ You do not have permission to extract metadata.")
        return

    # ── Resolve file_id via SDK models ────────────────────────────────────
    file_id = _resolve_file_id(message)
    if not file_id:
        await send_message(chat_id, "❌ Could not find a file in your message. Please try again with /metadata.")
        return

    try:
        # Step 1 — resolve the Telegram-side file path using telegram helper
        file_info = await get_file_info(file_id)
        if not file_info or not file_info.file_path:
            await send_message(chat_id, "❌ Failed to retrieve file info from Telegram.")
            return

        ext = os.path.splitext(file_info.file_path)[1] or ".jpg"
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp")

        # Step 2 & 3 — download and extract within temp-file lifecycle
        async with _temp_file(temp_dir, f"{user_id}{ext}") as local_path:
            file_bytes = await download_file(file_info.file_path)
            await asyncio.to_thread(_write_binary_file, local_path, file_bytes)
            logger.info("Downloaded file", extra={"user_id": user_id, "local_path": local_path, "file_id": file_id})

            metadata = await _EXIFTOOL.extract(local_path)

        await send_message(chat_id, _EXIFTOOL.format_response(metadata), parse_mode="Markdown")
        logger.info("Metadata extracted and sent", extra={"user_id": user_id, "chat_id": chat_id, "command": "/metadata", "key_count": len(metadata)})

    except RuntimeError as exc:
        logger.error("ExifTool error", extra={"user_id": user_id, "chat_id": chat_id, "error": str(exc)})
        await send_message(chat_id, f"❌ Metadata extraction failed: {exc}")
    except json.JSONDecodeError as exc:
        logger.error("JSON decode error from ExifTool", extra={"user_id": user_id, "chat_id": chat_id, "error": str(exc)})
        await send_message(chat_id, "❌ Failed to parse metadata output.")
    except Exception as exc:
        logger.error("Metadata extraction error", extra={"user_id": user_id, "chat_id": chat_id, "error": str(exc)})
        await send_message(chat_id, "❌ An error occurred during metadata extraction.")


def _write_binary_file(path: str, data: bytes) -> None:
    """Write binary *data* to *path* (intended to run via ``asyncio.to_thread``)."""
    with open(path, "wb") as fh:
        fh.write(data)


def _extract_user_metadata(entity: User | Chat | None) -> dict:
    """Extract rich metadata fields from an SDK User or Chat model.

    Iterates over :data:`core.rbac.USER_META_KEYS` (``username``,
    ``first_name``, ``last_name``, ``language_code``, ``is_premium``,
    ``is_special``) using ``getattr`` so fields that only exist on
    :class:`~sdk.models.User` (e.g. ``language_code``) safely return
    ``None`` when called on a :class:`~sdk.models.Chat` instance.
    """
    meta: dict = {}
    if entity is None:
        return meta
    for key in USER_META_KEYS:
        val = getattr(entity, key, None)
        if val is not None:
            meta[key] = val
    return meta
