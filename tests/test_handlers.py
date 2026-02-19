"""Tests for command handlers and callback query processing in main.py."""

import json
import sys
import os
from unittest.mock import patch, MagicMock, call

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.rbac import RBAC


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


def _make_message(user_id: int, text: str, chat_id: int = 1000) -> dict:
    """Build a minimal Telegram message dict."""
    return {
        "message_id": 1,
        "date": 0,
        "chat": {"id": chat_id, "type": "private"},
        "from": {"id": user_id, "is_bot": False, "first_name": f"User{user_id}"},
        "text": text,
    }


def _make_update(user_id: int, text: str, chat_id: int = 1000) -> dict:
    """Build a minimal Telegram update dict with a message."""
    return {
        "update_id": 1,
        "message": _make_message(user_id, text, chat_id),
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

    @patch("main.send_message")
    def test_new_user_registered_as_guest(self, mock_send, rbac) -> None:
        from main import handle_start

        msg = _make_message(999, "/start")
        handle_start(rbac, msg, 999)

        # User should be persisted at level 0
        assert rbac.get_user_level(999) == 0
        assert rbac.users["999"]["name"] == "User999"

        # Welcome message sent
        first_call_text = mock_send.call_args_list[0][0][1]
        assert "Welcome" in first_call_text
        assert "pending" in first_call_text

    @patch("main.send_message")
    def test_new_user_alerts_superadmins(self, mock_send, rbac) -> None:
        from main import handle_start

        msg = _make_message(999, "/start")
        handle_start(rbac, msg, 999)

        # Should have sent: 1 welcome + 1 alert to SuperAdmin(100)
        assert mock_send.call_count == 2
        admin_call = mock_send.call_args_list[1]
        assert admin_call[0][0] == 100  # sent to admin
        assert "reply_markup" in admin_call[1]
        markup = admin_call[1]["reply_markup"]
        assert "inline_keyboard" in markup

    @patch("main.send_message")
    def test_returning_user_no_reregistration(self, mock_send, rbac) -> None:
        from main import handle_start

        msg = _make_message(400, "/start")
        handle_start(rbac, msg, 400)

        # Level should remain 10 (Member), not reset to 0
        assert rbac.get_user_level(400) == 10
        first_call_text = mock_send.call_args_list[0][0][1]
        assert "Welcome back" in first_call_text


# ── /help handler ────────────────────────────────────────────────────────────


class TestHandleHelp:
    """Validate /help displays permission-aware buttons."""

    @patch("main.send_message")
    def test_guest_sees_basic_commands(self, mock_send, rbac) -> None:
        from main import handle_help

        msg = _make_message(9999, "/help")
        handle_help(rbac, msg, 9999)  # Unknown user → Guest

        call_args = mock_send.call_args
        assert "reply_markup" in call_args[1]
        markup = call_args[1]["reply_markup"]
        # Guest should see /start, /help, /status, /stop, /exit but NOT /kick
        button_texts = [btn["text"] for row in markup["inline_keyboard"] for btn in row]
        assert any("/help" in t for t in button_texts)
        assert not any("/kick" in t for t in button_texts)

    @patch("main.send_message")
    def test_moderator_sees_kick(self, mock_send, rbac) -> None:
        from main import handle_help

        msg = _make_message(300, "/help")
        handle_help(rbac, msg, 300)

        call_args = mock_send.call_args
        markup = call_args[1]["reply_markup"]
        button_texts = [btn["text"] for row in markup["inline_keyboard"] for btn in row]
        assert any("/kick" in t for t in button_texts)


# ── /status handler ──────────────────────────────────────────────────────────


class TestHandleStatus:
    """Validate /status shows rank info."""

    @patch("main.send_message")
    def test_status_shows_role(self, mock_send, rbac) -> None:
        from main import handle_status

        msg = _make_message(300, "/status")
        handle_status(rbac, msg, 300)

        text = mock_send.call_args[0][1]
        assert "Moderator" in text
        assert "50" in text
        assert "kick_user" in text


# ── /stop and /exit ──────────────────────────────────────────────────────────


class TestHandleStop:
    """Validate /stop and /exit handlers."""

    @patch("main.send_message")
    def test_stop(self, mock_send) -> None:
        from main import handle_stop

        msg = _make_message(400, "/stop")
        handle_stop(msg, 400)
        text = mock_send.call_args[0][1]
        assert "Session ended" in text

    @patch("main.send_message")
    def test_exit(self, mock_send) -> None:
        from main import handle_stop

        msg = _make_message(400, "/exit")
        handle_stop(msg, 400)
        assert mock_send.called


# ── Callback query (admin approval) ─────────────────────────────────────────


class TestCallbackApproval:
    """Validate the admin approval flow via callback queries."""

    @patch("main.answer_callback_query")
    @patch("main.send_message")
    def test_approve_member(self, mock_send, mock_answer, rbac) -> None:
        from main import handle_callback_query

        # First register the target user
        rbac.set_user_level(999, 0, name="NewUser")

        cb = _make_callback_query(100, "approve_member:999")["callback_query"]
        handle_callback_query(rbac, cb)

        # User level should be updated to 10
        assert rbac.get_user_level(999) == 10
        mock_answer.assert_called_once()
        # Two send_message calls: one to admin, one to user
        assert mock_send.call_count == 2

    @patch("main.answer_callback_query")
    @patch("main.send_message")
    def test_promote_mod(self, mock_send, mock_answer, rbac) -> None:
        from main import handle_callback_query

        rbac.set_user_level(999, 0, name="NewUser")

        cb = _make_callback_query(100, "promote_mod:999")["callback_query"]
        handle_callback_query(rbac, cb)

        assert rbac.get_user_level(999) == 50
        mock_answer.assert_called_once()

    @patch("main.answer_callback_query")
    @patch("main.send_message")
    def test_reject(self, mock_send, mock_answer, rbac) -> None:
        from main import handle_callback_query

        rbac.set_user_level(999, 0, name="NewUser")

        cb = _make_callback_query(100, "reject:999")["callback_query"]
        handle_callback_query(rbac, cb)

        # Level unchanged (still Guest)
        assert rbac.get_user_level(999) == 0
        mock_answer.assert_called_once()
        assert mock_send.call_count == 2

    @patch("main.answer_callback_query")
    @patch("main.send_message")
    def test_non_admin_cannot_approve(self, mock_send, mock_answer, rbac) -> None:
        from main import handle_callback_query

        rbac.set_user_level(999, 0, name="NewUser")

        # User 400 is a Member (level 10) — no manage_users permission
        cb = _make_callback_query(400, "approve_member:999")["callback_query"]
        handle_callback_query(rbac, cb)

        # Level should still be 0
        assert rbac.get_user_level(999) == 0
        mock_answer.assert_called_once()
        answer_text = mock_answer.call_args[0][1]
        assert "permission" in answer_text.lower()


# ── process_update dispatch ──────────────────────────────────────────────────


class TestProcessUpdate:
    """Validate that process_update dispatches to the right handlers."""

    @patch("main.handle_start")
    def test_dispatches_start(self, mock_handler, rbac) -> None:
        from main import process_update

        update = _make_update(400, "/start")
        process_update(rbac, update)
        mock_handler.assert_called_once()

    @patch("main.handle_help")
    def test_dispatches_help(self, mock_handler, rbac) -> None:
        from main import process_update

        update = _make_update(400, "/help")
        process_update(rbac, update)
        mock_handler.assert_called_once()

    @patch("main.handle_status")
    def test_dispatches_status(self, mock_handler, rbac) -> None:
        from main import process_update

        update = _make_update(400, "/status")
        process_update(rbac, update)
        mock_handler.assert_called_once()

    @patch("main.handle_stop")
    def test_dispatches_stop(self, mock_handler, rbac) -> None:
        from main import process_update

        update = _make_update(400, "/stop")
        process_update(rbac, update)
        mock_handler.assert_called_once()

    @patch("main.handle_stop")
    def test_dispatches_exit(self, mock_handler, rbac) -> None:
        from main import process_update

        update = _make_update(400, "/exit")
        process_update(rbac, update)
        mock_handler.assert_called_once()

    @patch("main.handle_kick")
    def test_dispatches_kick(self, mock_handler, rbac) -> None:
        from main import process_update

        update = _make_update(400, "/kick 123")
        process_update(rbac, update)
        mock_handler.assert_called_once()

    @patch("main.handle_callback_query")
    def test_dispatches_callback_query(self, mock_handler, rbac) -> None:
        from main import process_update

        update = _make_callback_query(100, "approve_member:999")
        process_update(rbac, update)
        mock_handler.assert_called_once()
