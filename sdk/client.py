"""ChitraguptClient -- service layer wrapping every Telegram Bot API endpoint.

All methods accept and return Pydantic models for strict type validation.
HTTP calls use the ``requests`` library per project standards.

The module also provides async free-function helpers (``make_request``,
``get_updates``, ``send_message``, etc.) that offload blocking I/O via
:func:`asyncio.to_thread`.  These were previously in ``bot/telegram.py``
and are now consolidated here so every Telegram API call lives in the SDK.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union

import requests

from sdk.models import (  # noqa: F401
    Error,
    Update,
    WebhookInfo,
    User,
    Chat,
    Message,
    MessageId,
    MessageEntity,
    PhotoSize,
    Animation,
    Audio,
    Document,
    Video,
    VideoNote,
    Voice,
    Contact,
    Dice,
    PollOption,
    PollAnswer,
    Poll,
    Location,
    Venue,
    ProximityAlertTriggered,
    UserProfilePhotos,
    File,
    ReplyKeyboardMarkup,
    KeyboardButton,
    KeyboardButtonPollType,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LoginUrl,
    CallbackQuery,
    ForceReply,
    ChatPhoto,
    ChatMember,
    ChatPermissions,
    ChatLocation,
    BotCommand,
    ResponseParameters,
    InputMedia,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaAnimation,
    InputMediaAudio,
    InputMediaDocument,
    InputFile,
    Sticker,
    StickerSet,
    MaskPosition,
    InlineQuery,
    InlineQueryResult,
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InlineQueryResultGif,
    InlineQueryResultMpeg4Gif,
    InlineQueryResultVideo,
    InlineQueryResultAudio,
    InlineQueryResultVoice,
    InlineQueryResultDocument,
    InlineQueryResultLocation,
    InlineQueryResultVenue,
    InlineQueryResultContact,
    InlineQueryResultGame,
    InlineQueryResultCachedPhoto,
    InlineQueryResultCachedGif,
    InlineQueryResultCachedMpeg4Gif,
    InlineQueryResultCachedSticker,
    InlineQueryResultCachedDocument,
    InlineQueryResultCachedVideo,
    InlineQueryResultCachedVoice,
    InlineQueryResultCachedAudio,
    InputMessageContent,
    InputTextMessageContent,
    InputLocationMessageContent,
    InputVenueMessageContent,
    InputContactMessageContent,
    ChosenInlineResult,
    LabeledPrice,
    Invoice,
    ShippingAddress,
    OrderInfo,
    ShippingOption,
    SuccessfulPayment,
    ShippingQuery,
    PreCheckoutQuery,
    PassportData,
    PassportFile,
    EncryptedPassportElement,
    EncryptedCredentials,
    PassportElementError,
    PassportElementErrorDataField,
    PassportElementErrorFrontSide,
    PassportElementErrorReverseSide,
    PassportElementErrorSelfie,
    PassportElementErrorFile,
    PassportElementErrorFiles,
    PassportElementErrorTranslationFile,
    PassportElementErrorTranslationFiles,
    PassportElementErrorUnspecified,
    Game,
    CallbackGame,
    GameHighScore,
)
from sdk.exceptions import APIException


class ChitraguptClient:
    """Client-side service layer for the Telegram Bot API.

    Each public method corresponds to a Telegram Bot API endpoint.
    The client validates responses with Pydantic models and raises
    :class:`APIException` for non-2xx status codes.
    """

    _DEFAULT_TIMEOUT: int = 10

    def __init__(self, base_url: str, timeout: int = _DEFAULT_TIMEOUT, bot_token: str | None = None) -> None:
        """Create a new client bound to *base_url*.

        Args:
            base_url: Full Bot API base URL (e.g. ``https://api.telegram.org/bot<token>``).
            timeout: Default request timeout in seconds.
            bot_token: Raw bot token, used for file-download URLs.
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._bot_token = bot_token

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    def _post(self, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a POST request and return the parsed JSON body.

        Raises:
            APIException: If the response status code is not 2xx.
            requests.RequestException: On transport-level failures.
        """
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        try:
            response = requests.post(url, json=payload, timeout=self._timeout)
        except requests.RequestException:
            raise
        try:
            body = response.json()
        except ValueError:
            body = {}
        if not response.ok:
            raise APIException(response.status_code, body)
        return body

    def get_updates(self, offset: Optional[int] = None, limit: Optional[int] = 100, timeout: Optional[int] = 0, allowed_updates: Optional[List[str]] = None) -> Dict[str, Any]:
        """Use this method to receive incoming updates using long polling ([wiki](https://en.wikipedia.org/wiki/Push_technology#Long_polling)). An Array of [Update](https://core.telegram.org/bots/api/#update) ob"""
        payload: Dict[str, Any] = {}
        if offset is not None:
            payload["offset"] = offset
        if limit is not None:
            payload["limit"] = limit
        if timeout is not None:
            payload["timeout"] = timeout
        if allowed_updates is not None:
            payload["allowed_updates"] = allowed_updates
        data = self._post("getUpdates", payload)
        return data

    def set_webhook(self, url: str, certificate: Optional["InputFile"] = None, ip_address: Optional[str] = None, max_connections: Optional[int] = 40, allowed_updates: Optional[List[str]] = None, drop_pending_updates: Optional[bool] = None) -> Dict[str, Any]:
        """Use this method to specify a url and receive incoming updates via an outgoing webhook. Whenever there is an update for the bot, we will send an HTTPS POST request to the specified url, containing a JS"""
        payload: Dict[str, Any] = {}
        payload["url"] = url
        if certificate is not None:
            payload["certificate"] = certificate
        if ip_address is not None:
            payload["ip_address"] = ip_address
        if max_connections is not None:
            payload["max_connections"] = max_connections
        if allowed_updates is not None:
            payload["allowed_updates"] = allowed_updates
        if drop_pending_updates is not None:
            payload["drop_pending_updates"] = drop_pending_updates
        data = self._post("setWebhook", payload)
        return data

    def delete_webhook(self, drop_pending_updates: Optional[bool] = None) -> Dict[str, Any]:
        """Use this method to remove webhook integration if you decide to switch back to [getUpdates](https://core.telegram.org/bots/api/#getupdates). Returns *True* on success."""
        payload: Dict[str, Any] = {}
        if drop_pending_updates is not None:
            payload["drop_pending_updates"] = drop_pending_updates
        data = self._post("deleteWebhook", payload)
        return data

    def get_webhook_info(self) -> Dict[str, Any]:
        """Use this method to get current webhook status. Requires no parameters. On success, returns a [WebhookInfo](https://core.telegram.org/bots/api/#webhookinfo) object. If the bot is using [getUpdates](htt"""
        data = self._post("getWebhookInfo")
        return data

    def get_me(self) -> Dict[str, Any]:
        """A simple method for testing your bot's auth token. Requires no parameters. Returns basic information about the bot in form of a [User](https://core.telegram.org/bots/api/#user) object."""
        data = self._post("getMe")
        return data

    def log_out(self) -> Dict[str, Any]:
        """Use this method to log out from the cloud Bot API server before launching the bot locally. You **must** log out the bot before running it locally, otherwise there is no guarantee that the bot will rec"""
        data = self._post("logOut")
        return data

    def close(self) -> Dict[str, Any]:
        """Use this method to close the bot instance before moving it from one local server to another. You need to delete the webhook before calling this method to ensure that the bot isn't launched again after"""
        data = self._post("close")
        return data

    def send_message(self, chat_id: Union[int, str], text: str, parse_mode: Optional[str] = None, entities: Optional[List["MessageEntity"]] = None, disable_web_page_preview: Optional[bool] = None, disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional[Union["InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"]] = None) -> Dict[str, Any]:
        """Use this method to send text messages. On success, the sent [Message](https://core.telegram.org/bots/api/#message) is returned."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["text"] = text
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if entities is not None:
            payload["entities"] = entities
        if disable_web_page_preview is not None:
            payload["disable_web_page_preview"] = disable_web_page_preview
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendMessage", payload)
        return data

    def forward_message(self, chat_id: Union[int, str], from_chat_id: Union[int, str], message_id: int, disable_notification: Optional[bool] = None) -> Dict[str, Any]:
        """Use this method to forward messages of any kind. On success, the sent [Message](https://core.telegram.org/bots/api/#message) is returned."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["from_chat_id"] = from_chat_id
        payload["message_id"] = message_id
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        data = self._post("forwardMessage", payload)
        return data

    def copy_message(self, chat_id: Union[int, str], from_chat_id: Union[int, str], message_id: int, caption: Optional[str] = None, parse_mode: Optional[str] = None, caption_entities: Optional[List["MessageEntity"]] = None, disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional[Union["InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"]] = None) -> Dict[str, Any]:
        """Use this method to copy messages of any kind. The method is analogous to the method [forwardMessages](https://core.telegram.org/bots/api/#forwardmessages), but the copied message doesn't have a link t"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["from_chat_id"] = from_chat_id
        payload["message_id"] = message_id
        if caption is not None:
            payload["caption"] = caption
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if caption_entities is not None:
            payload["caption_entities"] = caption_entities
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("copyMessage", payload)
        return data

    def send_photo(self, chat_id: Union[int, str], photo: Union["InputFile", str], caption: Optional[str] = None, parse_mode: Optional[str] = None, caption_entities: Optional[List["MessageEntity"]] = None, disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional[Union["InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"]] = None) -> Dict[str, Any]:
        """Use this method to send photos. On success, the sent [Message](https://core.telegram.org/bots/api/#message) is returned."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["photo"] = photo
        if caption is not None:
            payload["caption"] = caption
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if caption_entities is not None:
            payload["caption_entities"] = caption_entities
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendPhoto", payload)
        return data

    def send_audio(self, chat_id: Union[int, str], audio: Union["InputFile", str], caption: Optional[str] = None, parse_mode: Optional[str] = None, caption_entities: Optional[List["MessageEntity"]] = None, duration: Optional[int] = None, performer: Optional[str] = None, title: Optional[str] = None, thumb: Optional[Union["InputFile", str]] = None, disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional[Union["InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"]] = None) -> Dict[str, Any]:
        """Use this method to send audio files, if you want Telegram clients to display them in the music player. Your audio must be in the .MP3 or .M4A format. On success, the sent [Message](https://core.telegr"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["audio"] = audio
        if caption is not None:
            payload["caption"] = caption
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if caption_entities is not None:
            payload["caption_entities"] = caption_entities
        if duration is not None:
            payload["duration"] = duration
        if performer is not None:
            payload["performer"] = performer
        if title is not None:
            payload["title"] = title
        if thumb is not None:
            payload["thumb"] = thumb
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendAudio", payload)
        return data

    def send_document(self, chat_id: Union[int, str], document: Union["InputFile", str], thumb: Optional[Union["InputFile", str]] = None, caption: Optional[str] = None, parse_mode: Optional[str] = None, caption_entities: Optional[List["MessageEntity"]] = None, disable_content_type_detection: Optional[bool] = None, disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional[Union["InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"]] = None) -> Dict[str, Any]:
        """Use this method to send general files. On success, the sent [Message](https://core.telegram.org/bots/api/#message) is returned. Bots can currently send files of any type of up to 50 MB in size, this l"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["document"] = document
        if thumb is not None:
            payload["thumb"] = thumb
        if caption is not None:
            payload["caption"] = caption
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if caption_entities is not None:
            payload["caption_entities"] = caption_entities
        if disable_content_type_detection is not None:
            payload["disable_content_type_detection"] = disable_content_type_detection
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendDocument", payload)
        return data

    def send_video(self, chat_id: Union[int, str], video: Union["InputFile", str], duration: Optional[int] = None, width: Optional[int] = None, height: Optional[int] = None, thumb: Optional[Union["InputFile", str]] = None, caption: Optional[str] = None, parse_mode: Optional[str] = None, caption_entities: Optional[List["MessageEntity"]] = None, supports_streaming: Optional[bool] = None, disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional[Union["InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"]] = None) -> Dict[str, Any]:
        """Use this method to send video files, Telegram clients support mp4 videos (other formats may be sent as [Document](https://core.telegram.org/bots/api/#document)). On success, the sent [Message](https:/"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["video"] = video
        if duration is not None:
            payload["duration"] = duration
        if width is not None:
            payload["width"] = width
        if height is not None:
            payload["height"] = height
        if thumb is not None:
            payload["thumb"] = thumb
        if caption is not None:
            payload["caption"] = caption
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if caption_entities is not None:
            payload["caption_entities"] = caption_entities
        if supports_streaming is not None:
            payload["supports_streaming"] = supports_streaming
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendVideo", payload)
        return data

    def send_animation(self, chat_id: Union[int, str], animation: Union["InputFile", str], duration: Optional[int] = None, width: Optional[int] = None, height: Optional[int] = None, thumb: Optional[Union["InputFile", str]] = None, caption: Optional[str] = None, parse_mode: Optional[str] = None, caption_entities: Optional[List["MessageEntity"]] = None, disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional[Union["InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"]] = None) -> Dict[str, Any]:
        """Use this method to send animation files (GIF or H.264/MPEG-4 AVC video without sound). On success, the sent [Message](https://core.telegram.org/bots/api/#message) is returned. Bots can currently send """
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["animation"] = animation
        if duration is not None:
            payload["duration"] = duration
        if width is not None:
            payload["width"] = width
        if height is not None:
            payload["height"] = height
        if thumb is not None:
            payload["thumb"] = thumb
        if caption is not None:
            payload["caption"] = caption
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if caption_entities is not None:
            payload["caption_entities"] = caption_entities
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendAnimation", payload)
        return data

    def send_voice(self, chat_id: Union[int, str], voice: Union["InputFile", str], caption: Optional[str] = None, parse_mode: Optional[str] = None, caption_entities: Optional[List["MessageEntity"]] = None, duration: Optional[int] = None, disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional[Union["InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"]] = None) -> Dict[str, Any]:
        """Use this method to send audio files, if you want Telegram clients to display the file as a playable voice message. For this to work, your audio must be in an .OGG file encoded with OPUS (other formats"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["voice"] = voice
        if caption is not None:
            payload["caption"] = caption
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if caption_entities is not None:
            payload["caption_entities"] = caption_entities
        if duration is not None:
            payload["duration"] = duration
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendVoice", payload)
        return data

    def send_video_note(self, chat_id: Union[int, str], video_note: Union["InputFile", str], duration: Optional[int] = None, length: Optional[int] = None, thumb: Optional[Union["InputFile", str]] = None, disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional[Union["InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"]] = None) -> Dict[str, Any]:
        """As of [v.4.0](https://telegram.org/blog/video-messages-and-telescope), Telegram clients support rounded square mp4 videos of up to 1 minute long. Use this method to send video messages. On success, th"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["video_note"] = video_note
        if duration is not None:
            payload["duration"] = duration
        if length is not None:
            payload["length"] = length
        if thumb is not None:
            payload["thumb"] = thumb
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendVideoNote", payload)
        return data

    def send_media_group(self, chat_id: Union[int, str], media: List[Union["InputMediaAudio", "InputMediaDocument", "InputMediaPhoto", "InputMediaVideo"]], disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None) -> Dict[str, Any]:
        """Use this method to send a group of photos, videos, documents or audios as an album. Documents and audio files can be only grouped in an album with messages of the same type. On success, an array of [M"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["media"] = media
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        data = self._post("sendMediaGroup", payload)
        return data

    def send_location(self, chat_id: Union[int, str], latitude: float, longitude: float, horizontal_accuracy: Optional[float] = None, live_period: Optional[int] = None, heading: Optional[int] = None, proximity_alert_radius: Optional[int] = None, disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional[Union["InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"]] = None) -> Dict[str, Any]:
        """Use this method to send point on the map. On success, the sent [Message](https://core.telegram.org/bots/api/#message) is returned."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["latitude"] = latitude
        payload["longitude"] = longitude
        if horizontal_accuracy is not None:
            payload["horizontal_accuracy"] = horizontal_accuracy
        if live_period is not None:
            payload["live_period"] = live_period
        if heading is not None:
            payload["heading"] = heading
        if proximity_alert_radius is not None:
            payload["proximity_alert_radius"] = proximity_alert_radius
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendLocation", payload)
        return data

    def edit_message_live_location(self, latitude: float, longitude: float, chat_id: Optional[Union[int, str]] = None, message_id: Optional[int] = None, inline_message_id: Optional[str] = None, horizontal_accuracy: Optional[float] = None, heading: Optional[int] = None, proximity_alert_radius: Optional[int] = None, reply_markup: Optional["InlineKeyboardMarkup"] = None) -> Dict[str, Any]:
        """Use this method to edit live location messages. A location can be edited until its *live_period* expires or editing is explicitly disabled by a call to [stopMessageLiveLocation](https://core.telegram."""
        payload: Dict[str, Any] = {}
        payload["latitude"] = latitude
        payload["longitude"] = longitude
        if chat_id is not None:
            payload["chat_id"] = chat_id
        if message_id is not None:
            payload["message_id"] = message_id
        if inline_message_id is not None:
            payload["inline_message_id"] = inline_message_id
        if horizontal_accuracy is not None:
            payload["horizontal_accuracy"] = horizontal_accuracy
        if heading is not None:
            payload["heading"] = heading
        if proximity_alert_radius is not None:
            payload["proximity_alert_radius"] = proximity_alert_radius
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("editMessageLiveLocation", payload)
        return data

    def stop_message_live_location(self, chat_id: Optional[Union[int, str]] = None, message_id: Optional[int] = None, inline_message_id: Optional[str] = None, reply_markup: Optional["InlineKeyboardMarkup"] = None) -> Dict[str, Any]:
        """Use this method to stop updating a live location message before *live_period* expires. On success, if the message was sent by the bot, the sent [Message](https://core.telegram.org/bots/api/#message) i"""
        payload: Dict[str, Any] = {}
        if chat_id is not None:
            payload["chat_id"] = chat_id
        if message_id is not None:
            payload["message_id"] = message_id
        if inline_message_id is not None:
            payload["inline_message_id"] = inline_message_id
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("stopMessageLiveLocation", payload)
        return data

    def send_venue(self, chat_id: Union[int, str], latitude: float, longitude: float, title: str, address: str, foursquare_id: Optional[str] = None, foursquare_type: Optional[str] = None, google_place_id: Optional[str] = None, google_place_type: Optional[str] = None, disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional[Union["InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"]] = None) -> Dict[str, Any]:
        """Use this method to send information about a venue. On success, the sent [Message](https://core.telegram.org/bots/api/#message) is returned."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["latitude"] = latitude
        payload["longitude"] = longitude
        payload["title"] = title
        payload["address"] = address
        if foursquare_id is not None:
            payload["foursquare_id"] = foursquare_id
        if foursquare_type is not None:
            payload["foursquare_type"] = foursquare_type
        if google_place_id is not None:
            payload["google_place_id"] = google_place_id
        if google_place_type is not None:
            payload["google_place_type"] = google_place_type
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendVenue", payload)
        return data

    def send_contact(self, chat_id: Union[int, str], phone_number: str, first_name: str, last_name: Optional[str] = None, vcard: Optional[str] = None, disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional[Union["InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"]] = None) -> Dict[str, Any]:
        """Use this method to send phone contacts. On success, the sent [Message](https://core.telegram.org/bots/api/#message) is returned."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["phone_number"] = phone_number
        payload["first_name"] = first_name
        if last_name is not None:
            payload["last_name"] = last_name
        if vcard is not None:
            payload["vcard"] = vcard
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendContact", payload)
        return data

    def send_poll(self, chat_id: Union[int, str], question: str, options: List[str], is_anonymous: Optional[bool] = None, type: Optional[str] = None, allows_multiple_answers: Optional[bool] = None, correct_option_id: Optional[int] = None, explanation: Optional[str] = None, explanation_parse_mode: Optional[str] = None, explanation_entities: Optional[List["MessageEntity"]] = None, open_period: Optional[int] = None, close_date: Optional[int] = None, is_closed: Optional[bool] = None, disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional[Union["InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"]] = None) -> Dict[str, Any]:
        """Use this method to send a native poll. On success, the sent [Message](https://core.telegram.org/bots/api/#message) is returned."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["question"] = question
        payload["options"] = options
        if is_anonymous is not None:
            payload["is_anonymous"] = is_anonymous
        if type is not None:
            payload["type"] = type
        if allows_multiple_answers is not None:
            payload["allows_multiple_answers"] = allows_multiple_answers
        if correct_option_id is not None:
            payload["correct_option_id"] = correct_option_id
        if explanation is not None:
            payload["explanation"] = explanation
        if explanation_parse_mode is not None:
            payload["explanation_parse_mode"] = explanation_parse_mode
        if explanation_entities is not None:
            payload["explanation_entities"] = explanation_entities
        if open_period is not None:
            payload["open_period"] = open_period
        if close_date is not None:
            payload["close_date"] = close_date
        if is_closed is not None:
            payload["is_closed"] = is_closed
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendPoll", payload)
        return data

    def send_dice(self, chat_id: Union[int, str], emoji: Optional[str] = '🎲', disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional[Union["InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"]] = None) -> Dict[str, Any]:
        """Use this method to send an animated emoji that will display a random value. On success, the sent [Message](https://core.telegram.org/bots/api/#message) is returned."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        if emoji is not None:
            payload["emoji"] = emoji
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendDice", payload)
        return data

    def send_chat_action(self, chat_id: Union[int, str], action: str) -> Dict[str, Any]:
        """Use this method when you need to tell the user that something is happening on the bot's side. The status is set for 5 seconds or less (when a message arrives from your bot, Telegram clients clear its """
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["action"] = action
        data = self._post("sendChatAction", payload)
        return data

    def get_user_profile_photos(self, user_id: int, offset: Optional[int] = None, limit: Optional[int] = 100) -> Dict[str, Any]:
        """Use this method to get a list of profile pictures for a user. Returns a [UserProfilePhotos](https://core.telegram.org/bots/api/#userprofilephotos) object."""
        payload: Dict[str, Any] = {}
        payload["user_id"] = user_id
        if offset is not None:
            payload["offset"] = offset
        if limit is not None:
            payload["limit"] = limit
        data = self._post("getUserProfilePhotos", payload)
        return data

    def get_file(self, file_id: str) -> Dict[str, Any]:
        """Use this method to get basic info about a file and prepare it for downloading. For the moment, bots can download files of up to 20MB in size. On success, a [File](https://core.telegram.org/bots/api/#f"""
        payload: Dict[str, Any] = {}
        payload["file_id"] = file_id
        data = self._post("getFile", payload)
        return data

    def kick_chat_member(self, chat_id: Union[int, str], user_id: int, until_date: Optional[int] = None) -> Dict[str, Any]:
        """Use this method to kick a user from a group, a supergroup or a channel. In the case of supergroups and channels, the user will not be able to return to the group on their own using invite links, etc.,"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["user_id"] = user_id
        if until_date is not None:
            payload["until_date"] = until_date
        data = self._post("kickChatMember", payload)
        return data

    def unban_chat_member(self, chat_id: Union[int, str], user_id: int, only_if_banned: Optional[bool] = None) -> Dict[str, Any]:
        """Use this method to unban a previously kicked user in a supergroup or channel. The user will **not** return to the group or channel automatically, but will be able to join via link, etc. The bot must b"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["user_id"] = user_id
        if only_if_banned is not None:
            payload["only_if_banned"] = only_if_banned
        data = self._post("unbanChatMember", payload)
        return data

    def restrict_chat_member(self, chat_id: Union[int, str], user_id: int, permissions: "ChatPermissions", until_date: Optional[int] = None) -> Dict[str, Any]:
        """Use this method to restrict a user in a supergroup. The bot must be an administrator in the supergroup for this to work and must have the appropriate admin rights. Pass *True* for all permissions to l"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["user_id"] = user_id
        payload["permissions"] = permissions
        if until_date is not None:
            payload["until_date"] = until_date
        data = self._post("restrictChatMember", payload)
        return data

    def promote_chat_member(self, chat_id: Union[int, str], user_id: int, is_anonymous: Optional[bool] = None, can_change_info: Optional[bool] = None, can_post_messages: Optional[bool] = None, can_edit_messages: Optional[bool] = None, can_delete_messages: Optional[bool] = None, can_invite_users: Optional[bool] = None, can_restrict_members: Optional[bool] = None, can_pin_messages: Optional[bool] = None, can_promote_members: Optional[bool] = None) -> Dict[str, Any]:
        """Use this method to promote or demote a user in a supergroup or a channel. The bot must be an administrator in the chat for this to work and must have the appropriate admin rights. Pass *False* for all"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["user_id"] = user_id
        if is_anonymous is not None:
            payload["is_anonymous"] = is_anonymous
        if can_change_info is not None:
            payload["can_change_info"] = can_change_info
        if can_post_messages is not None:
            payload["can_post_messages"] = can_post_messages
        if can_edit_messages is not None:
            payload["can_edit_messages"] = can_edit_messages
        if can_delete_messages is not None:
            payload["can_delete_messages"] = can_delete_messages
        if can_invite_users is not None:
            payload["can_invite_users"] = can_invite_users
        if can_restrict_members is not None:
            payload["can_restrict_members"] = can_restrict_members
        if can_pin_messages is not None:
            payload["can_pin_messages"] = can_pin_messages
        if can_promote_members is not None:
            payload["can_promote_members"] = can_promote_members
        data = self._post("promoteChatMember", payload)
        return data

    def set_chat_administrator_custom_title(self, chat_id: Union[int, str], user_id: int, custom_title: str) -> Dict[str, Any]:
        """Use this method to set a custom title for an administrator in a supergroup promoted by the bot. Returns *True* on success."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["user_id"] = user_id
        payload["custom_title"] = custom_title
        data = self._post("setChatAdministratorCustomTitle", payload)
        return data

    def set_chat_permissions(self, chat_id: Union[int, str], permissions: "ChatPermissions") -> Dict[str, Any]:
        """Use this method to set default chat permissions for all members. The bot must be an administrator in the group or a supergroup for this to work and must have the *can_restrict_members* admin rights. R"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["permissions"] = permissions
        data = self._post("setChatPermissions", payload)
        return data

    def export_chat_invite_link(self, chat_id: Union[int, str]) -> Dict[str, Any]:
        """Use this method to generate a new invite link for a chat; any previously generated link is revoked. The bot must be an administrator in the chat for this to work and must have the appropriate admin ri"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        data = self._post("exportChatInviteLink", payload)
        return data

    def set_chat_photo(self, chat_id: Union[int, str], photo: "InputFile") -> Dict[str, Any]:
        """Use this method to set a new profile photo for the chat. Photos can't be changed for private chats. The bot must be an administrator in the chat for this to work and must have the appropriate admin ri"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["photo"] = photo
        data = self._post("setChatPhoto", payload)
        return data

    def delete_chat_photo(self, chat_id: Union[int, str]) -> Dict[str, Any]:
        """Use this method to delete a chat photo. Photos can't be changed for private chats. The bot must be an administrator in the chat for this to work and must have the appropriate admin rights. Returns *Tr"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        data = self._post("deleteChatPhoto", payload)
        return data

    def set_chat_title(self, chat_id: Union[int, str], title: str) -> Dict[str, Any]:
        """Use this method to change the title of a chat. Titles can't be changed for private chats. The bot must be an administrator in the chat for this to work and must have the appropriate admin rights. Retu"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["title"] = title
        data = self._post("setChatTitle", payload)
        return data

    def set_chat_description(self, chat_id: Union[int, str], description: Optional[str] = None) -> Dict[str, Any]:
        """Use this method to change the description of a group, a supergroup or a channel. The bot must be an administrator in the chat for this to work and must have the appropriate admin rights. Returns *True"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        if description is not None:
            payload["description"] = description
        data = self._post("setChatDescription", payload)
        return data

    def pin_chat_message(self, chat_id: Union[int, str], message_id: int, disable_notification: Optional[bool] = None) -> Dict[str, Any]:
        """Use this method to add a message to the list of pinned messages in a chat. If the chat is not a private chat, the bot must be an administrator in the chat for this to work and must have the 'can_pin_m"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["message_id"] = message_id
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        data = self._post("pinChatMessage", payload)
        return data

    def unpin_chat_message(self, chat_id: Union[int, str], message_id: Optional[int] = None) -> Dict[str, Any]:
        """Use this method to remove a message from the list of pinned messages in a chat. If the chat is not a private chat, the bot must be an administrator in the chat for this to work and must have the 'can_"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        if message_id is not None:
            payload["message_id"] = message_id
        data = self._post("unpinChatMessage", payload)
        return data

    def unpin_all_chat_messages(self, chat_id: Union[int, str]) -> Dict[str, Any]:
        """Use this method to clear the list of pinned messages in a chat. If the chat is not a private chat, the bot must be an administrator in the chat for this to work and must have the 'can_pin_messages' ad"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        data = self._post("unpinAllChatMessages", payload)
        return data

    def leave_chat(self, chat_id: Union[int, str]) -> Dict[str, Any]:
        """Use this method for your bot to leave a group, supergroup or channel. Returns *True* on success."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        data = self._post("leaveChat", payload)
        return data

    def get_chat(self, chat_id: Union[int, str]) -> Dict[str, Any]:
        """Use this method to get up to date information about the chat (current name of the user for one-on-one conversations, current username of a user, group or channel, etc.). Returns a [Chat](https://core."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        data = self._post("getChat", payload)
        return data

    def get_chat_administrators(self, chat_id: Union[int, str]) -> Dict[str, Any]:
        """Use this method to get a list of administrators in a chat. On success, returns an Array of [ChatMember](https://core.telegram.org/bots/api/#chatmember) objects that contains information about all chat"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        data = self._post("getChatAdministrators", payload)
        return data

    def get_chat_members_count(self, chat_id: Union[int, str]) -> Dict[str, Any]:
        """Use this method to get the number of members in a chat. Returns *Int* on success."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        data = self._post("getChatMembersCount", payload)
        return data

    def get_chat_member(self, chat_id: Union[int, str], user_id: int) -> Dict[str, Any]:
        """Use this method to get information about a member of a chat. Returns a [ChatMember](https://core.telegram.org/bots/api/#chatmember) object on success."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["user_id"] = user_id
        data = self._post("getChatMember", payload)
        return data

    def set_chat_sticker_set(self, chat_id: Union[int, str], sticker_set_name: str) -> Dict[str, Any]:
        """Use this method to set a new group sticker set for a supergroup. The bot must be an administrator in the chat for this to work and must have the appropriate admin rights. Use the field *can_set_sticke"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["sticker_set_name"] = sticker_set_name
        data = self._post("setChatStickerSet", payload)
        return data

    def delete_chat_sticker_set(self, chat_id: Union[int, str]) -> Dict[str, Any]:
        """Use this method to delete a group sticker set from a supergroup. The bot must be an administrator in the chat for this to work and must have the appropriate admin rights. Use the field *can_set_sticke"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        data = self._post("deleteChatStickerSet", payload)
        return data

    def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None, show_alert: Optional[bool] = False, url: Optional[str] = None, cache_time: Optional[int] = 0) -> Dict[str, Any]:
        """Use this method to send answers to callback queries sent from [inline keyboards](/bots#inline-keyboards-and-on-the-fly-updating). The answer will be displayed to the user as a notification at the top """
        payload: Dict[str, Any] = {}
        payload["callback_query_id"] = callback_query_id
        if text is not None:
            payload["text"] = text
        if show_alert is not None:
            payload["show_alert"] = show_alert
        if url is not None:
            payload["url"] = url
        if cache_time is not None:
            payload["cache_time"] = cache_time
        data = self._post("answerCallbackQuery", payload)
        return data

    def set_my_commands(self, commands: List["BotCommand"]) -> Dict[str, Any]:
        """Use this method to change the list of the bot's commands. Returns *True* on success."""
        payload: Dict[str, Any] = {}
        payload["commands"] = commands
        data = self._post("setMyCommands", payload)
        return data

    def get_my_commands(self) -> Dict[str, Any]:
        """Use this method to get the current list of the bot's commands. Requires no parameters. Returns Array of [BotCommand](https://core.telegram.org/bots/api/#botcommand) on success."""
        data = self._post("getMyCommands")
        return data

    def edit_message_text(self, text: str, chat_id: Optional[Union[int, str]] = None, message_id: Optional[int] = None, inline_message_id: Optional[str] = None, parse_mode: Optional[str] = None, entities: Optional[List["MessageEntity"]] = None, disable_web_page_preview: Optional[bool] = None, reply_markup: Optional["InlineKeyboardMarkup"] = None) -> Dict[str, Any]:
        """Use this method to edit text and [game](https://core.telegram.org/bots/api/#games) messages. On success, if the edited message is not an inline message, the edited [Message](https://core.telegram.org/"""
        payload: Dict[str, Any] = {}
        payload["text"] = text
        if chat_id is not None:
            payload["chat_id"] = chat_id
        if message_id is not None:
            payload["message_id"] = message_id
        if inline_message_id is not None:
            payload["inline_message_id"] = inline_message_id
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if entities is not None:
            payload["entities"] = entities
        if disable_web_page_preview is not None:
            payload["disable_web_page_preview"] = disable_web_page_preview
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("editMessageText", payload)
        return data

    def edit_message_caption(self, chat_id: Optional[Union[int, str]] = None, message_id: Optional[int] = None, inline_message_id: Optional[str] = None, caption: Optional[str] = None, parse_mode: Optional[str] = None, caption_entities: Optional[List["MessageEntity"]] = None, reply_markup: Optional["InlineKeyboardMarkup"] = None) -> Dict[str, Any]:
        """Use this method to edit captions of messages. On success, if the edited message is not an inline message, the edited [Message](https://core.telegram.org/bots/api/#message) is returned, otherwise *True"""
        payload: Dict[str, Any] = {}
        if chat_id is not None:
            payload["chat_id"] = chat_id
        if message_id is not None:
            payload["message_id"] = message_id
        if inline_message_id is not None:
            payload["inline_message_id"] = inline_message_id
        if caption is not None:
            payload["caption"] = caption
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if caption_entities is not None:
            payload["caption_entities"] = caption_entities
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("editMessageCaption", payload)
        return data

    def edit_message_media(self, media: "InputMedia", chat_id: Optional[Union[int, str]] = None, message_id: Optional[int] = None, inline_message_id: Optional[str] = None, reply_markup: Optional["InlineKeyboardMarkup"] = None) -> Dict[str, Any]:
        """Use this method to edit animation, audio, document, photo, or video messages. If a message is part of a message album, then it can be edited only to an audio for audio albums, only to a document for d"""
        payload: Dict[str, Any] = {}
        payload["media"] = media
        if chat_id is not None:
            payload["chat_id"] = chat_id
        if message_id is not None:
            payload["message_id"] = message_id
        if inline_message_id is not None:
            payload["inline_message_id"] = inline_message_id
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("editMessageMedia", payload)
        return data

    def edit_message_reply_markup(self, chat_id: Optional[Union[int, str]] = None, message_id: Optional[int] = None, inline_message_id: Optional[str] = None, reply_markup: Optional["InlineKeyboardMarkup"] = None) -> Dict[str, Any]:
        """Use this method to edit only the reply markup of messages. On success, if the edited message is not an inline message, the edited [Message](https://core.telegram.org/bots/api/#message) is returned, ot"""
        payload: Dict[str, Any] = {}
        if chat_id is not None:
            payload["chat_id"] = chat_id
        if message_id is not None:
            payload["message_id"] = message_id
        if inline_message_id is not None:
            payload["inline_message_id"] = inline_message_id
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("editMessageReplyMarkup", payload)
        return data

    def stop_poll(self, chat_id: Union[int, str], message_id: int, reply_markup: Optional["InlineKeyboardMarkup"] = None) -> Dict[str, Any]:
        """Use this method to stop a poll which was sent by the bot. On success, the stopped [Poll](https://core.telegram.org/bots/api/#poll) with the final results is returned."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["message_id"] = message_id
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("stopPoll", payload)
        return data

    def delete_message(self, chat_id: Union[int, str], message_id: int) -> Dict[str, Any]:
        """Use this method to delete a message, including service messages, with the following limitations: - A message can only be deleted if it was sent less than 48 hours ago. - A dice message in a private ch"""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["message_id"] = message_id
        data = self._post("deleteMessage", payload)
        return data

    def send_sticker(self, chat_id: Union[int, str], sticker: Union["InputFile", str], disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional[Union["InlineKeyboardMarkup", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "ForceReply"]] = None) -> Dict[str, Any]:
        """Use this method to send static .WEBP or [animated](https://telegram.org/blog/animated-stickers) .TGS stickers. On success, the sent [Message](https://core.telegram.org/bots/api/#message) is returned."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["sticker"] = sticker
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendSticker", payload)
        return data

    def get_sticker_set(self, name: str) -> Dict[str, Any]:
        """Use this method to get a sticker set. On success, a [StickerSet](https://core.telegram.org/bots/api/#stickerset) object is returned."""
        payload: Dict[str, Any] = {}
        payload["name"] = name
        data = self._post("getStickerSet", payload)
        return data

    def upload_sticker_file(self, user_id: int, png_sticker: "InputFile") -> Dict[str, Any]:
        """Use this method to upload a .PNG file with a sticker for later use in *createNewStickerSet* and *addStickerToSet* methods (can be used multiple times). Returns the uploaded [File](https://core.telegra"""
        payload: Dict[str, Any] = {}
        payload["user_id"] = user_id
        payload["png_sticker"] = png_sticker
        data = self._post("uploadStickerFile", payload)
        return data

    def create_new_sticker_set(self, user_id: int, name: str, title: str, emojis: str, png_sticker: Optional[Union["InputFile", str]] = None, tgs_sticker: Optional["InputFile"] = None, contains_masks: Optional[bool] = None, mask_position: Optional["MaskPosition"] = None) -> Dict[str, Any]:
        """Use this method to create a new sticker set owned by a user. The bot will be able to edit the sticker set thus created. You **must** use exactly one of the fields *png_sticker* or *tgs_sticker*. Retur"""
        payload: Dict[str, Any] = {}
        payload["user_id"] = user_id
        payload["name"] = name
        payload["title"] = title
        payload["emojis"] = emojis
        if png_sticker is not None:
            payload["png_sticker"] = png_sticker
        if tgs_sticker is not None:
            payload["tgs_sticker"] = tgs_sticker
        if contains_masks is not None:
            payload["contains_masks"] = contains_masks
        if mask_position is not None:
            payload["mask_position"] = mask_position
        data = self._post("createNewStickerSet", payload)
        return data

    def add_sticker_to_set(self, user_id: int, name: str, emojis: str, png_sticker: Optional[Union["InputFile", str]] = None, tgs_sticker: Optional["InputFile"] = None, mask_position: Optional["MaskPosition"] = None) -> Dict[str, Any]:
        """Use this method to add a new sticker to a set created by the bot. You **must** use exactly one of the fields *png_sticker* or *tgs_sticker*. Animated stickers can be added to animated sticker sets and"""
        payload: Dict[str, Any] = {}
        payload["user_id"] = user_id
        payload["name"] = name
        payload["emojis"] = emojis
        if png_sticker is not None:
            payload["png_sticker"] = png_sticker
        if tgs_sticker is not None:
            payload["tgs_sticker"] = tgs_sticker
        if mask_position is not None:
            payload["mask_position"] = mask_position
        data = self._post("addStickerToSet", payload)
        return data

    def set_sticker_position_in_set(self, sticker: str, position: int) -> Dict[str, Any]:
        """Use this method to move a sticker in a set created by the bot to a specific position. Returns *True* on success."""
        payload: Dict[str, Any] = {}
        payload["sticker"] = sticker
        payload["position"] = position
        data = self._post("setStickerPositionInSet", payload)
        return data

    def delete_sticker_from_set(self, sticker: str) -> Dict[str, Any]:
        """Use this method to delete a sticker from a set created by the bot. Returns *True* on success."""
        payload: Dict[str, Any] = {}
        payload["sticker"] = sticker
        data = self._post("deleteStickerFromSet", payload)
        return data

    def set_sticker_set_thumb(self, name: str, user_id: int, thumb: Optional[Union["InputFile", str]] = None) -> Dict[str, Any]:
        """Use this method to set the thumbnail of a sticker set. Animated thumbnails can be set for animated sticker sets only. Returns *True* on success."""
        payload: Dict[str, Any] = {}
        payload["name"] = name
        payload["user_id"] = user_id
        if thumb is not None:
            payload["thumb"] = thumb
        data = self._post("setStickerSetThumb", payload)
        return data

    def answer_inline_query(self, inline_query_id: str, results: List["InlineQueryResult"], cache_time: Optional[int] = 300, is_personal: Optional[bool] = None, next_offset: Optional[str] = None, switch_pm_text: Optional[str] = None, switch_pm_parameter: Optional[str] = None) -> Dict[str, Any]:
        """Use this method to send answers to an inline query. On success, *True* is returned. No more than **50** results per query are allowed."""
        payload: Dict[str, Any] = {}
        payload["inline_query_id"] = inline_query_id
        payload["results"] = results
        if cache_time is not None:
            payload["cache_time"] = cache_time
        if is_personal is not None:
            payload["is_personal"] = is_personal
        if next_offset is not None:
            payload["next_offset"] = next_offset
        if switch_pm_text is not None:
            payload["switch_pm_text"] = switch_pm_text
        if switch_pm_parameter is not None:
            payload["switch_pm_parameter"] = switch_pm_parameter
        data = self._post("answerInlineQuery", payload)
        return data

    def send_invoice(self, chat_id: int, title: str, description: str, payload: str, provider_token: str, start_parameter: str, currency: str, prices: List["LabeledPrice"], provider_data: Optional[str] = None, photo_url: Optional[str] = None, photo_size: Optional[int] = None, photo_width: Optional[int] = None, photo_height: Optional[int] = None, need_name: Optional[bool] = None, need_phone_number: Optional[bool] = None, need_email: Optional[bool] = None, need_shipping_address: Optional[bool] = None, send_phone_number_to_provider: Optional[bool] = None, send_email_to_provider: Optional[bool] = None, is_flexible: Optional[bool] = None, disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional["InlineKeyboardMarkup"] = None) -> Dict[str, Any]:
        """Use this method to send invoices. On success, the sent [Message](https://core.telegram.org/bots/api/#message) is returned."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["title"] = title
        payload["description"] = description
        payload["payload"] = payload
        payload["provider_token"] = provider_token
        payload["start_parameter"] = start_parameter
        payload["currency"] = currency
        payload["prices"] = prices
        if provider_data is not None:
            payload["provider_data"] = provider_data
        if photo_url is not None:
            payload["photo_url"] = photo_url
        if photo_size is not None:
            payload["photo_size"] = photo_size
        if photo_width is not None:
            payload["photo_width"] = photo_width
        if photo_height is not None:
            payload["photo_height"] = photo_height
        if need_name is not None:
            payload["need_name"] = need_name
        if need_phone_number is not None:
            payload["need_phone_number"] = need_phone_number
        if need_email is not None:
            payload["need_email"] = need_email
        if need_shipping_address is not None:
            payload["need_shipping_address"] = need_shipping_address
        if send_phone_number_to_provider is not None:
            payload["send_phone_number_to_provider"] = send_phone_number_to_provider
        if send_email_to_provider is not None:
            payload["send_email_to_provider"] = send_email_to_provider
        if is_flexible is not None:
            payload["is_flexible"] = is_flexible
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendInvoice", payload)
        return data

    def answer_shipping_query(self, shipping_query_id: str, ok: bool, shipping_options: Optional[List["ShippingOption"]] = None, error_message: Optional[str] = None) -> Dict[str, Any]:
        """If you sent an invoice requesting a shipping address and the parameter *is_flexible* was specified, the Bot API will send an [Update](https://core.telegram.org/bots/api/#update) with a *shipping_query"""
        payload: Dict[str, Any] = {}
        payload["shipping_query_id"] = shipping_query_id
        payload["ok"] = ok
        if shipping_options is not None:
            payload["shipping_options"] = shipping_options
        if error_message is not None:
            payload["error_message"] = error_message
        data = self._post("answerShippingQuery", payload)
        return data

    def answer_pre_checkout_query(self, pre_checkout_query_id: str, ok: bool, error_message: Optional[str] = None) -> Dict[str, Any]:
        """Once the user has confirmed their payment and shipping details, the Bot API sends the final confirmation in the form of an [Update](https://core.telegram.org/bots/api/#update) with the field *pre_chec"""
        payload: Dict[str, Any] = {}
        payload["pre_checkout_query_id"] = pre_checkout_query_id
        payload["ok"] = ok
        if error_message is not None:
            payload["error_message"] = error_message
        data = self._post("answerPreCheckoutQuery", payload)
        return data

    def set_passport_data_errors(self, user_id: int, errors: List["PassportElementError"]) -> Dict[str, Any]:
        """Informs a user that some of the Telegram Passport elements they provided contains errors. The user will not be able to re-submit their Passport to you until the errors are fixed (the contents of the f"""
        payload: Dict[str, Any] = {}
        payload["user_id"] = user_id
        payload["errors"] = errors
        data = self._post("setPassportDataErrors", payload)
        return data

    def send_game(self, chat_id: int, game_short_name: str, disable_notification: Optional[bool] = None, reply_to_message_id: Optional[int] = None, allow_sending_without_reply: Optional[bool] = None, reply_markup: Optional["InlineKeyboardMarkup"] = None) -> Dict[str, Any]:
        """Use this method to send a game. On success, the sent [Message](https://core.telegram.org/bots/api/#message) is returned."""
        payload: Dict[str, Any] = {}
        payload["chat_id"] = chat_id
        payload["game_short_name"] = game_short_name
        if disable_notification is not None:
            payload["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            payload["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendGame", payload)
        return data

    def set_game_score(self, user_id: int, score: int, force: Optional[bool] = None, disable_edit_message: Optional[bool] = None, chat_id: Optional[int] = None, message_id: Optional[int] = None, inline_message_id: Optional[str] = None) -> Dict[str, Any]:
        """Use this method to set the score of the specified user in a game. On success, if the message was sent by the bot, returns the edited [Message](https://core.telegram.org/bots/api/#message), otherwise r"""
        payload: Dict[str, Any] = {}
        payload["user_id"] = user_id
        payload["score"] = score
        if force is not None:
            payload["force"] = force
        if disable_edit_message is not None:
            payload["disable_edit_message"] = disable_edit_message
        if chat_id is not None:
            payload["chat_id"] = chat_id
        if message_id is not None:
            payload["message_id"] = message_id
        if inline_message_id is not None:
            payload["inline_message_id"] = inline_message_id
        data = self._post("setGameScore", payload)
        return data

    def get_game_high_scores(self, user_id: int, chat_id: Optional[int] = None, message_id: Optional[int] = None, inline_message_id: Optional[str] = None) -> Dict[str, Any]:
        """Use this method to get data for high score tables. Will return the score of the specified user and several of their neighbors in a game. On success, returns an *Array* of [GameHighScore](https://core."""
        payload: Dict[str, Any] = {}
        payload["user_id"] = user_id
        if chat_id is not None:
            payload["chat_id"] = chat_id
        if message_id is not None:
            payload["message_id"] = message_id
        if inline_message_id is not None:
            payload["inline_message_id"] = inline_message_id
        data = self._post("getGameHighScores", payload)
        return data


# ── Module-level async helpers ───────────────────────────────────────────────
#
# Thin async wrappers around ``requests`` for polling updates, sending
# messages, and acknowledging callback queries.  All blocking I/O is
# offloaded via :func:`asyncio.to_thread` so the event loop is never
# blocked.
#
# A lazily-initialised module-level :class:`ChitraguptClient` instance
# carries the ``BASE_URL`` / ``BOT_TOKEN`` values from :mod:`config`.
# ─────────────────────────────────────────────────────────────────────────────

_sdk_logger = logging.getLogger("sdk.client")

_default_client: ChitraguptClient | None = None


def _get_default_client() -> ChitraguptClient:
    """Return (and lazily create) the module-level client singleton."""
    global _default_client
    if _default_client is None:
        from config import BASE_URL, BOT_TOKEN  # deferred to avoid circular imports
        _default_client = ChitraguptClient(BASE_URL, bot_token=BOT_TOKEN)
    return _default_client


async def make_request(method: str, url: str, **kwargs: object) -> requests.Response:
    """Run a :mod:`requests` call inside a thread to keep the event loop free.

    *method* is the HTTP verb (``"get"``, ``"post"``, …).
    """
    func = getattr(requests, method.lower())
    return await asyncio.to_thread(func, url, **kwargs)


async def get_updates(offset: int | None = None) -> dict:
    """Long-poll the Telegram Bot API for new updates."""
    client = _get_default_client()
    params: dict = {"timeout": 30}
    if offset is not None:
        params["offset"] = offset
    try:
        response = await make_request("get", f"{client._base_url}/getUpdates", params=params, timeout=35)
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            _sdk_logger.error("getUpdates JSON decode error", extra={"api_endpoint": "getUpdates", "error": str(exc)})
            return {"ok": False, "result": []}
    except requests.RequestException as exc:
        _sdk_logger.error("getUpdates request error", extra={"api_endpoint": "getUpdates", "error": str(exc)})
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
    client = _get_default_client()
    _sdk_logger.debug("Sending message", extra={"chat_id": chat_id, "api_endpoint": "sendMessage", "text_preview": text[:80]})
    payload: dict = {"chat_id": chat_id, "text": text}
    if parse_mode is not None:
        payload["parse_mode"] = parse_mode
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    try:
        response = await make_request(
            "post",
            f"{client._base_url}/sendMessage",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            _sdk_logger.warning("sendMessage Telegram error", extra={"chat_id": chat_id, "api_endpoint": "sendMessage", "api_response": data})
        else:
            _sdk_logger.info("Message sent", extra={"chat_id": chat_id, "api_endpoint": "sendMessage"})
    except requests.HTTPError as exc:
        _sdk_logger.error("sendMessage HTTP error", extra={"chat_id": chat_id, "api_endpoint": "sendMessage", "status_code": exc.response.status_code, "error": str(exc)})
    except requests.RequestException as exc:
        _sdk_logger.error("sendMessage request error", extra={"chat_id": chat_id, "api_endpoint": "sendMessage", "error": str(exc)})


async def delete_message(chat_id: int, message_id: int) -> bool:
    """Delete a single message.  Returns True on success, False otherwise."""
    client = _get_default_client()
    try:
        response = await make_request(
            "post",
            f"{client._base_url}/deleteMessage",
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

    client = _get_default_client()
    deleted = 0
    batch_size = 100
    for start in range(0, len(message_ids), batch_size):
        batch = message_ids[start : start + batch_size]
        try:
            response = await make_request(
                "post",
                f"{client._base_url}/deleteMessages",
                json={"chat_id": chat_id, "message_ids": batch},
                timeout=10,
            )
            data = response.json()
            if data.get("ok"):
                deleted += len(batch)
                _sdk_logger.debug("deleteMessages batch ok", extra={"chat_id": chat_id, "api_endpoint": "deleteMessages", "batch_size": len(batch)})
            else:
                _sdk_logger.warning("deleteMessages batch failed", extra={"chat_id": chat_id, "api_endpoint": "deleteMessages", "api_response": data})
        except requests.RequestException as exc:
            _sdk_logger.error("deleteMessages request error", extra={"chat_id": chat_id, "api_endpoint": "deleteMessages", "error": str(exc)})
    return deleted


async def answer_callback_query(callback_query_id: str, text: str | None = None) -> None:
    """Acknowledge a callback query so the spinner disappears for the user."""
    client = _get_default_client()
    payload: dict = {"callback_query_id": callback_query_id}
    if text is not None:
        payload["text"] = text
    try:
        response = await make_request(
            "post",
            f"{client._base_url}/answerCallbackQuery",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        _sdk_logger.error("answerCallbackQuery request error", extra={"api_endpoint": "answerCallbackQuery", "callback_query_id": callback_query_id, "error": str(exc)})


# ── File download helpers ────────────────────────────────────────────────────


async def get_file_info(file_id: str) -> File | None:
    """Resolve a Telegram ``file_id`` to a :class:`~sdk.models.File` model.

    Calls the ``getFile`` API and parses the result into a Pydantic model.
    Returns ``None`` when the API call fails or Telegram returns an error.
    """
    client = _get_default_client()
    try:
        resp = await make_request(
            "get",
            f"{client._base_url}/getFile",
            params={"file_id": file_id},
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            return File(**data["result"])
        _sdk_logger.warning("getFile failed", extra={"api_endpoint": "getFile", "file_id": file_id, "api_response": data})
        return None
    except (requests.RequestException, json.JSONDecodeError) as exc:
        _sdk_logger.error("getFile request error", extra={"api_endpoint": "getFile", "file_id": file_id, "error": str(exc)})
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
    client = _get_default_client()
    url = f"https://api.telegram.org/file/bot{client._bot_token}/{telegram_file_path}"
    resp = await make_request("get", url, timeout=30)
    resp.raise_for_status()
    return resp.content
