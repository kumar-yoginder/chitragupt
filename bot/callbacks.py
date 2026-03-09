"""Callback-query handlers for inline keyboard interactions.

Processes button presses from SuperAdmin approval flows and the /help
command menu.  When a user taps a command button from /help, the
corresponding handler is invoked directly — no need to re-type the command.
"""

from sdk.models import CallbackQuery, Chat, Message
from core.logger import ChitraguptLogger
from core.rbac import RBAC
from bot.registry import registry
from sdk.client import answer_callback_query, send_message

logger = ChitraguptLogger.get_logger()


def _build_synthetic_message(callback_query: CallbackQuery, text: str) -> Message:
    """Build a minimal SDK :class:`~sdk.models.Message` from a callback query.

    Command handlers receive the same typed interface they would from a
    regular text message.  Fallback values (``message_id=0``, ``date=0``,
    a private chat with ``id=0``) are used only when the callback query
    has no attached message — an edge case for inline-mode callbacks.
    """
    cb_message = callback_query.message
    return Message(
        message_id=cb_message.message_id if cb_message else 0,
        date=cb_message.date if cb_message else 0,
        chat=cb_message.chat if cb_message else Chat(id=0, type="private"),
        from_field=callback_query.from_field,
        text=text,
    )


async def handle_callback_query(rbac: RBAC, callback_query: CallbackQuery, user_id: int) -> None:
    """Dispatch callback queries from inline keyboard buttons.

    Identity (*user_id*) is resolved by the dispatcher via
    :func:`core.identity.get_identity` before this function is called.
    """
    cb_id = callback_query.id
    data = callback_query.data or ""
    chat_id = callback_query.message.chat.id if callback_query.message else None

    if chat_id is None:
        logger.warning("Callback query missing chat", extra={"callback_query_id": cb_id})
        await answer_callback_query(cb_id, "❌ Could not process.")
        return

    logger.info("Callback query received", extra={"user_id": user_id, "chat_id": chat_id, "callback_data": data})

    # Approval / rejection flow (SuperAdmin buttons)
    if ":" in data and data.split(":")[0] in ("approve_member", "promote_mod", "reject"):
        await _handle_approval_callback(rbac, cb_id, data, user_id, chat_id)
        return

    # Group/user management flow
    if (data.startswith("manage_group:") or data.startswith("manage_user:") or 
        data.startswith("manage_chat:") or data.startswith("set_level:") or
        data.startswith("list_users:") or data.startswith("user_menu:") or
        data.startswith("change_level:") or data == "refresh_list"):
        await _handle_manage_callback(rbac, cb_id, data, user_id, chat_id)
        return

    # /help menu command buttons
    if data.startswith("/"):
        await _handle_command_callback(rbac, cb_id, data, callback_query, user_id)
        return

    # Fallback — unknown callback
    logger.debug("Unknown callback data", extra={"user_id": user_id, "callback_data": data})
    await answer_callback_query(cb_id)


async def _handle_command_callback(
    rbac: RBAC,
    cb_id: str,
    command: str,
    callback_query: CallbackQuery,
    user_id: int,
) -> None:
    """Execute the command handler that corresponds to an inline-button tap.

    A synthetic :class:`~sdk.models.Message` is built from the callback query
    so that each handler receives the same typed interface it would from a
    regular text message.  Uses the shared :data:`bot.registry.registry` for
    dispatch so new commands are automatically available without editing this
    module.
    """
    message = _build_synthetic_message(callback_query, command)
    chat_id = message.chat.id

    # Acknowledge the button press immediately so the spinner disappears.
    await answer_callback_query(cb_id, f"Running {command}…")

    if not await registry.dispatch(command, rbac, message, user_id):
        logger.debug("No handler mapped for command callback", extra={"command": command, "user_id": user_id})
        await send_message(chat_id, f"⚠️ Unknown command: {command}")


async def _handle_approval_callback(
    rbac: RBAC, cb_id: str, data: str, admin_id: int, admin_chat_id: int
) -> None:
    """Process approve/promote/reject callbacks for user registration."""
    action, _, target_id_str = data.partition(":")

    try:
        target_id = int(target_id_str)
    except ValueError:
        logger.error("Invalid target_id in callback data", extra={"callback_data": data, "admin_id": admin_id})
        await answer_callback_query(cb_id, "❌ Invalid user data.")
        return

    if not rbac.has_permission(admin_id, "manage_users"):
        logger.warning("Unauthorised approval attempt", extra={"admin_id": admin_id, "action": "manage_users", "callback_data": data})
        await answer_callback_query(cb_id, "⛔ You do not have permission to approve users.")
        return

    if action == "approve_member":
        await rbac.set_user_level(target_id, 10)
        await answer_callback_query(cb_id, f"✅ User {target_id} approved as Member.")
        await send_message(admin_chat_id, f"✅ User {target_id} has been approved as Member (Level 10).")
        await send_message(target_id, "🎉 Your access has been approved! You are now a Member.")
        logger.info("Admin approved user as Member", extra={"admin_id": admin_id, "target_id": target_id, "action": "approve_member", "new_level": 10})

    elif action == "promote_mod":
        await rbac.set_user_level(target_id, 50)
        await answer_callback_query(cb_id, f"🛡️ User {target_id} promoted to Moderator.")
        await send_message(admin_chat_id, f"🛡️ User {target_id} has been promoted to Moderator (Level 50).")
        await send_message(target_id, "🎉 You have been promoted to Moderator!")
        logger.info("Admin promoted user to Moderator", extra={"admin_id": admin_id, "target_id": target_id, "action": "promote_mod", "new_level": 50})

    elif action == "reject":
        await answer_callback_query(cb_id, f"❌ User {target_id} rejected.")
        await send_message(admin_chat_id, f"❌ User {target_id} has been rejected.")
        await send_message(target_id, "❌ Your access request has been rejected by an admin.")
        logger.info("Admin rejected user", extra={"admin_id": admin_id, "target_id": target_id, "action": "reject"})


async def _handle_manage_callback(
    rbac: RBAC, cb_id: str, data: str, admin_id: int, admin_chat_id: int
) -> None:
    """Process group/user management and pagination callbacks.

    Supports these callback_data prefixes:
    - ``manage_chat:<chat_id>`` — show options for managing a specific chat.
    - ``list_users:<page>`` — show paginated user list.
    - ``user_menu:<user_id>`` — show user management options.
    - ``manage_group:<group_id>`` — list users in the selected group (legacy).
    - ``manage_user:<user_id>`` — show level-change buttons for a user (legacy).
    - ``set_level:<user_id>:<new_level>`` — change a user's level.
    """
    # Permission gate
    if not rbac.has_permission(admin_id, "manage_users"):
        logger.warning("Unauthorised manage callback", extra={"admin_id": admin_id, "action": "manage_users", "callback_data": data})
        await answer_callback_query(cb_id, "⛔ You do not have permission to manage users.")
        return

    if data.startswith("list_users:"):
        # Pagination for user list
        _, _, page_str = data.partition(":")
        try:
            page = int(page_str)
        except ValueError:
            await answer_callback_query(cb_id, "❌ Invalid page.")
            return
        
        await answer_callback_query(cb_id)
        from bot.handlers import send_paginated_users
        await send_paginated_users(admin_chat_id, rbac, page)

    elif data.startswith("user_menu:"):
        # Directly show level selection options for the user
        _, _, target_id_str = data.partition(":")
        try:
            target_id = int(target_id_str)
        except ValueError:
            await answer_callback_query(cb_id, "❌ Invalid user data.")
            return

        await answer_callback_query(cb_id)
        current_level = rbac.get_user_level(target_id)
        name = rbac.users.get(str(target_id), {}).get("name", str(target_id))
        
        buttons = [
            [{"text": "🔴 Guest (0)", "callback_data": f"set_level:{target_id}:0"}],
            [{"text": "🟢 Member (10)", "callback_data": f"set_level:{target_id}:10"}],
            [{"text": "🟡 Moderator (50)", "callback_data": f"set_level:{target_id}:50"}],
            [{"text": "🔵 Admin (80)", "callback_data": f"set_level:{target_id}:80"}],
            [{"text": "⬅️ Back to Users", "callback_data": "refresh_list"}]
        ]

        markup = {"inline_keyboard": buttons}
        await send_message(
            admin_chat_id,
            f"📊 *Select New Level for {name}*\n\n"
            f"Current Level: {current_level}",
            reply_markup=markup,
        )

    elif data.startswith("change_level:"):
        # Legacy handler for change_level (kept for backward compatibility)
        _, _, target_id_str = data.partition(":")
        try:
            target_id = int(target_id_str)
        except ValueError:
            await answer_callback_query(cb_id, "❌ Invalid user data.")
            return

        await answer_callback_query(cb_id)
        current_level = rbac.get_user_level(target_id)
        
        buttons = [
            [{"text": "🔴 Guest (0)", "callback_data": f"set_level:{target_id}:0"}],
            [{"text": "🟢 Member (10)", "callback_data": f"set_level:{target_id}:10"}],
            [{"text": "🟡 Moderator (50)", "callback_data": f"set_level:{target_id}:50"}],
            [{"text": "🔵 Admin (80)", "callback_data": f"set_level:{target_id}:80"}],
            [{"text": "⬅️ Back", "callback_data": f"user_menu:{target_id}"}]
        ]

        markup = {"inline_keyboard": buttons}
        await send_message(
            admin_chat_id,
            f"📊 *Select New Level* (Current: {current_level}):",
            reply_markup=markup,
        )

    elif data.startswith("manage_chat:"):
        # Show info about managed chat
        _, _, chat_id_str = data.partition(":")
        try:
            chat_id = int(chat_id_str)
        except ValueError:
            await answer_callback_query(cb_id, "❌ Invalid chat data.")
            return

        await answer_callback_query(cb_id)
        chat_info = rbac.get_chat_info(chat_id)
        if not chat_info:
            await send_message(admin_chat_id, "❌ Chat information not found.")
            return

        text = (
            f"📊 *Chat Information*\n\n"
            f"• Title: {chat_info.get('title', 'Unknown')}\n"
            f"• Type: {chat_info.get('type', 'unknown').upper()}\n"
            f"• Chat ID: {chat_id}\n"
        )

        buttons = [
            [{"text": "👥 Manage Users", "callback_data": "manage_group:users"}],
            [{"text": "⬅️ Back", "callback_data": "manage:list:0"}]
        ]

        markup = {"inline_keyboard": buttons}
        await send_message(admin_chat_id, text, reply_markup=markup)

    elif data.startswith("manage_group:"):
        # List users (non-group entries) for the admin to manage
        await answer_callback_query(cb_id, "Loading users…")
        buttons: list[list[dict]] = []
        for uid_str, entry in rbac.users.items():
            try:
                uid = int(uid_str)
            except ValueError:
                continue
            if uid >= 0:
                name = entry.get("name", uid_str)
                level = entry.get("level", 0)
                role = rbac.get_role_name(uid)
                buttons.append([{
                    "text": f"👤 {name} — {role} (Lv {level})",
                    "callback_data": f"manage_user:{uid_str}",
                }])

        if not buttons:
            await send_message(admin_chat_id, "ℹ️ No users found.")
            return

        markup = {"inline_keyboard": buttons}
        await send_message(admin_chat_id, "👥 Select a user to manage:", reply_markup=markup)

    elif data.startswith("manage_user:"):
        _, _, target_id_str = data.partition(":")
        try:
            target_id = int(target_id_str)
        except ValueError:
            await answer_callback_query(cb_id, "❌ Invalid user data.")
            return

        await answer_callback_query(cb_id, "Loading user options…")
        current_level = rbac.get_user_level(target_id)
        role_name = rbac.get_role_name(target_id)
        name = rbac.users.get(str(target_id), {}).get("name", str(target_id))

        buttons = []
        # Offer promote/demote options based on current level
        if current_level < 80:
            buttons.append([{"text": "⬆️ Promote to Admin (80)", "callback_data": f"set_level:{target_id}:80"}])
        if current_level < 50:
            buttons.append([{"text": "⬆️ Promote to Moderator (50)", "callback_data": f"set_level:{target_id}:50"}])
        if current_level < 10:
            buttons.append([{"text": "⬆️ Promote to Member (10)", "callback_data": f"set_level:{target_id}:10"}])
        if current_level > 10:
            buttons.append([{"text": "⬇️ Demote to Member (10)", "callback_data": f"set_level:{target_id}:10"}])
        if current_level > 0 and current_level != 10:
            buttons.append([{"text": "⬇️ Demote to Guest (0)", "callback_data": f"set_level:{target_id}:0"}])

        if not buttons:
            await send_message(admin_chat_id, f"ℹ️ No level changes available for {name}.")
            return

        markup = {"inline_keyboard": buttons}
        await send_message(
            admin_chat_id,
            f"⚙️ Managing user: {name}\n• Current role: {role_name} (Level {current_level})\n\nChoose an action:",
            reply_markup=markup,
        )

    elif data.startswith("set_level:"):
        parts = data.split(":")
        if len(parts) != 3:
            await answer_callback_query(cb_id, "❌ Invalid data.")
            return
        try:
            target_id = int(parts[1])
            new_level = int(parts[2])
        except ValueError:
            await answer_callback_query(cb_id, "❌ Invalid user or level.")
            return

        # Validate that new_level corresponds to a known role (not SuperAdmin)
        valid_levels = {lvl for lvl in rbac._rules_by_level if lvl < 100}
        if new_level not in valid_levels:
            await answer_callback_query(cb_id, "❌ Invalid role level.")
            return

        old_level = rbac.get_user_level(target_id)
        await rbac.set_user_level(target_id, new_level)
        new_role = rbac.get_role_name(target_id)
        name = rbac.users.get(str(target_id), {}).get("name", str(target_id))

        await answer_callback_query(cb_id, f"✅ {name} is now {new_role}.")
        await send_message(admin_chat_id, f"✅ {name} has been changed from Level {old_level} to {new_role} (Level {new_level}).")
        await send_message(target_id, f"🔔 Your role has been updated to {new_role} (Level {new_level}).")
        logger.info("User level changed via /manage", extra={
            "admin_id": admin_id, "target_id": target_id,
            "old_level": old_level, "new_level": new_level,
            "new_role": new_role,
        })
    elif data == "refresh_list":
        # Refresh user list
        await answer_callback_query(cb_id)
        from bot.handlers import send_user_list
        await send_user_list(admin_chat_id, rbac)

    elif data.startswith("list_users:"):
        # Legacy pagination support
        _, _, page_str = data.partition(":")
        try:
            page = int(page_str)
        except ValueError:
            await answer_callback_query(cb_id, "❌ Invalid page.")
            return
        
        await answer_callback_query(cb_id)
        from bot.handlers import send_user_list
        await send_user_list(admin_chat_id, rbac)