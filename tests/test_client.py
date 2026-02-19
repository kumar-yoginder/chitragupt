"""Tests for ChitraguptClient and APIException."""

import json
import sys
import os
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sdk.client import ChitraguptClient
from sdk.exceptions import APIException


# ── APIException ─────────────────────────────────────────────────────────────


class TestAPIException:
    """Validate the base exception class."""

    def test_attributes(self) -> None:
        exc = APIException(403, {"description": "Forbidden"})
        assert exc.status_code == 403
        assert exc.response_body == {"description": "Forbidden"}
        assert "403" in str(exc)
        assert "Forbidden" in str(exc)

    def test_default_body(self) -> None:
        exc = APIException(500)
        assert exc.response_body == {}
        assert "Unknown error" in str(exc)

    def test_is_exception(self) -> None:
        assert issubclass(APIException, Exception)


# ── ChitraguptClient construction ───────────────────────────────────────────


class TestClientInit:
    """Validate client initialisation."""

    def test_base_url_strip(self) -> None:
        c = ChitraguptClient("https://api.example.com/bot123/")
        assert c._base_url == "https://api.example.com/bot123"

    def test_default_timeout(self) -> None:
        c = ChitraguptClient("https://api.example.com")
        assert c._timeout == 10

    def test_custom_timeout(self) -> None:
        c = ChitraguptClient("https://api.example.com", timeout=30)
        assert c._timeout == 30


# ── _post helper ─────────────────────────────────────────────────────────────


class TestPostHelper:
    """Validate the internal _post method."""

    @patch("sdk.client.requests.post")
    def test_success(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"ok": True, "result": {}}
        mock_post.return_value = mock_resp

        c = ChitraguptClient("https://api.example.com")
        result = c._post("getMe")
        assert result == {"ok": True, "result": {}}
        mock_post.assert_called_once()

    @patch("sdk.client.requests.post")
    def test_api_error_raises(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"ok": False, "description": "Unauthorized"}
        mock_post.return_value = mock_resp

        c = ChitraguptClient("https://api.example.com")
        with pytest.raises(APIException) as exc_info:
            c._post("getMe")
        assert exc_info.value.status_code == 401

    @patch("sdk.client.requests.post")
    def test_json_decode_failure(self, mock_post: MagicMock) -> None:
        """If the response body is not JSON, body defaults to {}."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_post.return_value = mock_resp

        c = ChitraguptClient("https://api.example.com")
        # The response is 2xx but body is not JSON; we get empty dict
        result = c._post("getMe")
        assert result == {}

    @patch("sdk.client.requests.post")
    def test_network_error_propagates(self, mock_post: MagicMock) -> None:
        import requests as req_lib

        mock_post.side_effect = req_lib.ConnectionError("offline")

        c = ChitraguptClient("https://api.example.com")
        with pytest.raises(req_lib.ConnectionError):
            c._post("getMe")


# ── Endpoint methods ─────────────────────────────────────────────────────────


class TestEndpointMethods:
    """Spot-check selected endpoint wrapper methods."""

    @patch("sdk.client.requests.post")
    def test_get_me(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "ok": True,
            "result": {"id": 1, "is_bot": True, "first_name": "Bot"},
        }
        mock_post.return_value = mock_resp

        c = ChitraguptClient("https://api.example.com")
        result = c.get_me()
        assert result == {"ok": True, "result": {"id": 1, "is_bot": True, "first_name": "Bot"}}

    @patch("sdk.client.requests.post")
    def test_send_message(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"ok": True, "result": {"message_id": 1}}
        mock_post.return_value = mock_resp

        c = ChitraguptClient("https://api.example.com")
        result = c.send_message(chat_id=42, text="hello")
        assert result == {"ok": True, "result": {"message_id": 1}}

        # Verify the payload was correct
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["chat_id"] == 42
        assert payload["text"] == "hello"

    @patch("sdk.client.requests.post")
    def test_kick_chat_member(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"ok": True, "result": True}
        mock_post.return_value = mock_resp

        c = ChitraguptClient("https://api.example.com")
        result = c.kick_chat_member(chat_id=-1001234, user_id=42)
        assert result["ok"] is True

    @patch("sdk.client.requests.post")
    def test_get_updates_with_defaults(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"ok": True, "result": []}
        mock_post.return_value = mock_resp

        c = ChitraguptClient("https://api.example.com")
        result = c.get_updates()
        assert result["ok"] is True

    def test_all_74_methods_exist(self) -> None:
        """Every swagger endpoint should have a corresponding method."""
        c = ChitraguptClient("https://api.example.com")
        expected_methods = [
            "get_updates", "set_webhook", "delete_webhook", "get_webhook_info",
            "get_me", "log_out", "close", "send_message", "forward_message",
            "copy_message", "send_photo", "send_audio", "send_document",
            "send_video", "send_animation", "send_voice", "send_video_note",
            "send_media_group", "send_location", "edit_message_live_location",
            "stop_message_live_location", "send_venue", "send_contact",
            "send_poll", "send_dice", "send_chat_action",
            "get_user_profile_photos", "get_file", "kick_chat_member",
            "unban_chat_member", "restrict_chat_member", "promote_chat_member",
            "set_chat_administrator_custom_title", "set_chat_permissions",
            "export_chat_invite_link", "set_chat_photo", "delete_chat_photo",
            "set_chat_title", "set_chat_description", "pin_chat_message",
            "unpin_chat_message", "unpin_all_chat_messages", "leave_chat",
            "get_chat", "get_chat_administrators", "get_chat_members_count",
            "get_chat_member", "set_chat_sticker_set", "delete_chat_sticker_set",
            "answer_callback_query", "set_my_commands", "get_my_commands",
            "edit_message_text", "edit_message_caption", "edit_message_media",
            "edit_message_reply_markup", "stop_poll", "delete_message",
            "send_sticker", "get_sticker_set", "upload_sticker_file",
            "create_new_sticker_set", "add_sticker_to_set",
            "set_sticker_position_in_set", "delete_sticker_from_set",
            "set_sticker_set_thumb", "answer_inline_query", "send_invoice",
            "answer_shipping_query", "answer_pre_checkout_query",
            "set_passport_data_errors", "send_game", "set_game_score",
            "get_game_high_scores",
        ]
        for name in expected_methods:
            assert hasattr(c, name), f"Missing method: {name}"
