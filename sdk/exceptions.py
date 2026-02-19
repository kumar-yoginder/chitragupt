"""Exception hierarchy for the Chitragupt Telegram SDK."""

from typing import Any, Dict, Optional


class APIException(Exception):
    """Base exception for non-2xx responses from the Telegram Bot API.

    Attributes:
        status_code: HTTP status code returned by the API.
        response_body: Raw response body as a dict, when available.
    """

    def __init__(self, status_code: int, response_body: Optional[Dict[str, Any]] = None) -> None:
        """Initialise with the HTTP status code and optional body."""
        self.status_code = status_code
        self.response_body = response_body or {}
        description = self.response_body.get("description", "Unknown error")
        super().__init__(f"API error {status_code}: {description}")
