"""Telegram bot application layer — polling, command handlers, callback handlers.

This package may import from ``core/`` and ``config`` only.
"""

from bot.callbacks import handle_callback_query
from bot.dispatcher import process_update, run
from bot.handlers import (
    handle_help,
    handle_kick,
    handle_start,
    handle_status,
    handle_stop,
)
from bot.telegram import answer_callback_query, get_updates, send_message

__all__ = [
    # Dispatcher
    "run",
    "process_update",
    # Command handlers
    "handle_start",
    "handle_help",
    "handle_status",
    "handle_stop",
    "handle_kick",
    # Callback handlers
    "handle_callback_query",
    # Telegram API helpers
    "get_updates",
    "send_message",
    "answer_callback_query",
]
