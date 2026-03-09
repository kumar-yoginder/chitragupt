"""Utility functions for the Chitragupt IAM bot.

Provides framework-agnostic helpers such as barcode generation.
"""

import io

import barcode
from barcode.writer import ImageWriter

from core.logger import ChitraguptLogger

logger = ChitraguptLogger.get_logger()


def generate_barcode(data: str) -> bytes:
    """Generate a Code128 barcode PNG image from *data*.

    Args:
        data: The string to encode (must consist only of digits).

    Returns:
        PNG image bytes.

    Raises:
        ValueError: If *data* is empty or contains non-digit characters.
    """
    if not data or not data.isdigit():
        raise ValueError("Input must be an integer.")

    code128 = barcode.get_barcode_class("code128")
    writer = ImageWriter()
    barcode_instance = code128(data, writer=writer)

    buf = io.BytesIO()
    barcode_instance.write(buf, options={"write_text": True})
    buf.seek(0)
    logger.info("Barcode generated", extra={"data": data, "size_bytes": buf.getbuffer().nbytes})
    return buf.getvalue()
