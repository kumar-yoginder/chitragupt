# Chitragupt

A high-concurrency **Identity & Access Management (IAM)** bot for Telegram, built on an SDK-first architecture.
Chitragupt manages roles, permissions, and administrative actions through a command interface backed by JSON flat-file storage.
The bot uses `asyncio` with a `requests` thread-pool to handle updates concurrently — long-running API calls never block the polling loop.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│  main.py  (thin entry point → bot.dispatcher.run())      │
└────────────────────────┬─────────────────────────────────┘
                         │
          ┌──────────────▼──────────────┐
          │         bot/ layer          │
          │  handlers · callbacks       │
          │  registry · dispatcher      │
          ├─────────┬───────────────────┤
          │         │                   │
  ┌───────▼───┐  ┌──▼──────────┐       │
  │  core/    │  │  sdk/       │       │
  │  identity │  │  models     │       │
  │  rbac     │  │  client     │       │
  │  logger   │  │  exceptions │       │
  └───────────┘  └─────────────┘       │
                                       │
          ┌────────────────────────────┘
          │
  ┌───────▼──────────┐
  │  data/ (JSON)    │
  │  db_rules.json   │
  │  db_users.json   │
  └──────────────────┘
```

**Import boundaries** — strictly enforced:

| Direction | Allowed? |
|-----------|----------|
| `bot/` → `core/`, `sdk/`, `config` | ✅ |
| `sdk/` → `config` (lazy) | ✅ |
| `core/` → `bot/` or `sdk/` | ❌ Never |
| `sdk/` → `bot/` or `core/` | ❌ Never |

---

## Project Structure

```
chitragupt/
├── main.py                     # Thin entry point — delegates to bot.dispatcher.run()
├── config.py                   # Loads BOT_TOKEN, SUPER_ADMINS, EXIFTOOL_PATH from environment
├── requirements.txt            # Python dependencies
├── swagger.yaml                # OpenAPI spec (Telegram Bot API) — source of truth for SDK
├── Dockerfile                  # Multi-stage build: python:3.12-slim → python:3.12-alpine
├── docker-compose.yml          # Production orchestration with security hardening
│
├── bot/                        # Telegram-specific logic
│   ├── handlers.py             # Slash-command handlers (/start, /help, /status, /kick, /clear, /metadata, /stop, /exit)
│   ├── callbacks.py            # Inline-keyboard callback query handlers (admin approval flow)
│   ├── registry.py             # Generic command registry — single source of truth for command → handler mapping
│   └── dispatcher.py           # process_update() routing + run() async polling loop
│
├── core/                       # Framework-agnostic IAM engine (no Telegram imports)
│   ├── identity.py             # get_identity(): resolves acting entity from sender_chat or from
│   ├── rbac.py                 # RBAC class: JSON-backed permission checks, user level management
│   └── logger.py               # ChitraguptLogger: singleton JSON logger (console + rotating file)
│
├── sdk/                        # OOP client + async helpers derived from swagger.yaml
│   ├── models.py               # Pydantic v2 BaseModel classes for every Telegram API schema
│   ├── client.py               # ChitraguptClient (sync) + module-level async free functions
│   └── exceptions.py           # APIException for non-2xx responses
│
├── data/                       # Persistence layer (JSON flat-files, atomic writes only)
│   ├── db_rules.json           # Role definitions: levels and allowed action slugs
│   └── db_users.json           # User registry: maps user_id → { name, level }
│
├── logs/                       # Rotating JSON log files (gitignored)
│   └── chitragupt.log          # 5 MB × 5 backups
│
└── tests/                      # Pytest test suite (68 tests)
    ├── test_client.py           # Tests for sdk/client.py and sdk/exceptions.py
    ├── test_handlers.py         # Tests for bot/handlers.py, bot/callbacks.py, bot/dispatcher.py
    └── test_models.py           # Tests for sdk/models.py
```

---

## Features

- **Action-Slug RBAC** — five role levels (Guest → SuperAdmin) with granular action-slug permissions, checked before every privileged operation
- **Dynamic Help Menu** — `/help` builds an inline-keyboard filtered by the caller's role; display order controlled by `_HELP_ORDER`
- **Interactive Admin Approval** — new users trigger inline-keyboard prompts to SuperAdmins for role assignment
- **EXIF Metadata Extraction** — `/metadata` runs ExifTool (Perl) to extract and display image EXIF data
- **Adaptive Bulk Deletion** — `/clear` uses binary-search boundary finding (`_bisect_deletable`) to efficiently delete messages in batches of 100
- **64-bit Telegram ID Support** — handles users, groups, channels, and anonymous admins (negative IDs)
- **Anonymous Admin Detection** — resolves identity from `sender_chat.id` for admins posting as the group
- **Structured JSON Logging** — dual-handler (console + rotating file) with machine-parseable JSON output
- **Atomic Data Persistence** — crash-safe writes via `tempfile.NamedTemporaryFile` + `os.replace`
- **Long-Polling** — no webhooks or external infrastructure required

---

## Bot Commands

| Command | Action Slug | Description |
|---------|-------------|-------------|
| `/start` | `view_help` | Register as Guest and request access from SuperAdmins |
| `/help` | `view_help` | Show available commands (role-filtered inline keyboard) |
| `/status` | `view_help` | View your rank, role name, and permissions |
| `/clear` | `view_help`* | Bulk-delete recent messages in the chat |
| `/metadata` | `extract_metadata` | Extract EXIF metadata from an uploaded image |
| `/kick <user_id>` | `kick_user` | Kick a user from the group |
| `/stop` | `view_help` | End your session |
| `/exit` | `view_help` | End your session (alias for `/stop`) |

\* `/clear` is visible to everyone but requires the `delete_msg` permission when used in groups.

---

## Role Levels

Defined in `data/db_rules.json`:

| Level | Role | Permitted Actions |
|-------|------|-------------------|
| 100 | SuperAdmin | `*` (wildcard — all actions) |
| 80 | Admin | `view_help`, `kick_user`, `delete_msg`, `ban_user`, `mute_user`, `manage_users`, `extract_metadata` |
| 50 | Moderator | `view_help`, `kick_user`, `delete_msg`, `extract_metadata` |
| 10 | Member | `view_help`, `extract_metadata` |
| 0 | Guest | `view_help`, `extract_metadata` (default for unknown users) |

---

## Setup & Environment

### Prerequisites

- **Python 3.12+**
- A Telegram Bot token from [@BotFather](https://t.me/BotFather)
- **ExifTool** (requires Perl) — needed for the `/metadata` command

### Local Setup

```bash
git clone https://github.com/kumar-yoginder/chitragupt.git
cd chitragupt

python -m venv venv
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows

pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root (gitignored):

```dotenv
BOT_TOKEN=<your-telegram-bot-token>
SUPER_ADMINS=755764114,12345678      # Comma-separated Telegram user IDs
EXIFTOOL_PATH=/usr/bin/exiftool      # Optional — auto-resolved from PATH if omitted
LOG_LEVEL=INFO                       # Optional — DEBUG, INFO, WARNING, ERROR
```

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | **Yes** | Telegram Bot API token |
| `SUPER_ADMINS` | Recommended | Comma-separated list of user IDs granted level 100 at startup |
| `EXIFTOOL_PATH` | No | Absolute path to the ExifTool binary; auto-resolved if omitted |
| `LOG_LEVEL` | No | Python logging level (default: `INFO`) |

### Run

```bash
python main.py
```

---

## Docker

### Build & Run

```bash
docker compose build
docker compose up -d
```

### Image Details

The `Dockerfile` uses a **multi-stage build**:

1. **Builder** (`python:3.12-slim`) — installs Python dependencies into a virtual environment.
2. **Final** (`python:3.12-alpine`) — copies the venv + source code, installs `perl` and `exiftool` via `apk`.

### Security Hardening

| Feature | Detail |
|---------|--------|
| Non-root user | Runs as `chitragupt_user` in `chitragupt_group` |
| `cap_drop: ALL` | All Linux kernel capabilities dropped |
| Read-only source | Application code is root-owned; only `data/` and `logs/` are writable |
| Resource limits | 0.5 CPU, 512 MB memory |
| Restart policy | `unless-stopped` |

### Volumes

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| `./data` | `/app/data` | Persistent JSON databases |
| `./logs` | `/app/logs` | Rotating log files |

---

## How It Works

1. **Polling** — `bot/dispatcher.py` long-polls the Telegram Bot API via `getUpdates` (30 s timeout, 35 s request timeout).
2. **Model Validation** — each raw update is validated through `Update.model_validate()` (Pydantic v2) before processing.
3. **Identity Resolution** — `core/identity.py` resolves the actor: `sender_chat.id` (anonymous admin / channel) → `from.id` (regular user) → `None` (ignored).
4. **Command Registry** — `bot/registry.py` maps slash-commands to handlers via `@registry.register` decorators with action slugs and descriptions.
5. **Permission Gate** — every handler calls `rbac.has_permission(user_id, action_slug)` before executing privileged actions.
6. **SDK Layer** — all Telegram API calls go through `sdk/client.py` async free functions (`send_message`, `delete_messages`, `make_request`, etc.), which wrap `requests` calls via `asyncio.to_thread`.
7. **Persistence** — user data is atomically written to `data/db_users.json` via `tempfile` + `os.replace`.

---

## Developer Guide

### Run Tests

```bash
pytest tests/ -v
```

68 tests cover the SDK client, Pydantic models, command handlers, callbacks, and the dispatcher.

### SDK Generation

The `sdk/models.py` Pydantic models are derived from `swagger.yaml` (OpenAPI 3.0 spec of the Telegram Bot API).
When the upstream API changes, update `swagger.yaml` and regenerate/update the models accordingly.

### Logging

All log output uses `core/logger.py` — a singleton `ChitraguptLogger` that writes JSON-formatted lines to both the console and `logs/chitragupt.log` (5 MB max, 5 rotated backups).

```json
{"timestamp": "2025-01-01T00:00:00", "level": "INFO", "logger": "chitragupt", "message": "...", "module": "handlers", "func_name": "handle_start"}
```

---

## License

This project is licensed under the **GNU General Public License v3.0** — see the [LICENSE](LICENSE) file for details.
