"""OOP Telegram Bot API SDK — Pydantic models, service client, and exceptions.

Derived from ``swagger.yaml``. The :class:`ChitraguptClient` class wraps every
API endpoint with synchronous methods.  Module-level async free functions
(``send_message``, ``get_updates``, etc.) provide non-blocking convenience
wrappers used by the bot layer.

Usage::

    from sdk import ChitraguptClient, APIException
    from sdk.models import User, Message, Update
    from sdk.client import send_message, get_updates  # async helpers
"""

from sdk.client import ChitraguptClient
from sdk.exceptions import APIException

__all__ = [
    "ChitraguptClient",
    "APIException",
]
