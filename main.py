"""Chitragupt — Entry point.

Delegates all work to :func:`bot.dispatcher.run` via :func:`asyncio.run`.
"""

import asyncio

from bot.dispatcher import run

if __name__ == "__main__":
    asyncio.run(run())
