"""Tests for Pydantic data models generated from swagger.yaml."""

import sys
import os
import pytest

# Ensure the project root is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import (
    Error,
    Update,
    WebhookInfo,
    User,
    Chat,
    Message,
    MessageId,
    MessageEntity,
    PhotoSize,
    Location,
    Poll,
    PollOption,
    ChatPermissions,
    BotCommand,
    ResponseParameters,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    UserProfilePhotos,
    File,
    Contact,
    Dice,
    Venue,
    CallbackQuery,
)
from pydantic import ValidationError


# ── Error ────────────────────────────────────────────────────────────────────


class TestErrorModel:
    """Validate the Error schema."""

    def test_required_fields(self) -> None:
        """ok, error_code, and description are required."""
        err = Error(ok=False, error_code=401, description="Unauthorized")
        assert err.ok is False
        assert err.error_code == 401
        assert err.description == "Unauthorized"

    def test_optional_parameters(self) -> None:
        """parameters field should default to None."""
        err = Error(ok=False, error_code=400, description="Bad Request")
        assert err.parameters is None

    def test_missing_required_raises(self) -> None:
        """Omitting a required field must raise ValidationError."""
        with pytest.raises(ValidationError):
            Error(ok=False, error_code=400)  # missing description


# ── User ─────────────────────────────────────────────────────────────────────


class TestUserModel:
    """Validate the User schema."""

    def test_minimal_user(self) -> None:
        u = User(id=42, is_bot=False, first_name="Ada")
        assert u.id == 42
        assert u.is_bot is False
        assert u.first_name == "Ada"
        assert u.last_name is None
        assert u.username is None

    def test_full_user(self) -> None:
        u = User(
            id=99,
            is_bot=True,
            first_name="Bot",
            last_name="User",
            username="testbot",
            language_code="en",
        )
        assert u.username == "testbot"
        assert u.language_code == "en"

    def test_64_bit_id(self) -> None:
        """Telegram IDs can be 64-bit integers."""
        big_id = 5_000_000_000
        u = User(id=big_id, is_bot=False, first_name="Big")
        assert u.id == big_id


# ── Update ───────────────────────────────────────────────────────────────────


class TestUpdateModel:
    """Validate the Update schema."""

    def test_minimal_update(self) -> None:
        up = Update(update_id=1)
        assert up.update_id == 1
        assert up.message is None

    def test_update_with_nested_message(self) -> None:
        """Update can contain a nested Message with a User."""
        data = {
            "update_id": 10,
            "message": {
                "message_id": 100,
                "date": 1609459200,
                "chat": {"id": -1001234, "type": "supergroup"},
                "from": {"id": 42, "is_bot": False, "first_name": "Ada"},
                "text": "hello",
            },
        }
        up = Update.model_validate(data)
        assert up.message is not None
        assert up.message.message_id == 100
        assert up.message.from_field is not None
        assert up.message.from_field.first_name == "Ada"


# ── Chat ─────────────────────────────────────────────────────────────────────


class TestChatModel:
    """Validate the Chat schema."""

    def test_private_chat(self) -> None:
        c = Chat(id=42, type="private")
        assert c.id == 42

    def test_negative_group_id(self) -> None:
        """Groups/channels use negative IDs."""
        c = Chat(id=-1001234567890, type="supergroup")
        assert c.id < 0


# ── WebhookInfo ──────────────────────────────────────────────────────────────


class TestWebhookInfoModel:
    def test_required_fields(self) -> None:
        wh = WebhookInfo(url="https://example.com", has_custom_certificate=False, pending_update_count=0)
        assert wh.url == "https://example.com"


# ── MessageEntity ────────────────────────────────────────────────────────────


class TestMessageEntityModel:
    def test_minimal(self) -> None:
        e = MessageEntity(type="bold", offset=0, length=5)
        assert e.type == "bold"


# ── PhotoSize ────────────────────────────────────────────────────────────────


class TestPhotoSizeModel:
    def test_required(self) -> None:
        p = PhotoSize(file_id="abc", file_unique_id="xyz", width=100, height=200)
        assert p.width == 100


# ── BotCommand ───────────────────────────────────────────────────────────────


class TestBotCommandModel:
    def test_command(self) -> None:
        b = BotCommand(command="help", description="Show help")
        assert b.command == "help"


# ── InlineKeyboardMarkup ────────────────────────────────────────────────────


class TestInlineKeyboardMarkup:
    def test_nested_buttons(self) -> None:
        data = {
            "inline_keyboard": [
                [{"text": "Click", "callback_data": "action"}]
            ]
        }
        kb = InlineKeyboardMarkup.model_validate(data)
        assert len(kb.inline_keyboard) == 1
        assert kb.inline_keyboard[0][0].text == "Click"


# ── Serialization round-trip ─────────────────────────────────────────────────


class TestRoundTrip:
    """Ensure models can serialize to dict and back."""

    def test_user_round_trip(self) -> None:
        u = User(id=1, is_bot=False, first_name="Test")
        data = u.model_dump()
        u2 = User.model_validate(data)
        assert u == u2

    def test_error_round_trip(self) -> None:
        err = Error(ok=False, error_code=500, description="Internal")
        data = err.model_dump()
        err2 = Error.model_validate(data)
        assert err == err2

    def test_update_from_alias(self) -> None:
        """The 'from' field uses alias 'from_field' in Python."""
        data = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "date": 0,
                "chat": {"id": 1, "type": "private"},
                "from": {"id": 1, "is_bot": False, "first_name": "X"},
            },
        }
        up = Update.model_validate(data)
        assert up.message.from_field.id == 1
