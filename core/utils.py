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

    code39 = barcode.get_barcode_class("code39")
    barcode_instance = code39(data, writer=ImageWriter(), add_checksum=False)
    buf = io.BytesIO()
    # Tweak the visual options to match your uploaded image
    options = {
        'module_width': 0.25,    # Thinner bars to keep it from getting too long
        'module_height': 15.0,   # Height of the bars
        'quiet_zone': 3.0,       # Margin on the sides
        'font_size': 12,         # Size of the "12345" text
        'text_distance': 5,    # Gap between bars and text
        'write_text': True       # Show the numbers below
    }
    barcode_instance.write(buf, options=options)
    buf.seek(0)
    logger.info("Barcode generated", extra={"data": data, "size_bytes": buf.getbuffer().nbytes})
    return buf.getvalue()
