# Chitragupt

A lightweight **Identity & Access Management (IAM)** bot for Telegram groups and channels. Chitragupt acts as an automated gatekeeper—managing roles, permissions, and administrative actions through a simple command interface backed by JSON flat-file storage.

## Features

- **Role-Based Access Control (RBAC)** — five built-in role levels (Guest → SuperAdmin) with action-slug permissions
- **64-bit Telegram ID support** — handles users, groups, channels, and anonymous admins
- **Anonymous Admin detection** — resolves identity from `sender_chat` for admins posting as the group
- **Atomic data persistence** — crash-safe writes to JSON flat-files via `tempfile` + `os.replace`
- **Long-polling** — no webhooks or external infrastructure required

## Project Structure

```
chitragupt/
├── config.py               # Loads BOT_TOKEN from .env / environment
├── main.py                 # Entry point: long-polling loop, update dispatch, command handlers
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not committed)
├── core/
│   ├── __init__.py
│   ├── identity.py         # get_identity(): resolves the acting entity from a Telegram update
│   └── rbac.py             # RBAC class: permission checks, user level management, persistence
└── data/
    ├── db_rules.json       # Role definitions: levels and allowed action slugs
    └── db_users.json       # User registry: maps user_id → { name, level }
```

## Role Levels

| Level | Role        | Permitted Actions                                               |
|-------|-------------|-----------------------------------------------------------------|
| 100   | SuperAdmin  | `*` (wildcard — all actions)                                    |
| 80    | Admin       | `view_help`, `kick_user`, `delete_msg`, `ban_user`, `mute_user` |
| 50    | Moderator   | `view_help`, `kick_user`, `delete_msg`                          |
| 10    | Member      | `view_help`                                                     |
| 0     | Guest       | `view_help` (default for unknown users)                         |

## Prerequisites

- Python 3.9+
- A Telegram Bot token (create one via [@BotFather](https://t.me/BotFather))

## Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/<your-username>/chitragupt.git
   cd chitragupt
   ```

2. **Create a virtual environment** (recommended)

   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux / macOS
   venv\Scripts\activate      # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the project root (already listed in `.gitignore`):

   ```dotenv
   BOT_TOKEN=<your-telegram-bot-token>
   ```

   The token is loaded automatically via `python-dotenv` in `config.py`.

5. **Run the bot**

   ```bash
   python main.py
   ```

## Bot Commands

| Command              | Action Slug  | Description                          |
|----------------------|-------------|--------------------------------------|
| `/kick <user_id>`    | `kick_user` | Kick a user from the group           |

> More commands (ban, mute, delete, help) are planned for upcoming releases.

## How It Works

1. **Polling** — `main.py` long-polls the Telegram Bot API via `getUpdates`.
2. **Identity Resolution** — each update is passed through `get_identity()`, which checks `sender_chat.id` (anonymous admin / channel) then `from.id` (regular user).
3. **Permission Gate** — before executing any privileged action, the handler calls `rbac.has_permission(user_id, action_slug)`.
4. **Persistence** — user roles are stored in `data/db_users.json` with atomic writes; role definitions live in `data/db_rules.json`.

## License

This project is distributed under the terms of the [LICENSE](LICENSE) file.
