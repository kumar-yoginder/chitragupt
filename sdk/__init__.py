"""OOP Telegram Bot API SDK — Pydantic models, service client, and exceptions.

Derived from ``swagger.yaml``. This package is fully self-contained and must
NEVER import from ``bot/`` or ``core/``.

Usage::

    from sdk import ChitraguptClient, APIException
    from sdk.models import User, Message, Update
"""

from sdk.client import ChitraguptClient
from sdk.exceptions import APIException

__all__ = [
    "ChitraguptClient",
    "APIException",
]
