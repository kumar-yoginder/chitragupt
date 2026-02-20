"""Tests for command handlers and callback query processing."""

import json
import sys
import os
from unittest.mock import patch, AsyncMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.rbac import RBAC
from sdk.models import CallbackQuery, Chat, Message, User


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def rbac(tmp_path):
    """Create an RBAC instance backed by temporary JSON files."""
    rules = {
        "roles": [
            {"level": 0, "name": "Guest", "actions": ["view_help"]},
            {"level": 10, "name": "Member", "actions": ["view_help"]},
            {"level": 50, "name": "Moderator", "actions": ["view_help", "kick_user", "delete_msg"]},
            {"level": 80, "name": "Admin", "actions": ["view_help", "kick_user", "delete_msg", "ban_user", "mute_user", "manage_users"]},
            {"level": 100, "name": "SuperAdmin", "actions": ["*"]},
        ]
    }
    users = {
        "100": {"name": "SuperAdmin", "level": 100},
        "200": {"name": "AdminUser", "level": 80},
        "300": {"name": "ModUser", "level": 50},
        "400": {"name": "MemberUser", "level": 10},
    }
    rules_path = tmp_path / "db_rules.json"
    users_path = tmp_path / "db_users.json"
    rules_path.write_text(json.dumps(rules))
    users_path.write_text(json.dumps(users))
    return RBAC(rules_path=str(rules_path), users_path=str(users_path))


def _make_message(user_id: int, text: str, chat_id: int = 1000) -> Message:
    """Build a minimal SDK Message model for handler tests."""
    return Message(
        message_id=1,
        date=0,
        chat=Chat(id=chat_id, type="private"),
        from_field=User(id=user_id, is_bot=False, first_name=f"User{user_id}"),
        text=text,
    )


def _make_update(user_id: int, text: str, chat_id: int = 1000) -> dict:
    """Build a minimal Telegram update dict with a message.

    Serialises the SDK Message back to a plain dict so that
    :func:`core.identity.get_identity` (which operates on raw dicts)
    and ``Update.model_validate`` both work correctly.
    """
    msg = _make_message(user_id, text, chat_id)
    return {
        "update_id": 1,
        "message": msg.model_dump(by_alias=True, exclude_none=True),
    }


def _make_callback_query(
    admin_id: int, data: str, chat_id: int = 1000, cb_id: str = "cb123"
) -> dict:
    """Build a minimal callback_query update dict."""
    return {
        "update_id": 2,
        "callback_query": {
            "id": cb_id,
            "from": {"id": admin_id, "is_bot": False, "first_name": f"Admin{admin_id}"},
            "chat_instance": "test",
            "message": {
                "message_id": 10,
                "date": 0,
                "chat": {"id": chat_id, "type": "private"},
            },
            "data": data,
        },
    }


# ── RBAC helper methods ─────────────────────────────────────────────────────


class TestRBACHelpers:
    """Validate new RBAC helper methods."""

    def test_get_role_name_known(self, rbac) -> None:
        assert rbac.get_role_name(100) == "SuperAdmin"
        assert rbac.get_role_name(400) == "Member"

    def test_get_role_name_unknown(self, rbac) -> None:
        assert rbac.get_role_name(9999) == "Guest"

    def test_get_user_actions(self, rbac) -> None:
        actions = rbac.get_user_actions(300)
        assert "kick_user" in actions

    def test_get_user_actions_unknown(self, rbac) -> None:
        actions = rbac.get_user_actions(9999)
        assert "view_help" in actions

    def test_get_superadmins(self, rbac) -> None:
        admins = rbac.get_superadmins()
        assert 100 in admins
        assert 200 not in admins

    def test_get_superadmins_empty(self, tmp_path) -> None:
        rules = {"roles": [{"level": 0, "name": "Guest", "actions": ["view_help"]}]}
        users = {"1": {"name": "test", "level": 0}}
        rules_path = tmp_path / "rules.json"
        users_path = tmp_path / "users.json"
        rules_path.write_text(json.dumps(rules))
        users_path.write_text(json.dumps(users))
        r = RBAC(rules_path=str(rules_path), users_path=str(users_path))
        assert r.get_superadmins() == []


# ── /start handler ───────────────────────────────────────────────────────────


class TestHandleStart:
    """Validate /start command registration and admin alerts."""

    @pytest.mark.asyncio
    @patch("bot.handlers.send_message", new_callable=AsyncMock)
    async def test_new_user_registered_as_guest(self, mock_send, rbac) -> None:
        from bot.handlers import handle_start

        msg = _make_message(999, "/start")
        await handle_start(rbac, msg, 999)

        # User should be persisted at level 0
        assert rbac.get_user_level(999) == 0
        assert rbac.users["999"]["name"] == "User999"

        # Welcome message sent
        first_call_text = mock_send.call_args_list[0][0][1]
        assert "Welcome" in first_call_text
        assert "pending" in first_call_text

    @pytest.mark.asyncio
    @patch("bot.handlers.send_message", new_callable=AsyncMock)
    async def test_new_user_alerts_superadmins(self, mock_send, rbac) -> None:
        from bot.handlers import handle_start

        msg = _make_message(999, "/start")
        await handle_start(rbac, msg, 999)

        # Should have sent: 1 welcome + 1 alert to SuperAdmin(100)
        assert mock_send.call_count == 2
        admin_call = mock_send.call_args_list[1]
        assert admin_call[0][0] == 100  # sent to admin
        assert "reply_markup" in admin_call[1]
        markup = admin_call[1]["reply_markup"]
        assert "inline_keyboard" in markup

    @pytest.mark.asyncio
    @patch("bot.handlers.send_message", new_callable=AsyncMock)
    async def test_returning_user_no_reregistration(self, mock_send, rbac) -> None:
        from bot.handlers import handle_start

        msg = _make_message(400, "/start")
        await handle_start(rbac, msg, 400)

        # Level should remain 10 (Member), not reset to 0
        assert rbac.get_user_level(400) == 10
        first_call_text = mock_send.call_args_list[0][0][1]
        assert "Welcome back" in first_call_text


# ── /help handler ────────────────────────────────────────────────────────────


class TestHandleHelp:
    """Validate /help displays permission-aware buttons."""

    @pytest.mark.asyncio
    @patch("bot.handlers.send_message", new_callable=AsyncMock)
    async def test_guest_sees_basic_commands(self, mock_send, rbac) -> None:
        from bot.handlers import handle_help

        msg = _make_message(9999, "/help")
        await handle_help(rbac, msg, 9999)  # Unknown user → Guest

        call_args = mock_send.call_args
        assert "reply_markup" in call_args[1]
        markup = call_args[1]["reply_markup"]
        # Guest should see /start, /help, /status, /stop, /exit but NOT /kick
        button_texts = [btn["text"] for row in markup["inline_keyboard"] for btn in row]
        assert any("/help" in t for t in button_texts)
        assert not any("/kick" in t for t in button_texts)

    @pytest.mark.asyncio
    @patch("bot.handlers.send_message", new_callable=AsyncMock)
    async def test_moderator_sees_kick(self, mock_send, rbac) -> None:
        from bot.handlers import handle_help

        msg = _make_message(300, "/help")
        await handle_help(rbac, msg, 300)

        call_args = mock_send.call_args
        markup = call_args[1]["reply_markup"]
        button_texts = [btn["text"] for row in markup["inline_keyboard"] for btn in row]
        assert any("/kick" in t for t in button_texts)


# ── /status handler ──────────────────────────────────────────────────────────


class TestHandleStatus:
    """Validate /status shows rank info."""

    @pytest.mark.asyncio
    @patch("bot.handlers.send_message", new_callable=AsyncMock)
    async def test_status_shows_role(self, mock_send, rbac) -> None:
        from bot.handlers import handle_status

        msg = _make_message(300, "/status")
        await handle_status(rbac, msg, 300)

        text = mock_send.call_args[0][1]
        assert "Moderator" in text
        assert "50" in text
        assert "kick_user" in text


# ── /stop and /exit ──────────────────────────────────────────────────────────


class TestHandleStop:
    """Validate /stop and /exit handlers."""

    @pytest.mark.asyncio
    @patch("bot.handlers.send_message", new_callable=AsyncMock)
    async def test_stop(self, mock_send) -> None:
        from bot.handlers import handle_stop

        msg = _make_message(400, "/stop")
        await handle_stop(msg, 400)
        text = mock_send.call_args[0][1]
        assert "Session ended" in text

    @pytest.mark.asyncio
    @patch("bot.handlers.send_message", new_callable=AsyncMock)
    async def test_exit(self, mock_send) -> None:
        from bot.handlers import handle_stop

        msg = _make_message(400, "/exit")
        await handle_stop(msg, 400)
        assert mock_send.called


# ── Callback query (admin approval) ─────────────────────────────────────────


class TestCallbackApproval:
    """Validate the admin approval flow via callback queries."""

    @pytest.mark.asyncio
    @patch("bot.callbacks.answer_callback_query", new_callable=AsyncMock)
    @patch("bot.callbacks.send_message", new_callable=AsyncMock)
    async def test_approve_member(self, mock_send, mock_answer, rbac) -> None:
        from bot.callbacks import handle_callback_query

        # First register the target user
        await rbac.set_user_level(999, 0, name="NewUser")

        cb_dict = _make_callback_query(100, "approve_member:999")["callback_query"]
        cb = CallbackQuery.model_validate(cb_dict)
        await handle_callback_query(rbac, cb, 100)

        # User level should be updated to 10
        assert rbac.get_user_level(999) == 10
        mock_answer.assert_called_once()
        # Two send_message calls: one to admin, one to user
        assert mock_send.call_count == 2

    @pytest.mark.asyncio
    @patch("bot.callbacks.answer_callback_query", new_callable=AsyncMock)
    @patch("bot.callbacks.send_message", new_callable=AsyncMock)
    async def test_promote_mod(self, mock_send, mock_answer, rbac) -> None:
        from bot.callbacks import handle_callback_query

        await rbac.set_user_level(999, 0, name="NewUser")

        cb_dict = _make_callback_query(100, "promote_mod:999")["callback_query"]
        cb = CallbackQuery.model_validate(cb_dict)
        await handle_callback_query(rbac, cb, 100)

        assert rbac.get_user_level(999) == 50
        mock_answer.assert_called_once()

    @pytest.mark.asyncio
    @patch("bot.callbacks.answer_callback_query", new_callable=AsyncMock)
    @patch("bot.callbacks.send_message", new_callable=AsyncMock)
    async def test_reject(self, mock_send, mock_answer, rbac) -> None:
        from bot.callbacks import handle_callback_query

        await rbac.set_user_level(999, 0, name="NewUser")

        cb_dict = _make_callback_query(100, "reject:999")["callback_query"]
        cb = CallbackQuery.model_validate(cb_dict)
        await handle_callback_query(rbac, cb, 100)

        # Level unchanged (still Guest)
        assert rbac.get_user_level(999) == 0
        mock_answer.assert_called_once()
        assert mock_send.call_count == 2

    @pytest.mark.asyncio
    @patch("bot.callbacks.answer_callback_query", new_callable=AsyncMock)
    @patch("bot.callbacks.send_message", new_callable=AsyncMock)
    async def test_non_admin_cannot_approve(self, mock_send, mock_answer, rbac) -> None:
        from bot.callbacks import handle_callback_query

        await rbac.set_user_level(999, 0, name="NewUser")

        # User 400 is a Member (level 10) — no manage_users permission
        cb_dict = _make_callback_query(400, "approve_member:999")["callback_query"]
        cb = CallbackQuery.model_validate(cb_dict)
        await handle_callback_query(rbac, cb, 400)

        # Level should still be 0
        assert rbac.get_user_level(999) == 0
        mock_answer.assert_called_once()
        answer_text = mock_answer.call_args[0][1]
        assert "permission" in answer_text.lower()


# ── process_update dispatch ──────────────────────────────────────────────────


class TestProcessUpdate:
    """Validate that process_update dispatches to the right handlers via the registry."""

    @pytest.mark.asyncio
    @patch("bot.handlers.send_message", new_callable=AsyncMock)
    async def test_dispatches_start(self, mock_send, rbac) -> None:
        from bot.dispatcher import process_update

        update = _make_update(999, "/start")
        await process_update(rbac, update)
        # /start for an unknown user sends a welcome message
        assert mock_send.called
        first_text = mock_send.call_args_list[0][0][1]
        assert "Welcome" in first_text

    @pytest.mark.asyncio
    @patch("bot.handlers.send_message", new_callable=AsyncMock)
    async def test_dispatches_help(self, mock_send, rbac) -> None:
        from bot.dispatcher import process_update

        update = _make_update(400, "/help")
        await process_update(rbac, update)
        assert mock_send.called

    @pytest.mark.asyncio
    @patch("bot.handlers.send_message", new_callable=AsyncMock)
    async def test_dispatches_status(self, mock_send, rbac) -> None:
        from bot.dispatcher import process_update

        update = _make_update(300, "/status")
        await process_update(rbac, update)
        text = mock_send.call_args[0][1]
        assert "Moderator" in text

    @pytest.mark.asyncio
    @patch("bot.handlers.send_message", new_callable=AsyncMock)
    async def test_dispatches_stop(self, mock_send, rbac) -> None:
        from bot.dispatcher import process_update

        update = _make_update(400, "/stop")
        await process_update(rbac, update)
        text = mock_send.call_args[0][1]
        assert "Session ended" in text

    @pytest.mark.asyncio
    @patch("bot.handlers.send_message", new_callable=AsyncMock)
    async def test_dispatches_exit(self, mock_send, rbac) -> None:
        from bot.dispatcher import process_update

        update = _make_update(400, "/exit")
        await process_update(rbac, update)
        text = mock_send.call_args[0][1]
        assert "Session ended" in text

    @pytest.mark.asyncio
    @patch("bot.handlers.make_request", new_callable=AsyncMock)
    @patch("bot.handlers.send_message", new_callable=AsyncMock)
    async def test_dispatches_kick(self, mock_send, mock_req, rbac) -> None:
        from unittest.mock import MagicMock
        from bot.dispatcher import process_update

        # make_request returns a Response-like object (sync .json())
        fake_response = MagicMock()
        fake_response.json.return_value = {"ok": True}
        mock_req.return_value = fake_response

        update = _make_update(100, "/kick 999")
        await process_update(rbac, update)
        # SuperAdmin (100) can kick — should call the API
        assert mock_req.called

    @pytest.mark.asyncio
    @patch("bot.dispatcher.handle_callback_query", new_callable=AsyncMock)
    async def test_dispatches_callback_query(self, mock_handler, rbac) -> None:
        from bot.dispatcher import process_update

        update = _make_callback_query(100, "approve_member:999")
        await process_update(rbac, update)
        mock_handler.assert_called_once()


# ── Identity resolution for callback_query ───────────────────────────────────


class TestIdentityCallbackQuery:
    """Validate get_identity handles callback_query updates."""

    def test_callback_from_user(self) -> None:
        from core.identity import get_identity

        update = _make_callback_query(42, "approve_member:999")
        assert get_identity(update) == 42

    def test_callback_sender_chat(self) -> None:
        from core.identity import get_identity

        update = {
            "update_id": 3,
            "callback_query": {
                "id": "cb1",
                "from": {"id": 42, "is_bot": False, "first_name": "X"},
                "message": {
                    "message_id": 10,
                    "date": 0,
                    "chat": {"id": 1000, "type": "private"},
                    "sender_chat": {"id": -1001234},
                },
                "data": "test",
            },
        }
        # sender_chat in the message takes priority
        assert get_identity(update) == -1001234


# ── Rich metadata storage ───────────────────────────────────────────────────


class TestRichMetadata:
    """Validate RBAC stores rich user metadata fields."""

    @pytest.mark.asyncio
    async def test_set_user_level_with_metadata(self, rbac) -> None:
        await rbac.set_user_level(
            777, 10, name="TestUser",
            username="testuser", first_name="Test", last_name="User",
            language_code="en", is_premium=True, is_special=False,
        )
        entry = rbac.users["777"]
        assert entry["level"] == 10
        assert entry["username"] == "testuser"
        assert entry["first_name"] == "Test"
        assert entry["last_name"] == "User"
        assert entry["language_code"] == "en"
        assert entry["is_premium"] is True
        assert entry["is_special"] is False

    @pytest.mark.asyncio
    async def test_sync_super_admin_rich_metadata(self, rbac) -> None:
        await rbac.sync_super_admin(
            888, "Admin", username="admin_bot", first_name="Admin",
            language_code="de",
        )
        entry = rbac.users["888"]
        assert entry["level"] == 100
        assert entry["username"] == "admin_bot"
        assert entry["first_name"] == "Admin"
        assert entry["language_code"] == "de"

    @pytest.mark.asyncio
    async def test_sync_super_admin_updates_changed_metadata(self, rbac) -> None:
        await rbac.sync_super_admin(888, "Admin", username="old_name")
        assert rbac.users["888"]["username"] == "old_name"

        await rbac.sync_super_admin(888, "Admin", username="new_name")
        assert rbac.users["888"]["username"] == "new_name"


# ── asyncio.Lock safety ─────────────────────────────────────────────────────


class TestAsyncLock:
    """Validate the asyncio.Lock prevents concurrent write corruption."""

    @pytest.mark.asyncio
    async def test_parallel_writes_do_not_corrupt(self, rbac) -> None:
        """Fire many set_user_level calls concurrently — file should stay valid."""
        import asyncio

        tasks = [rbac.set_user_level(i, 10, name=f"user{i}") for i in range(500, 520)]
        await asyncio.gather(*tasks)

        # All 20 new users must be present
        for i in range(500, 520):
            assert str(i) in rbac.users

        # The persisted file must be valid JSON
        with open(rbac.users_path) as f:
            on_disk = json.load(f)
        for i in range(500, 520):
            assert str(i) in on_disk
