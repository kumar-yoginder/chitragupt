---
name: 'Chitragupt IAM Bot Standards'
description: 'Core architectural and coding rules for the Chitragupt Telegram IAM project'
applyTo: '**/*.py'
---

# Project Context: Chitragupt
Chitragupt is an Identity & Access Management (IAM) bot for Telegram.
Phase 1 uses a lightweight stack: Python `requests` (no frameworks) and JSON flat-files for persistence.

# Project Structure
```
chitragupt/
├── config.py               # Loads BOT_TOKEN and BASE_URL from environment
├── main.py                 # Entry point: long-polling loop, update dispatch, command handlers
├── core/
│   ├── __init__.py
│   ├── identity.py         # get_identity(): resolves the acting entity from a Telegram update
│   └── rbac.py             # RBAC class: permission checks, user level management, persistence
└── data/
    ├── db_rules.json       # Role definitions: levels and allowed action slugs
    └── db_users.json       # User registry: maps user_id (str) → { name, level }
```

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
`process_update()` in `main.py` resolves a message from the following update fields, in priority order:
`message` → `edited_message` → `channel_post` → `edited_channel_post`.
Always use this order when extracting the message object from an update dict.

## Permission Model: Action-Slug RBAC (`core/rbac.py`)

Permissions are **not** checked by comparing rank levels directly. They are checked by looking up
an **action slug** (e.g. `"kick_user"`, `"ban_user"`, `"delete_msg"`) against the list of actions
permitted for the user's level in `db_rules.json`.

### Role Levels (defined in `data/db_rules.json`)
| Level | Role Name  | Permitted Actions                                          |
|-------|------------|------------------------------------------------------------|
| 100   | SuperAdmin | `*` (wildcard — all actions)                               |
| 80    | Admin      | `view_help`, `kick_user`, `delete_msg`, `ban_user`, `mute_user` |
| 50    | Moderator  | `view_help`, `kick_user`, `delete_msg`                     |
| 10    | Member     | `view_help`                                                |
| 0     | Guest      | `view_help` (default for unknown users)                    |

### `RBAC` Class — Key Methods
- `get_user_level(user_id: int) -> int` — returns the numeric level for a user, defaulting to `0`.
- `has_permission(user_id: int, action_slug: str) -> bool` — the **permission gate**. Returns `True`
  if the user's role permits `action_slug`, or if the role has the `"*"` wildcard.
- `set_user_level(user_id: int, level: int, name: str | None = None) -> None` — upserts a user
  entry and atomically persists `db_users.json`.

### Permission Gate Rule
Every administrative command handler **must** call `rbac.has_permission(user_id, action_slug)`
**before** executing any privileged action. Example:
```python
if not rbac.has_permission(user_id, "kick_user"):
    send_message(chat_id, "⛔ You do not have permission to kick users.")
    return
```

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