"""Generic command registry — single source of truth for command → handler mapping.

Eliminates the triple-maintenance problem across ``handlers.py``,
``dispatcher.py``, and ``callbacks.py`` by providing a typed, declarative
registry that all three modules consume.

Design:
- ``CommandHandler`` is a :class:`Protocol` describing the two handler
  signatures currently in use (with-RBAC and without-RBAC).
- ``CommandRegistry`` is a :class:`Generic` singleton that stores
  ``CommandEntry`` metadata and exposes lookup / iteration helpers.
- ``@register`` is a decorator applied in ``handlers.py`` to bind a
  function to a slash-command, its required action slug, and a
  human-readable description — all in **one** place.

Backward compatibility:
    - Existing handler functions keep the same signature.
    - ``dispatcher.py`` calls ``registry.dispatch()`` instead of if/elif.
    - ``callbacks.py`` calls ``registry.dispatch()`` with a synthetic message.
    - ``COMMAND_PERMISSIONS`` dict is auto-generated from the registry for
      the ``/help`` handler.
"""

from __future__ import annotations

import dataclasses
from typing import (
    Any,
    Callable,
    Coroutine,
    Generic,
    TypeVar,
    Protocol,
    runtime_checkable,
)

from core.rbac import RBAC
from sdk.models import Message

# ── Type variables ───────────────────────────────────────────────────────────

T = TypeVar("T")  # generic payload type

# ── Handler protocol ─────────────────────────────────────────────────────────

@runtime_checkable
class RBACHandler(Protocol):
    """Handler that requires RBAC + message + user_id."""
    async def __call__(self, rbac: RBAC, message: Message, user_id: int) -> None: ...  # noqa: E704


@runtime_checkable
class SimpleHandler(Protocol):
    """Handler that only needs message + user_id (no RBAC)."""
    async def __call__(self, message: Message, user_id: int) -> None: ...  # noqa: E704


# Union of both handler shapes
HandlerFunc = RBACHandler | SimpleHandler


# ── Registry entry ───────────────────────────────────────────────────────────

@dataclasses.dataclass(frozen=True, slots=True)
class CommandEntry(Generic[T]):
    """Metadata for a single registered slash-command.

    Generic over *T* so the registry can evolve from ``dict`` payloads to
    typed Pydantic models without touching business logic.
    """
    command: str              # e.g. "/kick"
    action: str               # RBAC action slug, e.g. "kick_user"
    description: str          # shown in /help
    handler: HandlerFunc      # the async callable
    needs_rbac: bool = True   # whether dispatcher must pass RBAC


# ── Generic registry ─────────────────────────────────────────────────────────

class CommandRegistry(Generic[T]):
    """Singleton command registry, generic over the message type *T*.

    Usage::

        registry: CommandRegistry[dict] = CommandRegistry()

        @registry.register("/ping", action="view_help", description="Ping")
        async def handle_ping(message: dict, user_id: int) -> None: ...

        # In the dispatcher:
        entry = registry.get("/ping")
        await entry.handler(message, user_id)
    """

    _instance: CommandRegistry[Any] | None = None
    _entries: dict[str, CommandEntry[T]]

    def __new__(cls) -> CommandRegistry[T]:
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._entries = {}
            cls._instance = inst
        return cls._instance  # type: ignore[return-value]

    # ── decorator ────────────────────────────────────────────────────────

    def register(
        self,
        command: str,
        *,
        action: str,
        description: str,
        needs_rbac: bool = True,
    ) -> Callable[[HandlerFunc], HandlerFunc]:
        """Decorator that registers *handler* for *command*.

        Example::

            @registry.register("/kick", action="kick_user",
                               description="Kick a user from the chat")
            async def handle_kick(rbac, message, user_id): ...
        """
        def decorator(func: HandlerFunc) -> HandlerFunc:
            entry = CommandEntry(
                command=command,
                action=action,
                description=description,
                handler=func,
                needs_rbac=needs_rbac,
            )
            self._entries[command] = entry
            return func
        return decorator

    # ── lookup helpers ───────────────────────────────────────────────────

    def get(self, command: str) -> CommandEntry[T] | None:
        """Return the entry for *command*, or ``None``."""
        return self._entries.get(command)

    def entries(self) -> dict[str, CommandEntry[T]]:
        """Return a *read-only* view of all registered commands."""
        return dict(self._entries)

    async def dispatch(
        self,
        command: str,
        rbac: RBAC,
        message: Message,
        user_id: int,
    ) -> bool:
        """Look up *command* and invoke its handler.

        Returns ``True`` if a handler was found and called, ``False`` otherwise.
        """
        entry = self._entries.get(command)
        if entry is None:
            return False
        if entry.needs_rbac:
            await entry.handler(rbac, message, user_id)  # type: ignore[arg-type]
        else:
            await entry.handler(message, user_id)  # type: ignore[arg-type]
        return True


# Module-level singleton — import this everywhere.
registry: CommandRegistry[Message] = CommandRegistry()
