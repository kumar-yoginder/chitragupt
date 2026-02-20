---
name: 'Chitragupt IAM Bot Standards'
description: 'Core architectural and coding rules for the Chitragupt Telegram IAM project'
applyTo: '**/*.py'
---

# Project Context: Chitragupt
Chitragupt is an Identity & Access Management (IAM) bot for Telegram.
Phase 1 uses a lightweight stack: Python `requests` (no frameworks) and JSON flat-files for persistence.

# Project Structure

> **Ignored directories:** `__pycache__/` and `.pytest_cache/` are build/test artifacts.
> **Always ignore them** when generating code, interpreting the project tree, or resolving imports.
> Never commit them to version control.

```
chitragupt/
├── main.py                     # Thin entry point — delegates to bot.dispatcher.run()
├── config.py                   # Loads BOT_TOKEN and BASE_URL from environment via python-dotenv
├── requirements.txt            # Python dependencies
├── swagger.yaml                # OpenAPI spec (Telegram Bot API) — source of truth for SDK
│
├── bot/                        # Entry point & Telegram-specific logic
│   ├── __init__.py
│   ├── handlers.py             # Slash-command handlers (/start, /help, /status, /kick, /stop, /exit, /clear, /metadata)
│   ├── callbacks.py            # Inline-keyboard callback query handlers (approval flow)
│   ├── registry.py             # Generic command registry — single source of truth for command → handler mapping
│   └── dispatcher.py           # process_update() routing + run() polling loop
│
├── core/                       # The "Brain" — framework-agnostic IAM engine
│   ├── __init__.py
│   ├── identity.py             # get_identity(): resolves the acting entity from a Telegram update
│   ├── logger.py               # ChitraguptLogger: Singleton JSON logger (console + rotating file)
│   └── rbac.py                 # RBAC class: JSON-based permission checks, user level management, persistence
│
├── sdk/                        # OOP implementation from the Swagger spec + async API helpers
│   ├── __init__.py
│   ├── models.py               # Pydantic (BaseModel) data models for every API schema
│   ├── client.py               # ChitraguptClient OOP service layer + module-level async helpers
│   └── exceptions.py           # APIException base class for non-2xx responses
│
├── data/                       # Persistence layer (JSON flat-files)
│   ├── db_rules.json           # Role definitions: levels and allowed action slugs
│   └── db_users.json           # User registry: maps user_id (str) → { name, level }
│
├── logs/                       # ChitraguptLogger rotating log files (gitignored)
│   └── chitragupt.log          # Rotating JSON log (5 MB × 5 backups)
│
└── tests/                      # Pytest test suite — mirrors bot/ and core/ structure
    ├── __init__.py
    ├── test_client.py           # Tests for sdk/client.py and sdk/exceptions.py
    ├── test_handlers.py         # Tests for bot/handlers.py, bot/callbacks.py, bot/dispatcher.py
    └── test_models.py           # Tests for sdk/models.py
```

## Directory Responsibilities

| Directory | Role | May import from | Must **never** contain |
|-----------|------|-----------------|------------------------|
| `bot/`    | Entry point & Telegram-specific logic (command handlers, callback handlers, dispatcher) | `core/`, `config`, `sdk/` | Raw dictionary parsing of Telegram payloads — use `sdk/` models instead. No RBAC logic; delegate to `core.rbac`. No direct `requests` calls — use `sdk.client` async helpers. |
| `core/`   | The **Brain** of Chitragupt — entity resolution (`identity.py`), JSON-based permission logic (`rbac.py`), logging (`logger.py`) | stdlib only + `core.logger` | **No Telegram API calls.** No imports from `bot/` or `sdk/`. No HTTP requests. Only pure IAM logic. |
| `sdk/`    | OOP `ChitraguptClient` service layer (sync methods per API endpoint) + module-level async free functions (`send_message`, `get_updates`, `delete_messages`, etc.) consumed by `bot/`. Derived from `swagger.yaml`. | `sdk/` only + `config` (lazy import for async helpers) | No business logic, no RBAC checks, no handler code. |
| `data/`   | Persistence layer — JSON flat-file storage | — (never imported; read/written only by `core.rbac`) | No Python files. Only `db_rules.json` and `db_users.json`. No temporary files (atomic writes use `tempfile` + `os.replace`). |
| `logs/`   | Destination for `ChitraguptLogger` rotating files | — (never imported; written only by `core.logger`) | No Python files. Only `chitragupt.log` and its rotated backups. Entire directory is gitignored. |
| `tests/`  | Pytest test suite mirroring `bot/`, `core/`, and `sdk/` | everything | No application code. No fixtures that mutate `data/` files on disk. |

## Boundary Rules

### Import Restrictions
```
core/  ──✗──▶  bot/       (NEVER: core must not know about the bot layer)
core/  ──✗──▶  sdk/       (NEVER: core must not depend on generated SDK)
bot/   ──✓──▶  core/      (OK: handlers use RBAC, identity, logger)
bot/   ──✓──▶  config     (OK: needs BOT_TOKEN / BASE_URL)
bot/   ──✓──▶  sdk/       (OK: uses async helpers and Pydantic models from sdk.client)
sdk/   ──✗──▶  bot/       (NEVER: SDK is self-contained)
sdk/   ──✗──▶  core/      (NEVER: SDK is self-contained)
```

### Isolation
- `sdk/` Pydantic models and `ChitraguptClient` should be consumed by `bot/` to handle
  structured data, keeping `main.py` free of any raw dictionary parsing.
- `main.py` is a **thin entry point only** — it must contain no logic beyond
  `from bot.dispatcher import run` and `run()`.

### Cleanup — Ignored Artifacts
When generating code, analyzing the project, or interpreting directory listings,
**always disregard** these directories:
- `__pycache__/` — bytecode cache (created automatically by Python)
- `.pytest_cache/` — pytest runtime cache

These directories must **never** appear in import paths, structure diagrams, or generated code.

### Anti-Patterns (God Object Prevention)
| Violation | Rule |
|-----------|------|
| A single file in `bot/` that handles commands, callbacks, polling, **and** Telegram API calls | Split into `handlers.py` (commands), `callbacks.py` (buttons), `dispatcher.py` (routing + loop). API calls live in `sdk/client.py`. |
| `core/rbac.py` making HTTP calls to Telegram | `core/` must be pure logic — move API calls to `sdk/` |
| `sdk/client.py` containing permission checks or handler routing | `sdk/` is an API wrapper only — business logic belongs in `bot/` or `core/` |
| `main.py` containing handler functions or raw dict parsing | `main.py` delegates exclusively to `bot.dispatcher.run()` |
| Any `.py` file inside `data/` or `logs/` | These are storage-only directories — no executable code |

# Architectural Patterns

## 64-bit Identity
Always treat Telegram IDs and Chat IDs as 64-bit integers. Never assume they are 10 digits or less.

## Identity Resolution (`core/identity.py`)
The `get_identity(update: dict) -> int | None` function is the **single entry point** for resolving
who is acting on any update. It checks, in order:
1. `sender_chat.id` — present for Anonymous Admins and channel posts (always a **negative** integer).
2. `from.id` — present for regular users.
3. Returns `None` if neither is present (update should be ignored).

> ⚠️ **Known gap:** The `is_special` flag (indicating an Anonymous Admin identity) is not yet
> persisted in `db_users.json`. When implementing user registration/logging, set
> `is_special: true` on any entry whose identity came from `sender_chat`.

## Update Types
`process_update()` in `bot/dispatcher.py` resolves a message from the following update fields,
in priority order:
`message` → `edited_message` → `channel_post` → `edited_channel_post`.
Always use this order when extracting the message object from an update dict.

## Bot Application Layer (`bot/`)

### `bot/handlers.py` — Command Handlers
One function per slash-command (`handle_start`, `handle_help`, `handle_status`,
`handle_stop`, `handle_kick`, `handle_clear`, `handle_metadata`). Each checks
permissions via `rbac.has_permission()` before executing any privileged action.
All Telegram API calls use the async helpers from `sdk.client` — handlers never
call `requests` directly.

### `bot/callbacks.py` — Callback Query Handlers
Processes inline-keyboard button presses (admin approval/rejection flow).

### `bot/registry.py` — Command Registry
Generic singleton registry (`CommandRegistry[Message]`) that maps slash-commands
to handler functions, action slugs, and descriptions. Used by `dispatcher.py`
for routing and by `handle_help` for building the inline-keyboard menu.

### `bot/dispatcher.py` — Update Router + Polling Loop
- `process_update(rbac, update)` — routes each update to the correct handler.
- `run()` — the main polling loop (long-polling via `get_updates`).
- `main.py` simply calls `bot.dispatcher.run()`.

## Permission Model: Action-Slug RBAC (`core/rbac.py`)

Permissions are **not** checked by comparing rank levels directly. They are checked by looking up
an **action slug** (e.g. `"kick_user"`, `"ban_user"`, `"delete_msg"`) against the list of actions
permitted for the user's level in `db_rules.json`.

### Role Levels (defined in `data/db_rules.json`)
| Level | Role Name  | Permitted Actions                                          |
|-------|------------|------------------------------------------------------------|
| 100   | SuperAdmin | `*` (wildcard — all actions)                               |
| 80    | Admin      | `view_help`, `kick_user`, `delete_msg`, `ban_user`, `mute_user`, `manage_users` |
| 50    | Moderator  | `view_help`, `kick_user`, `delete_msg`                     |
| 10    | Member     | `view_help`                                                |
| 0     | Guest      | `view_help` (default for unknown users)                    |

### `RBAC` Class — Key Methods
- `get_user_level(user_id: int) -> int` — returns the numeric level for a user, defaulting to `0`.
- `has_permission(user_id: int, action_slug: str) -> bool` — the **permission gate**. Returns `True`
  if the user's role permits `action_slug`, or if the role has the `"*"` wildcard.
- `set_user_level(user_id: int, level: int, name: str | None = None) -> None` — upserts a user
  entry and atomically persists `db_users.json`.
- `get_role_name(user_id: int) -> str` — human-readable role name.
- `get_user_actions(user_id: int) -> list[str]` — action slugs for the user's level.
- `get_superadmins() -> list[int]` — all user IDs at level 100.

### Permission Gate Rule
Every administrative command handler **must** call `rbac.has_permission(user_id, action_slug)`
**before** executing any privileged action. Example:
```python
if not rbac.has_permission(user_id, "kick_user"):
    send_message(chat_id, "⛔ You do not have permission to kick users.")
    return
```

## SDK Layer (`sdk/`)

### `sdk/models.py`
Pydantic `BaseModel` classes generated from `swagger.yaml` `components/schemas`.
Use strict type hints (`Optional`, `List`, `Dict`, `Union`) and `Field(alias=...)` for
Telegram's reserved keywords (e.g. `from` → `from_field`).

### `sdk/client.py`
`ChitraguptClient` — one method per API endpoint (sync). Accepts/returns dicts.
Raises `sdk.exceptions.APIException` for non-2xx responses.

Also contains **module-level async free functions** (`send_message`, `get_updates`,
`delete_message`, `delete_messages`, `answer_callback_query`, `get_file_info`,
`download_file`, `make_request`) that wrap blocking I/O via `asyncio.to_thread`.
These are the single API entry point for the entire `bot/` layer.

### `sdk/exceptions.py`
`APIException(status_code, response_body)` — base exception with HTTP status code and
parsed error body.

## Logging (`core/logger.py`)
- **Singleton** `ChitraguptLogger` with `get_logger()` static method.
- **Dual handlers:** `StreamHandler` (console) + `RotatingFileHandler` (`logs/chitragupt.log`).
- **JSON format:** Every log line is a JSON object with keys: `timestamp`, `level`, `logger`,
  `message`, `module`, `func_name`.
- **Rotation:** 5 MB max, 5 backup files.
- Usage: `from core.logger import ChitraguptLogger; logger = ChitraguptLogger.get_logger()`

## Data Storage
- **Rules:** `data/db_rules.json` — role definitions with `level`, `name`, and `actions` list.
- **Users:** `data/db_users.json` — a flat JSON object keyed by `str(user_id)`, each entry:
  ```json
  { "name": "display_name", "level": 10 }
  ```
- **Atomic Writes:** All writes to `db_users.json` must go through `_save_users()`, which uses
  `tempfile.NamedTemporaryFile` + `os.replace()` to prevent file corruption on crash.

## Configuration (`config.py`)
- `BOT_TOKEN` is loaded exclusively from the environment: `os.environ.get("BOT_TOKEN")`.
- `BASE_URL` is derived as `f"https://api.telegram.org/bot{BOT_TOKEN or ''}"`.
- **Never hardcode tokens.** Always use environment variables.

# Technology Stack
- **HTTP Library:** Use the `requests` library for all Telegram API calls.
- **Polling:** Long-polling via `getUpdates` with `params={"timeout": 30}` and a `requests` timeout
  of `35` seconds (always 5s more than the Telegram timeout to avoid premature disconnection).
- **Sending:** All outbound messages use `requests.post` to `sendMessage` with a `timeout=10`.
- **Data Storage:** Use the `json` module for all reads/writes to `data/db_rules.json` and
  `data/db_users.json`.
- **Validation:** Pydantic ≥ 2.0 `BaseModel` for all SDK models.

# Coding Standards
- **Naming Conventions:** Use `snake_case` for variables and functions, `PascalCase` for classes.
- **Type Hinting:** Required for all function signatures (e.g., `user_id: int`).
- **Error Handling:** Use `try-except` blocks for all API calls and JSON I/O operations.
  - Catch `requests.RequestException` for network errors.
  - Catch `json.JSONDecodeError` for malformed responses or corrupt files.
  - Catch `requests.HTTPError` separately when you need the status code.
- **Documentation:** Every function must have a brief docstring explaining its role in the IAM flow.

# Security & Compliance
- **ID Validation:** Validate that IDs are integers. Handle negative IDs correctly — they represent
  Groups/Channels (and Anonymous Admins posting as a group).
- **Permission Gates:** Every administrative command handler must call
  `rbac.has_permission(user_id, action_slug)` before execution.
- **Token Safety:** `BOT_TOKEN` must only be sourced from `os.environ.get("BOT_TOKEN")`. Never
  commit tokens to source control.
- **Atomic Persistence:** Never write user data directly with `open(..., "w")`. Always use the
  `_save_users()` atomic write pattern (`tempfile` + `os.replace`).