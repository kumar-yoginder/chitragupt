"""Command handlers for Chitragupt bot.

Each public function handles a single Telegram slash-command and is invoked
by the dispatcher in :mod:`bot.dispatcher`.
"""

import asyncio
import json
import os

from config import BASE_URL, BOT_TOKEN, EXIFTOOL_PATH
from core.logger import ChitraguptLogger
from core.rbac import RBAC
from bot.telegram import send_message, delete_message, delete_messages, make_request

logger = ChitraguptLogger.get_logger()

# ── Conversation state: users awaiting image upload for /metadata ────────────
_pending_metadata: set[int] = set()

# ── Command definitions (slug → description) used by /help ───────────────────
COMMAND_PERMISSIONS: dict[str, dict[str, str]] = {
    "/start":  {"action": "view_help",    "description": "Register and request access"},
    "/help":   {"action": "view_help",    "description": "Show available commands"},
    "/status": {"action": "view_help",    "description": "View your rank and permissions"},
    "/kick":   {"action": "kick_user",    "description": "Kick a user from the chat"},
    "/stop":   {"action": "view_help",    "description": "End your session"},
    "/exit":   {"action": "view_help",    "description": "End your session"},
    "/clear":     {"action": "view_help",         "description": "Clear chat history with the bot"},
    "/metadata":  {"action": "extract_metadata",  "description": "Extract EXIF metadata from an image"},
}


async def handle_start(rbac: RBAC, message: dict, user_id: int) -> None:
    """Handle /start — register the user as Guest and alert SuperAdmins."""
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    display_name = from_user.get("first_name", str(user_id))
    logger.info("User %s invoked /start in chat %s", user_id, chat_id)

    existing = rbac.users.get(str(user_id))
    if existing is not None:
        role_name = rbac.get_role_name(user_id)
        await send_message(chat_id, f"👋 Welcome back, {display_name}! Your current role is *{role_name}*.")
        logger.info("Returning user %s (role=%s) invoked /start", user_id, role_name)
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
        await send_message(admin_id, alert_text, reply_markup=markup)
        logger.info("Sent approval alert for user %s to admin %s", user_id, admin_id)


async def handle_help(rbac: RBAC, message: dict, user_id: int) -> None:
    """Handle /help — show commands the user is permitted to use as inline buttons."""
    chat_id = message["chat"]["id"]
    logger.info("User %s invoked /help in chat %s", user_id, chat_id)

    buttons: list[list[dict]] = []
    for cmd, info in COMMAND_PERMISSIONS.items():
        if rbac.has_permission(user_id, info["action"]):
            buttons.append([{"text": f"{cmd} — {info['description']}", "callback_data": cmd}])

    if not buttons:
        await send_message(chat_id, "⛔ You have no available commands.")
        return

    markup = {"inline_keyboard": buttons}
    await send_message(chat_id, "📖 Available commands (tap to use):", reply_markup=markup)


async def handle_status(rbac: RBAC, message: dict, user_id: int) -> None:
    """Handle /status — show the user's rank level and permissions."""
    chat_id = message["chat"]["id"]
    logger.info("User %s invoked /status in chat %s", user_id, chat_id)

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


async def handle_stop(message: dict, user_id: int) -> None:
    """Handle /stop and /exit — session termination."""
    chat_id = message["chat"]["id"]
    logger.info("User %s invoked /stop or /exit in chat %s", user_id, chat_id)
    await send_message(chat_id, "👋 Session ended. Use /start to begin again.")


async def handle_kick(rbac: RBAC, message: dict, user_id: int) -> None:
    """Handle the /kick command.

    Usage: /kick <user_id>
    Requires the 'kick_user' action permission.
    """
    chat_id = message["chat"]["id"]
    logger.info("User %s invoked /kick in chat %s", user_id, chat_id)

    if not rbac.has_permission(user_id, "kick_user"):
        logger.warning("Unauthorised /kick attempt by user %s in chat %s", user_id, chat_id)
        await send_message(chat_id, "⛔ You do not have permission to kick users.")
        return

    parts = message.get("text", "").split()
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
        logger.error("kickChatMember error: %s", exc)
        await send_message(chat_id, "❌ Failed to reach Telegram API.")
        return

    if result.get("ok"):
        logger.info("User %s kicked target %s in chat %s", user_id, target_id, chat_id)
        await send_message(chat_id, f"✅ User {target_id} has been kicked.")
    else:
        description = result.get("description", "Unknown error")
        logger.warning("Kick failed for target %s in chat %s: %s", target_id, chat_id, description)
        await send_message(chat_id, f"❌ Could not kick user: {description}")


async def handle_clear(message: dict, user_id: int) -> None:
    """Handle /clear — bulk-delete all messages from current down to 1.

    Builds the full range of message IDs (current_msg_id → 1) and sends
    them to Telegram's ``deleteMessages`` endpoint in batches of 100.
    """
    chat_id = message["chat"]["id"]
    current_msg_id = message.get("message_id", 0)
    logger.info("User %s invoked /clear in chat %s (msg_id=%s)", user_id, chat_id, current_msg_id)

    if not current_msg_id:
        await send_message(chat_id, "❌ Could not determine message range.")
        return

    # Build the full list of message IDs from current down to 1.
    msg_ids = list(range(current_msg_id, 0, -1))

    deleted = await delete_messages(chat_id, msg_ids)

    logger.info("Cleared %d message(s) for user %s in chat %s", deleted, user_id, chat_id)
    await send_message(chat_id, f"🧹 Cleared {deleted} message(s).")


# ── /metadata command & image processing ─────────────────────────────────────

async def handle_metadata(rbac: RBAC, message: dict, user_id: int) -> None:
    """Handle /metadata — prompt the user to upload an image for EXIF extraction."""
    chat_id = message["chat"]["id"]
    logger.info("User %s invoked /metadata in chat %s", user_id, chat_id)

    if not rbac.has_permission(user_id, "extract_metadata"):
        logger.warning("Unauthorised /metadata attempt by user %s in chat %s", user_id, chat_id)
        await send_message(chat_id, "⛔ You do not have permission to extract metadata.")
        return

    _pending_metadata.add(user_id)
    await send_message(
        chat_id,
        "📸 Please upload an image (as a photo or uncompressed document) "
        "to extract its EXIF metadata.",
    )


async def get_image_metadata(file_path: str) -> dict:
    """Run ExifTool on *file_path* and return the parsed metadata dict.

    Uses ``asyncio.create_subprocess_exec`` so the event loop is never
    blocked.  The ``-j`` flag ensures JSON output; ``-G`` includes group
    names for better organisation.
    """
    proc = await asyncio.create_subprocess_exec(
        EXIFTOOL_PATH, "-j", file_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        error_msg = stderr.decode().strip()
        raise RuntimeError(f"ExifTool failed (rc={proc.returncode}): {error_msg}")

    data = json.loads(stdout.decode())
    if isinstance(data, list) and data:
        result = data[0]
    else:
        result = {}

    # Strip noisy/internal keys from the output
    for key in ("ExifToolVersion", "Directory", "SourceFile"):
        result.pop(key, None)

    logger.info("ExifTool output for %s: %s", file_path, json.dumps(result, ensure_ascii=False))

    return result


async def handle_metadata_upload(rbac: RBAC, message: dict, user_id: int) -> None:
    """Process a photo/document upload for EXIF metadata extraction.

    Called by the dispatcher when a user who previously issued ``/metadata``
    sends a message containing a photo or document.
    """
    chat_id = message["chat"]["id"]

    if user_id not in _pending_metadata:
        return
    _pending_metadata.discard(user_id)

    # Re-check permission (belt-and-suspenders)
    if not rbac.has_permission(user_id, "extract_metadata"):
        await send_message(chat_id, "⛔ You do not have permission to extract metadata.")
        return

    # ── Resolve file_id ──────────────────────────────────────────────────
    file_id: str | None = None
    if message.get("photo"):
        # photo is a list of PhotoSize objects; last element is the largest
        file_id = message["photo"][-1]["file_id"]
    elif message.get("document"):
        file_id = message["document"]["file_id"]

    if not file_id:
        await send_message(chat_id, "❌ Could not find a file in your message. Please try again with /metadata.")
        return

    # ── Download file via Telegram getFile API ───────────────────────────
    temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    local_path: str | None = None

    try:
        # Step 1 — resolve the Telegram-side file path
        resp = await make_request(
            "get",
            f"{BASE_URL}/getFile",
            params={"file_id": file_id},
            timeout=10,
        )
        file_info = resp.json()
        if not file_info.get("ok"):
            await send_message(chat_id, "❌ Failed to retrieve file info from Telegram.")
            return
        telegram_file_path: str = file_info["result"]["file_path"]

        # Use 64-bit user ID in the filename to prevent parallel-user conflicts
        ext = os.path.splitext(telegram_file_path)[1] or ".jpg"
        local_path = os.path.join(temp_dir, f"{user_id}{ext}")

        # Step 2 — download the binary content
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{telegram_file_path}"
        dl_resp = await make_request("get", download_url, timeout=30)
        dl_resp.raise_for_status()

        await asyncio.to_thread(_write_binary_file, local_path, dl_resp.content)
        logger.info("Downloaded file for user %s → %s", user_id, local_path)

        # Step 3 — extract metadata
        metadata = await get_image_metadata(local_path)
        formatted = json.dumps(metadata, indent=2, ensure_ascii=False)

        # Telegram message limit is 4096 chars; truncate if necessary
        code_block = f"```json\n{formatted}\n```"
        if len(code_block) > 4096:
            max_len = 4096 - len("```json\n\n… (truncated)\n```")
            code_block = f"```json\n{formatted[:max_len]}\n… (truncated)\n```"

        await send_message(chat_id, code_block, parse_mode="Markdown")
        logger.info("Metadata extracted and sent for user %s in chat %s", user_id, chat_id)

    except RuntimeError as exc:
        logger.error("ExifTool error for user %s: %s", user_id, exc)
        await send_message(chat_id, f"❌ Metadata extraction failed: {exc}")
    except json.JSONDecodeError as exc:
        logger.error("JSON decode error from ExifTool for user %s: %s", user_id, exc)
        await send_message(chat_id, "❌ Failed to parse metadata output.")
    except Exception as exc:
        logger.error("Metadata extraction error for user %s: %s", user_id, exc)
        await send_message(chat_id, "❌ An error occurred during metadata extraction.")
    finally:
        # Always delete the temp file
        if local_path:
            try:
                await asyncio.to_thread(os.remove, local_path)
                logger.debug("Cleaned up temp file %s", local_path)
            except OSError as exc:
                logger.error("Failed to clean up temp file %s: %s", local_path, exc)


def _write_binary_file(path: str, data: bytes) -> None:
    """Write binary *data* to *path* (intended to run via ``asyncio.to_thread``)."""
    with open(path, "wb") as fh:
        fh.write(data)


def _extract_user_metadata(from_user: dict) -> dict:
    """Extract rich metadata fields from a Telegram ``from`` object."""
    meta: dict = {}
    for key in ("username", "first_name", "last_name", "language_code", "is_premium"):
        val = from_user.get(key)
        if val is not None:
            meta[key] = val
    return meta
