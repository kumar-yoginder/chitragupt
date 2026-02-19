"""Pydantic data models auto-generated from the Telegram Bot API swagger.yaml.

Every class corresponds to a schema defined in ``components/schemas``.
Use these models for strict request/response validation in the
ChitraguptClient service layer.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class Error(BaseModel):
    """Error model from Telegram Bot API."""

    ok: bool = False
    error_code: int
    description: str
    parameters: Optional["ResponseParameters"] = None

    model_config = {"populate_by_name": True}


class Update(BaseModel):
    """This [object](https://core.telegram.org/bots/api/#available-types) represents an incoming update. At most **one** of the optional parameters can be present in any given update."""

    update_id: int
    message: Optional["Message"] = None
    edited_message: Optional["Message"] = None
    channel_post: Optional["Message"] = None
    edited_channel_post: Optional["Message"] = None
    inline_query: Optional["InlineQuery"] = None
    chosen_inline_result: Optional["ChosenInlineResult"] = None
    callback_query: Optional["CallbackQuery"] = None
    shipping_query: Optional["ShippingQuery"] = None
    pre_checkout_query: Optional["PreCheckoutQuery"] = None
    poll: Optional["Poll"] = None
    poll_answer: Optional["PollAnswer"] = None

    model_config = {"populate_by_name": True}


class WebhookInfo(BaseModel):
    """Contains information about the current status of a webhook."""

    url: str
    has_custom_certificate: bool
    pending_update_count: int
    ip_address: Optional[str] = None
    last_error_date: Optional[int] = None
    last_error_message: Optional[str] = None
    max_connections: Optional[int] = None
    allowed_updates: Optional[List[str]] = None

    model_config = {"populate_by_name": True}


class User(BaseModel):
    """This object represents a Telegram user or bot."""

    id: int
    is_bot: bool
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    can_join_groups: Optional[bool] = None
    can_read_all_group_messages: Optional[bool] = None
    supports_inline_queries: Optional[bool] = None

    model_config = {"populate_by_name": True}


class Chat(BaseModel):
    """This object represents a chat."""

    id: int
    type: str
    title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    photo: Optional["ChatPhoto"] = None
    bio: Optional[str] = None
    description: Optional[str] = None
    invite_link: Optional[str] = None
    pinned_message: Optional["Message"] = None
    permissions: Optional["ChatPermissions"] = None
    slow_mode_delay: Optional[int] = None
    sticker_set_name: Optional[str] = None
    can_set_sticker_set: Optional[bool] = None
    linked_chat_id: Optional[int] = None
    location: Optional["ChatLocation"] = None

    model_config = {"populate_by_name": True}


class Message(BaseModel):
    """This object represents a message."""

    message_id: int
    date: int
    chat: "Chat"
    from_field: Optional["User"] = Field(None, alias="from")
    sender_chat: Optional["Chat"] = None
    forward_from: Optional["User"] = None
    forward_from_chat: Optional["Chat"] = None
    forward_from_message_id: Optional[int] = None
    forward_signature: Optional[str] = None
    forward_sender_name: Optional[str] = None
    forward_date: Optional[int] = None
    reply_to_message: Optional["Message"] = None
    via_bot: Optional["User"] = None
    edit_date: Optional[int] = None
    media_group_id: Optional[str] = None
    author_signature: Optional[str] = None
    text: Optional[str] = None
    entities: Optional[List["MessageEntity"]] = None
    animation: Optional["Animation"] = None
    audio: Optional["Audio"] = None
    document: Optional["Document"] = None
    photo: Optional[List["PhotoSize"]] = None
    sticker: Optional["Sticker"] = None
    video: Optional["Video"] = None
    video_note: Optional["VideoNote"] = None
    voice: Optional["Voice"] = None
    caption: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    contact: Optional["Contact"] = None
    dice: Optional["Dice"] = None
    game: Optional["Game"] = None
    poll: Optional["Poll"] = None
    venue: Optional["Venue"] = None
    location: Optional["Location"] = None
    new_chat_members: Optional[List["User"]] = None
    left_chat_member: Optional["User"] = None
    new_chat_title: Optional[str] = None
    new_chat_photo: Optional[List["PhotoSize"]] = None
    delete_chat_photo: Optional[bool] = None
    group_chat_created: Optional[bool] = None
    supergroup_chat_created: Optional[bool] = None
    channel_chat_created: Optional[bool] = None
    migrate_to_chat_id: Optional[int] = None
    migrate_from_chat_id: Optional[int] = None
    pinned_message: Optional["Message"] = None
    invoice: Optional["Invoice"] = None
    successful_payment: Optional["SuccessfulPayment"] = None
    connected_website: Optional[str] = None
    passport_data: Optional["PassportData"] = None
    proximity_alert_triggered: Optional["ProximityAlertTriggered"] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None

    model_config = {"populate_by_name": True}


class MessageId(BaseModel):
    """This object represents a unique message identifier."""

    message_id: int

    model_config = {"populate_by_name": True}


class MessageEntity(BaseModel):
    """This object represents one special entity in a text message. For example, hashtags, usernames, URLs, etc."""

    type: str
    offset: int
    length: int
    url: Optional[str] = None
    user: Optional["User"] = None
    language: Optional[str] = None

    model_config = {"populate_by_name": True}


class PhotoSize(BaseModel):
    """This object represents one size of a photo or a [file](https://core.telegram.org/bots/api/#document) / [sticker](https://core.telegram.org/bots/api/#sticker) thumbnail."""

    file_id: str
    file_unique_id: str
    width: int
    height: int
    file_size: Optional[int] = None

    model_config = {"populate_by_name": True}


class Animation(BaseModel):
    """This object represents an animation file (GIF or H.264/MPEG-4 AVC video without sound)."""

    file_id: str
    file_unique_id: str
    width: int
    height: int
    duration: int
    thumb: Optional["PhotoSize"] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None

    model_config = {"populate_by_name": True}


class Audio(BaseModel):
    """This object represents an audio file to be treated as music by the Telegram clients."""

    file_id: str
    file_unique_id: str
    duration: int
    performer: Optional[str] = None
    title: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    thumb: Optional["PhotoSize"] = None

    model_config = {"populate_by_name": True}


class Document(BaseModel):
    """This object represents a general file (as opposed to [photos](https://core.telegram.org/bots/api/#photosize), [voice messages](https://core.telegram.org/bots/api/#voice) and [audio files](https://core"""

    file_id: str
    file_unique_id: str
    thumb: Optional["PhotoSize"] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None

    model_config = {"populate_by_name": True}


class Video(BaseModel):
    """This object represents a video file."""

    file_id: str
    file_unique_id: str
    width: int
    height: int
    duration: int
    thumb: Optional["PhotoSize"] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None

    model_config = {"populate_by_name": True}


class VideoNote(BaseModel):
    """This object represents a [video message](https://telegram.org/blog/video-messages-and-telescope) (available in Telegram apps as of [v.4.0](https://telegram.org/blog/video-messages-and-telescope))."""

    file_id: str
    file_unique_id: str
    length: int
    duration: int
    thumb: Optional["PhotoSize"] = None
    file_size: Optional[int] = None

    model_config = {"populate_by_name": True}


class Voice(BaseModel):
    """This object represents a voice note."""

    file_id: str
    file_unique_id: str
    duration: int
    mime_type: Optional[str] = None
    file_size: Optional[int] = None

    model_config = {"populate_by_name": True}


class Contact(BaseModel):
    """This object represents a phone contact."""

    phone_number: str
    first_name: str
    last_name: Optional[str] = None
    user_id: Optional[int] = None
    vcard: Optional[str] = None

    model_config = {"populate_by_name": True}


class Dice(BaseModel):
    """This object represents an animated emoji that displays a random value."""

    emoji: str
    value: int

    model_config = {"populate_by_name": True}


class PollOption(BaseModel):
    """This object contains information about one answer option in a poll."""

    text: str
    voter_count: int

    model_config = {"populate_by_name": True}


class PollAnswer(BaseModel):
    """This object represents an answer of a user in a non-anonymous poll."""

    poll_id: str
    user: "User"
    option_ids: List[int]

    model_config = {"populate_by_name": True}


class Poll(BaseModel):
    """This object contains information about a poll."""

    id: str
    question: str
    options: List["PollOption"]
    total_voter_count: int
    is_closed: bool
    is_anonymous: bool
    type: str
    allows_multiple_answers: bool
    correct_option_id: Optional[int] = None
    explanation: Optional[str] = None
    explanation_entities: Optional[List["MessageEntity"]] = None
    open_period: Optional[int] = None
    close_date: Optional[int] = None

    model_config = {"populate_by_name": True}


class Location(BaseModel):
    """This object represents a point on the map."""

    longitude: float
    latitude: float
    horizontal_accuracy: Optional[float] = None
    live_period: Optional[int] = None
    heading: Optional[int] = None
    proximity_alert_radius: Optional[int] = None

    model_config = {"populate_by_name": True}


class Venue(BaseModel):
    """This object represents a venue."""

    location: "Location"
    title: str
    address: str
    foursquare_id: Optional[str] = None
    foursquare_type: Optional[str] = None
    google_place_id: Optional[str] = None
    google_place_type: Optional[str] = None

    model_config = {"populate_by_name": True}


class ProximityAlertTriggered(BaseModel):
    """This object represents the content of a service message, sent whenever a user in the chat triggers a proximity alert set by another user."""

    traveler: "User"
    watcher: "User"
    distance: int

    model_config = {"populate_by_name": True}


class UserProfilePhotos(BaseModel):
    """This object represent a user's profile pictures."""

    total_count: int
    photos: List[List["PhotoSize"]]

    model_config = {"populate_by_name": True}


class File(BaseModel):
    """This object represents a file ready to be downloaded. The file can be downloaded via the link `https://api.telegram.org/file/bot<token>/<file_path>`. It is guaranteed that the link will be valid for a"""

    file_id: str
    file_unique_id: str
    file_size: Optional[int] = None
    file_path: Optional[str] = None

    model_config = {"populate_by_name": True}


class ReplyKeyboardMarkup(BaseModel):
    """This object represents a [custom keyboard](https://core.telegram.org/bots#keyboards) with reply options (see [Introduction to bots](https://core.telegram.org/bots#keyboards) for details and examples)."""

    keyboard: List[List["KeyboardButton"]]
    resize_keyboard: Optional[bool] = False
    one_time_keyboard: Optional[bool] = False
    selective: Optional[bool] = None

    model_config = {"populate_by_name": True}


class KeyboardButton(BaseModel):
    """This object represents one button of the reply keyboard. For simple text buttons *String* can be used instead of this object to specify text of the button. Optional fields *request_contact*, *request_"""

    text: str
    request_contact: Optional[bool] = None
    request_location: Optional[bool] = None
    request_poll: Optional["KeyboardButtonPollType"] = None

    model_config = {"populate_by_name": True}


class KeyboardButtonPollType(BaseModel):
    """This object represents type of a poll, which is allowed to be created and sent when the corresponding button is pressed."""

    type: Optional[str] = None

    model_config = {"populate_by_name": True}


class ReplyKeyboardRemove(BaseModel):
    """Upon receiving a message with this object, Telegram clients will remove the current custom keyboard and display the default letter-keyboard. By default, custom keyboards are displayed until a new keyb"""

    remove_keyboard: bool
    selective: Optional[bool] = None

    model_config = {"populate_by_name": True}


class InlineKeyboardMarkup(BaseModel):
    """This object represents an [inline keyboard](https://core.telegram.org/bots#inline-keyboards-and-on-the-fly-updating) that appears right next to the message it belongs to."""

    inline_keyboard: List[List["InlineKeyboardButton"]]

    model_config = {"populate_by_name": True}


class InlineKeyboardButton(BaseModel):
    """This object represents one button of an inline keyboard. You **must** use exactly one of the optional fields."""

    text: str
    url: Optional[str] = None
    login_url: Optional["LoginUrl"] = None
    callback_data: Optional[str] = None
    switch_inline_query: Optional[str] = None
    switch_inline_query_current_chat: Optional[str] = None
    callback_game: Optional["CallbackGame"] = None
    pay: Optional[bool] = None

    model_config = {"populate_by_name": True}


class LoginUrl(BaseModel):
    """This object represents a parameter of the inline keyboard button used to automatically authorize a user. Serves as a great replacement for the [Telegram Login Widget](https://core.telegram.org/widgets"""

    url: str
    forward_text: Optional[str] = None
    bot_username: Optional[str] = None
    request_write_access: Optional[bool] = None

    model_config = {"populate_by_name": True}


class CallbackQuery(BaseModel):
    """This object represents an incoming callback query from a callback button in an [inline keyboard](/bots#inline-keyboards-and-on-the-fly-updating). If the button that originated the query was attached t"""

    id: str
    from_field: "User" = Field(..., alias="from")
    chat_instance: str
    message: Optional["Message"] = None
    inline_message_id: Optional[str] = None
    data: Optional[str] = None
    game_short_name: Optional[str] = None

    model_config = {"populate_by_name": True}


class ForceReply(BaseModel):
    """Upon receiving a message with this object, Telegram clients will display a reply interface to the user (act as if the user has selected the bot's message and tapped 'Reply'). This can be extremely use"""

    force_reply: bool
    selective: Optional[bool] = None

    model_config = {"populate_by_name": True}


class ChatPhoto(BaseModel):
    """This object represents a chat photo."""

    small_file_id: str
    small_file_unique_id: str
    big_file_id: str
    big_file_unique_id: str

    model_config = {"populate_by_name": True}


class ChatMember(BaseModel):
    """This object contains information about one member of a chat."""

    user: "User"
    status: str
    custom_title: Optional[str] = None
    is_anonymous: Optional[bool] = None
    can_be_edited: Optional[bool] = None
    can_post_messages: Optional[bool] = None
    can_edit_messages: Optional[bool] = None
    can_delete_messages: Optional[bool] = None
    can_restrict_members: Optional[bool] = None
    can_promote_members: Optional[bool] = None
    can_change_info: Optional[bool] = None
    can_invite_users: Optional[bool] = None
    can_pin_messages: Optional[bool] = None
    is_member: Optional[bool] = None
    can_send_messages: Optional[bool] = None
    can_send_media_messages: Optional[bool] = None
    can_send_polls: Optional[bool] = None
    can_send_other_messages: Optional[bool] = None
    can_add_web_page_previews: Optional[bool] = None
    until_date: Optional[int] = None

    model_config = {"populate_by_name": True}


class ChatPermissions(BaseModel):
    """Describes actions that a non-administrator user is allowed to take in a chat."""

    can_send_messages: Optional[bool] = None
    can_send_media_messages: Optional[bool] = None
    can_send_polls: Optional[bool] = None
    can_send_other_messages: Optional[bool] = None
    can_add_web_page_previews: Optional[bool] = None
    can_change_info: Optional[bool] = None
    can_invite_users: Optional[bool] = None
    can_pin_messages: Optional[bool] = None

    model_config = {"populate_by_name": True}


class ChatLocation(BaseModel):
    """Represents a location to which a chat is connected."""

    location: "Location"
    address: str

    model_config = {"populate_by_name": True}


class BotCommand(BaseModel):
    """This object represents a bot command."""

    command: str
    description: str

    model_config = {"populate_by_name": True}


class ResponseParameters(BaseModel):
    """Contains information about why a request was unsuccessful."""

    migrate_to_chat_id: Optional[int] = None
    retry_after: Optional[int] = None

    model_config = {"populate_by_name": True}


class InputMedia(BaseModel):
    """This object represents the content of a media message to be sent. It should be one of"""

    pass

    model_config = {"populate_by_name": True}


class InputMediaPhoto(BaseModel):
    """Represents a photo to be sent."""

    type: str
    media: str
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None

    model_config = {"populate_by_name": True}


class InputMediaVideo(BaseModel):
    """Represents a video to be sent."""

    type: str
    media: str
    thumb: Optional[Union["InputFile", str]] = None
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None
    supports_streaming: Optional[bool] = None

    model_config = {"populate_by_name": True}


class InputMediaAnimation(BaseModel):
    """Represents an animation file (GIF or H.264/MPEG-4 AVC video without sound) to be sent."""

    type: str
    media: str
    thumb: Optional[Union["InputFile", str]] = None
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None

    model_config = {"populate_by_name": True}


class InputMediaAudio(BaseModel):
    """Represents an audio file to be treated as music to be sent."""

    type: str
    media: str
    thumb: Optional[Union["InputFile", str]] = None
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    duration: Optional[int] = None
    performer: Optional[str] = None
    title: Optional[str] = None

    model_config = {"populate_by_name": True}


class InputMediaDocument(BaseModel):
    """Represents a general file to be sent."""

    type: str
    media: str
    thumb: Optional[Union["InputFile", str]] = None
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    disable_content_type_detection: Optional[bool] = None

    model_config = {"populate_by_name": True}


class InputFile(BaseModel):
    """This object represents the contents of a file to be uploaded. Must be posted using multipart/form-data in the usual way that files are uploaded via the browser."""

    pass

    model_config = {"populate_by_name": True}


class Sticker(BaseModel):
    """This object represents a sticker."""

    file_id: str
    file_unique_id: str
    width: int
    height: int
    is_animated: bool
    thumb: Optional["PhotoSize"] = None
    emoji: Optional[str] = None
    set_name: Optional[str] = None
    mask_position: Optional["MaskPosition"] = None
    file_size: Optional[int] = None

    model_config = {"populate_by_name": True}


class StickerSet(BaseModel):
    """This object represents a sticker set."""

    name: str
    title: str
    is_animated: bool
    contains_masks: bool
    stickers: List["Sticker"]
    thumb: Optional["PhotoSize"] = None

    model_config = {"populate_by_name": True}


class MaskPosition(BaseModel):
    """This object describes the position on faces where a mask should be placed by default."""

    point: str
    x_shift: float
    y_shift: float
    scale: float

    model_config = {"populate_by_name": True}


class InlineQuery(BaseModel):
    """This object represents an incoming inline query. When the user sends an empty query, your bot could return some default or trending results."""

    id: str
    from_field: "User" = Field(..., alias="from")
    query: str
    offset: str
    location: Optional["Location"] = None

    model_config = {"populate_by_name": True}


class InlineQueryResult(BaseModel):
    """This object represents one result of an inline query. Telegram clients currently support results of the following 20 types:"""

    pass

    model_config = {"populate_by_name": True}


class InlineQueryResultArticle(BaseModel):
    """Represents a link to an article or web page."""

    type: str
    id: str
    title: str
    input_message_content: "InputMessageContent"
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    url: Optional[str] = None
    hide_url: Optional[bool] = None
    description: Optional[str] = None
    thumb_url: Optional[str] = None
    thumb_width: Optional[int] = None
    thumb_height: Optional[int] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultPhoto(BaseModel):
    """Represents a link to a photo. By default, this photo will be sent by the user with optional caption. Alternatively, you can use *input_message_content* to send a message with the specified content ins"""

    type: str
    id: str
    photo_url: str
    thumb_url: str
    photo_width: Optional[int] = None
    photo_height: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultGif(BaseModel):
    """Represents a link to an animated GIF file. By default, this animated GIF file will be sent by the user with optional caption. Alternatively, you can use *input_message_content* to send a message with """

    type: str
    id: str
    gif_url: str
    thumb_url: str
    gif_width: Optional[int] = None
    gif_height: Optional[int] = None
    gif_duration: Optional[int] = None
    thumb_mime_type: Optional[str] = 'image/jpeg'
    title: Optional[str] = None
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultMpeg4Gif(BaseModel):
    """Represents a link to a video animation (H.264/MPEG-4 AVC video without sound). By default, this animated MPEG-4 file will be sent by the user with optional caption. Alternatively, you can use *input_m"""

    type: str
    id: str
    mpeg4_url: str
    thumb_url: str
    mpeg4_width: Optional[int] = None
    mpeg4_height: Optional[int] = None
    mpeg4_duration: Optional[int] = None
    thumb_mime_type: Optional[str] = 'image/jpeg'
    title: Optional[str] = None
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultVideo(BaseModel):
    """Represents a link to a page containing an embedded video player or a video file. By default, this video file will be sent by the user with an optional caption. Alternatively, you can use *input_messag"""

    type: str
    id: str
    video_url: str
    mime_type: str
    thumb_url: str
    title: str
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    video_width: Optional[int] = None
    video_height: Optional[int] = None
    video_duration: Optional[int] = None
    description: Optional[str] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultAudio(BaseModel):
    """Represents a link to an MP3 audio file. By default, this audio file will be sent by the user. Alternatively, you can use *input_message_content* to send a message with the specified content instead of"""

    type: str
    id: str
    audio_url: str
    title: str
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    performer: Optional[str] = None
    audio_duration: Optional[int] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultVoice(BaseModel):
    """Represents a link to a voice recording in an .OGG container encoded with OPUS. By default, this voice recording will be sent by the user. Alternatively, you can use *input_message_content* to send a m"""

    type: str
    id: str
    voice_url: str
    title: str
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    voice_duration: Optional[int] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultDocument(BaseModel):
    """Represents a link to a file. By default, this file will be sent by the user with an optional caption. Alternatively, you can use *input_message_content* to send a message with the specified content in"""

    type: str
    id: str
    title: str
    document_url: str
    mime_type: str
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    description: Optional[str] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None
    thumb_url: Optional[str] = None
    thumb_width: Optional[int] = None
    thumb_height: Optional[int] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultLocation(BaseModel):
    """Represents a location on a map. By default, the location will be sent by the user. Alternatively, you can use *input_message_content* to send a message with the specified content instead of the locati"""

    type: str
    id: str
    latitude: float
    longitude: float
    title: str
    horizontal_accuracy: Optional[float] = None
    live_period: Optional[int] = None
    heading: Optional[int] = None
    proximity_alert_radius: Optional[int] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None
    thumb_url: Optional[str] = None
    thumb_width: Optional[int] = None
    thumb_height: Optional[int] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultVenue(BaseModel):
    """Represents a venue. By default, the venue will be sent by the user. Alternatively, you can use *input_message_content* to send a message with the specified content instead of the venue."""

    type: str
    id: str
    latitude: float
    longitude: float
    title: str
    address: str
    foursquare_id: Optional[str] = None
    foursquare_type: Optional[str] = None
    google_place_id: Optional[str] = None
    google_place_type: Optional[str] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None
    thumb_url: Optional[str] = None
    thumb_width: Optional[int] = None
    thumb_height: Optional[int] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultContact(BaseModel):
    """Represents a contact with a phone number. By default, this contact will be sent by the user. Alternatively, you can use *input_message_content* to send a message with the specified content instead of """

    type: str
    id: str
    phone_number: str
    first_name: str
    last_name: Optional[str] = None
    vcard: Optional[str] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None
    thumb_url: Optional[str] = None
    thumb_width: Optional[int] = None
    thumb_height: Optional[int] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultGame(BaseModel):
    """Represents a [Game](https://core.telegram.org/bots/api/#games)."""

    type: str
    id: str
    game_short_name: str
    reply_markup: Optional["InlineKeyboardMarkup"] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultCachedPhoto(BaseModel):
    """Represents a link to a photo stored on the Telegram servers. By default, this photo will be sent by the user with an optional caption. Alternatively, you can use *input_message_content* to send a mess"""

    type: str
    id: str
    photo_file_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultCachedGif(BaseModel):
    """Represents a link to an animated GIF file stored on the Telegram servers. By default, this animated GIF file will be sent by the user with an optional caption. Alternatively, you can use *input_messag"""

    type: str
    id: str
    gif_file_id: str
    title: Optional[str] = None
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultCachedMpeg4Gif(BaseModel):
    """Represents a link to a video animation (H.264/MPEG-4 AVC video without sound) stored on the Telegram servers. By default, this animated MPEG-4 file will be sent by the user with an optional caption. A"""

    type: str
    id: str
    mpeg4_file_id: str
    title: Optional[str] = None
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultCachedSticker(BaseModel):
    """Represents a link to a sticker stored on the Telegram servers. By default, this sticker will be sent by the user. Alternatively, you can use *input_message_content* to send a message with the specifie"""

    type: str
    id: str
    sticker_file_id: str
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultCachedDocument(BaseModel):
    """Represents a link to a file stored on the Telegram servers. By default, this file will be sent by the user with an optional caption. Alternatively, you can use *input_message_content* to send a messag"""

    type: str
    id: str
    title: str
    document_file_id: str
    description: Optional[str] = None
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultCachedVideo(BaseModel):
    """Represents a link to a video file stored on the Telegram servers. By default, this video file will be sent by the user with an optional caption. Alternatively, you can use *input_message_content* to s"""

    type: str
    id: str
    video_file_id: str
    title: str
    description: Optional[str] = None
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultCachedVoice(BaseModel):
    """Represents a link to a voice message stored on the Telegram servers. By default, this voice message will be sent by the user. Alternatively, you can use *input_message_content* to send a message with """

    type: str
    id: str
    voice_file_id: str
    title: str
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None

    model_config = {"populate_by_name": True}


class InlineQueryResultCachedAudio(BaseModel):
    """Represents a link to an MP3 audio file stored on the Telegram servers. By default, this audio file will be sent by the user. Alternatively, you can use *input_message_content* to send a message with t"""

    type: str
    id: str
    audio_file_id: str
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    caption_entities: Optional[List["MessageEntity"]] = None
    reply_markup: Optional["InlineKeyboardMarkup"] = None
    input_message_content: Optional["InputMessageContent"] = None

    model_config = {"populate_by_name": True}


class InputMessageContent(BaseModel):
    """This object represents the content of a message to be sent as a result of an inline query. Telegram clients currently support the following 4 types:"""

    pass

    model_config = {"populate_by_name": True}


class InputTextMessageContent(BaseModel):
    """Represents the [content](https://core.telegram.org/bots/api/#inputmessagecontent) of a text message to be sent as the result of an inline query."""

    message_text: str
    parse_mode: Optional[str] = None
    entities: Optional[List["MessageEntity"]] = None
    disable_web_page_preview: Optional[bool] = None

    model_config = {"populate_by_name": True}


class InputLocationMessageContent(BaseModel):
    """Represents the [content](https://core.telegram.org/bots/api/#inputmessagecontent) of a location message to be sent as the result of an inline query."""

    latitude: float
    longitude: float
    horizontal_accuracy: Optional[float] = None
    live_period: Optional[int] = None
    heading: Optional[int] = None
    proximity_alert_radius: Optional[int] = None

    model_config = {"populate_by_name": True}


class InputVenueMessageContent(BaseModel):
    """Represents the [content](https://core.telegram.org/bots/api/#inputmessagecontent) of a venue message to be sent as the result of an inline query."""

    latitude: float
    longitude: float
    title: str
    address: str
    foursquare_id: Optional[str] = None
    foursquare_type: Optional[str] = None
    google_place_id: Optional[str] = None
    google_place_type: Optional[str] = None

    model_config = {"populate_by_name": True}


class InputContactMessageContent(BaseModel):
    """Represents the [content](https://core.telegram.org/bots/api/#inputmessagecontent) of a contact message to be sent as the result of an inline query."""

    phone_number: str
    first_name: str
    last_name: Optional[str] = None
    vcard: Optional[str] = None

    model_config = {"populate_by_name": True}


class ChosenInlineResult(BaseModel):
    """Represents a [result](https://core.telegram.org/bots/api/#inlinequeryresult) of an inline query that was chosen by the user and sent to their chat partner."""

    result_id: str
    from_field: "User" = Field(..., alias="from")
    query: str
    location: Optional["Location"] = None
    inline_message_id: Optional[str] = None

    model_config = {"populate_by_name": True}


class LabeledPrice(BaseModel):
    """This object represents a portion of the price for goods or services."""

    label: str
    amount: int

    model_config = {"populate_by_name": True}


class Invoice(BaseModel):
    """This object contains basic information about an invoice."""

    title: str
    description: str
    start_parameter: str
    currency: str
    total_amount: int

    model_config = {"populate_by_name": True}


class ShippingAddress(BaseModel):
    """This object represents a shipping address."""

    country_code: str
    state: str
    city: str
    street_line1: str
    street_line2: str
    post_code: str

    model_config = {"populate_by_name": True}


class OrderInfo(BaseModel):
    """This object represents information about an order."""

    name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    shipping_address: Optional["ShippingAddress"] = None

    model_config = {"populate_by_name": True}


class ShippingOption(BaseModel):
    """This object represents one shipping option."""

    id: str
    title: str
    prices: List["LabeledPrice"]

    model_config = {"populate_by_name": True}


class SuccessfulPayment(BaseModel):
    """This object contains basic information about a successful payment."""

    currency: str
    total_amount: int
    invoice_payload: str
    telegram_payment_charge_id: str
    provider_payment_charge_id: str
    shipping_option_id: Optional[str] = None
    order_info: Optional["OrderInfo"] = None

    model_config = {"populate_by_name": True}


class ShippingQuery(BaseModel):
    """This object contains information about an incoming shipping query."""

    id: str
    from_field: "User" = Field(..., alias="from")
    invoice_payload: str
    shipping_address: "ShippingAddress"

    model_config = {"populate_by_name": True}


class PreCheckoutQuery(BaseModel):
    """This object contains information about an incoming pre-checkout query."""

    id: str
    from_field: "User" = Field(..., alias="from")
    currency: str
    total_amount: int
    invoice_payload: str
    shipping_option_id: Optional[str] = None
    order_info: Optional["OrderInfo"] = None

    model_config = {"populate_by_name": True}


class PassportData(BaseModel):
    """Contains information about Telegram Passport data shared with the bot by the user."""

    data: List["EncryptedPassportElement"]
    credentials: "EncryptedCredentials"

    model_config = {"populate_by_name": True}


class PassportFile(BaseModel):
    """This object represents a file uploaded to Telegram Passport. Currently all Telegram Passport files are in JPEG format when decrypted and don't exceed 10MB."""

    file_id: str
    file_unique_id: str
    file_size: int
    file_date: int

    model_config = {"populate_by_name": True}


class EncryptedPassportElement(BaseModel):
    """Contains information about documents or other Telegram Passport elements shared with the bot by the user."""

    type: str
    hash: str
    data: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    files: Optional[List["PassportFile"]] = None
    front_side: Optional["PassportFile"] = None
    reverse_side: Optional["PassportFile"] = None
    selfie: Optional["PassportFile"] = None
    translation: Optional[List["PassportFile"]] = None

    model_config = {"populate_by_name": True}


class EncryptedCredentials(BaseModel):
    """Contains data required for decrypting and authenticating [EncryptedPassportElement](https://core.telegram.org/bots/api/#encryptedpassportelement). See the [Telegram Passport Documentation](https://cor"""

    data: str
    hash: str
    secret: str

    model_config = {"populate_by_name": True}


class PassportElementError(BaseModel):
    """This object represents an error in the Telegram Passport element which was submitted that should be resolved by the user. It should be one of:"""

    pass

    model_config = {"populate_by_name": True}


class PassportElementErrorDataField(BaseModel):
    """Represents an issue in one of the data fields that was provided by the user. The error is considered resolved when the field's value changes."""

    source: str
    type: str
    field_name: str
    data_hash: str
    message: str

    model_config = {"populate_by_name": True}


class PassportElementErrorFrontSide(BaseModel):
    """Represents an issue with the front side of a document. The error is considered resolved when the file with the front side of the document changes."""

    source: str
    type: str
    file_hash: str
    message: str

    model_config = {"populate_by_name": True}


class PassportElementErrorReverseSide(BaseModel):
    """Represents an issue with the reverse side of a document. The error is considered resolved when the file with reverse side of the document changes."""

    source: str
    type: str
    file_hash: str
    message: str

    model_config = {"populate_by_name": True}


class PassportElementErrorSelfie(BaseModel):
    """Represents an issue with the selfie with a document. The error is considered resolved when the file with the selfie changes."""

    source: str
    type: str
    file_hash: str
    message: str

    model_config = {"populate_by_name": True}


class PassportElementErrorFile(BaseModel):
    """Represents an issue with a document scan. The error is considered resolved when the file with the document scan changes."""

    source: str
    type: str
    file_hash: str
    message: str

    model_config = {"populate_by_name": True}


class PassportElementErrorFiles(BaseModel):
    """Represents an issue with a list of scans. The error is considered resolved when the list of files containing the scans changes."""

    source: str
    type: str
    file_hashes: List[str]
    message: str

    model_config = {"populate_by_name": True}


class PassportElementErrorTranslationFile(BaseModel):
    """Represents an issue with one of the files that constitute the translation of a document. The error is considered resolved when the file changes."""

    source: str
    type: str
    file_hash: str
    message: str

    model_config = {"populate_by_name": True}


class PassportElementErrorTranslationFiles(BaseModel):
    """Represents an issue with the translated version of a document. The error is considered resolved when a file with the document translation change."""

    source: str
    type: str
    file_hashes: List[str]
    message: str

    model_config = {"populate_by_name": True}


class PassportElementErrorUnspecified(BaseModel):
    """Represents an issue in an unspecified place. The error is considered resolved when new data is added."""

    source: str
    type: str
    element_hash: str
    message: str

    model_config = {"populate_by_name": True}


class Game(BaseModel):
    """This object represents a game. Use BotFather to create and edit games, their short names will act as unique identifiers."""

    title: str
    description: str
    photo: List["PhotoSize"]
    text: Optional[str] = None
    text_entities: Optional[List["MessageEntity"]] = None
    animation: Optional["Animation"] = None

    model_config = {"populate_by_name": True}


class CallbackGame(BaseModel):
    """A placeholder, currently holds no information. Use [BotFather](https://t.me/botfather) to set up your game."""

    pass

    model_config = {"populate_by_name": True}


class GameHighScore(BaseModel):
    """This object represents one row of the high scores table for a game."""

    position: int
    user: "User"
    score: int

    model_config = {"populate_by_name": True}

