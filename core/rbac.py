"""Role-Based Access Control engine backed by local JSON flat-files.

Permissions are checked via action-slug lookup (not rank-level comparison).
All writes to ``db_users.json`` use atomic ``tempfile`` + ``os.replace``.
"""

import asyncio
import json
import os
import tempfile

from config import SUPER_ADMINS
from core.logger import ChitraguptLogger

logger = ChitraguptLogger.get_logger()

# Keys stored per-user beyond 'name' and 'level'.
USER_META_KEYS: tuple[str, ...] = (
    "username", "first_name", "last_name", "language_code", "is_premium", "is_special",
)


class RBAC:
    """Role-Based Access Control backed by local JSON flat-files."""

    def __init__(
        self,
        rules_path: str = "data/db_rules.json",
        users_path: str = "data/db_users.json",
        chats_path: str = "data/db_chats.json",
    ) -> None:
        logger.info("Initialising RBAC", extra={"rules_path": rules_path, "users_path": users_path, "chats_path": chats_path})
        try:
            with open(rules_path, "r") as f:
                raw_rules = json.load(f)
        except FileNotFoundError:
            logger.critical("Rules file not found", extra={"rules_path": rules_path})
            raise FileNotFoundError(f"Rules file not found: {rules_path}")
        except json.JSONDecodeError as exc:
            logger.critical("Invalid JSON in rules file", extra={"rules_path": rules_path, "error": str(exc)})
            raise ValueError(f"Invalid JSON in rules file '{rules_path}': {exc}")

        # Build a dict keyed by numeric level for fast lookup.
        self._rules_by_level = {
            role["level"]: role for role in raw_rules.get("roles", [])
        }
        logger.info("Loaded role definitions", extra={"role_count": len(self._rules_by_level)})

        try:
            with open(users_path, "r") as f:
                self.users = json.load(f)
        except FileNotFoundError:
            logger.critical("Users file not found", extra={"users_path": users_path})
            raise FileNotFoundError(f"Users file not found: {users_path}")
        except json.JSONDecodeError as exc:
            logger.critical("Invalid JSON in users file", extra={"users_path": users_path, "error": str(exc)})
            raise ValueError(f"Invalid JSON in users file '{users_path}': {exc}")

        logger.info("Loaded user entries", extra={"user_count": len(self.users)})
        self.users_path = users_path
        self.chats_path = chats_path
        self.chats = self._load_chats()
        self._lock = asyncio.Lock()

    def get_user_level(self, user_id: int) -> int:
        """Return the numeric role level for user_id, defaulting to 0 (Guest)."""
        entry = self.users.get(str(user_id))
        if entry is None:
            logger.debug("User not found in registry, defaulting to level 0", extra={"user_id": user_id})
            return 0
        level = entry.get("level", 0)
        logger.debug("User level resolved", extra={"user_id": user_id, "level": level})
        return level

    def has_permission(self, user_id: int, action_slug: str) -> bool:
        """Return True if user_id's role level permits action_slug.

        If the user_id appears in the ``SUPER_ADMINS`` environment list the
        check short-circuits to ``True`` immediately.  Otherwise a level whose
        actions list contains ``"*"`` grants all permissions (SuperAdmin
        wildcard).
        """
        # Global privilege injection — env-level super-admins bypass everything.
        if user_id in SUPER_ADMINS:
            logger.info(
                "Permission GRANTED (env SUPER_ADMIN bypass)",
                extra={"user_id": user_id, "action": action_slug, "reason": "env_super_admin"},
            )
            return True

        level = self.get_user_level(user_id)
        role = self._rules_by_level.get(level)
        if role is None:
            logger.warning("No role definition for level — denying", extra={"user_id": user_id, "level": level, "action": action_slug})
            return False
        actions = role.get("actions", [])
        granted = "*" in actions or action_slug in actions
        if granted:
            logger.info("Permission GRANTED", extra={"user_id": user_id, "level": level, "action": action_slug, "role_actions": actions})
        else:
            logger.warning("Permission DENIED", extra={"user_id": user_id, "level": level, "action": action_slug, "role_actions": actions})
        return granted

    async def set_user_level(
        self,
        user_id: int,
        level: int,
        name: str | None = None,
        **metadata: object,
    ) -> None:
        """Update (or create) a user entry and persist it to db_users.json atomically.

        Accepts optional rich metadata keys: *username*, *first_name*,
        *last_name*, *language_code*, *is_premium*, *is_special*.
        """
        key = str(user_id)
        if key not in self.users:
            entry: dict = {
                "name": name or str(user_id),
                "level": level,
            }
            for mk in USER_META_KEYS:
                if mk in metadata and metadata[mk] is not None:
                    entry[mk] = metadata[mk]
            self.users[key] = entry
            logger.info("Created new user entry", extra={"user_id": user_id, "level": level, "display_name": name})
        else:
            old_level = self.users[key].get("level")
            self.users[key]["level"] = level
            if name:
                self.users[key]["name"] = name
            for mk in USER_META_KEYS:
                if mk in metadata and metadata[mk] is not None:
                    self.users[key][mk] = metadata[mk]
            logger.info("Updated user entry", extra={"user_id": user_id, "old_level": old_level, "new_level": level})

        await self._save_users()

    def get_role_name(self, user_id: int) -> str:
        """Return the human-readable role name for *user_id*."""
        level = self.get_user_level(user_id)
        role = self._rules_by_level.get(level)
        if role is None:
            return "Unknown"
        return role.get("name", "Unknown")

    def get_user_actions(self, user_id: int) -> list[str]:
        """Return the list of action slugs permitted for *user_id*."""
        level = self.get_user_level(user_id)
        role = self._rules_by_level.get(level)
        if role is None:
            return []
        return role.get("actions", [])

    def get_groups(self) -> dict[str, dict]:
        """Return unique groups/chats derived from the user registry.

        Negative user IDs represent groups or channels where the bot is
        active.  Returns a dict keyed by the string user-ID with the
        corresponding entry value.
        """
        groups: dict[str, dict] = {}
        for uid_str, entry in self.users.items():
            try:
                uid = int(uid_str)
            except ValueError:
                continue
            if uid < 0:
                groups[uid_str] = entry
        logger.debug("Found groups", extra={"count": len(groups)})
        return groups

    def get_superadmins(self) -> list[int]:
        """Return a list of user IDs whose level is 100 (SuperAdmin)."""
        admins: list[int] = []
        for uid_str, entry in self.users.items():
            if entry.get("level") == 100:
                try:
                    admins.append(int(uid_str))
                except ValueError:
                    logger.warning("Invalid user_id key in db_users", extra={"uid_str": uid_str})
        logger.debug("Found SuperAdmins", extra={"count": len(admins)})
        return admins

    async def sync_super_admin(self, user_id: int, name: str, **metadata: object) -> None:
        """Ensure *user_id* is stored in db_users.json at level 100.

        Called on every interaction for env-listed SUPER_ADMINS so the
        database always mirrors the current Telegram profile.  Accepts
        optional rich metadata keys (*username*, *first_name*, *last_name*,
        *language_code*, *is_premium*, *is_special*).  Uses the existing
        atomic-write pattern.
        """
        key = str(user_id)
        entry = self.users.get(key)

        needs_update = False
        if entry is None:
            # Brand-new super admin — insert at level 100.
            new_entry: dict = {"name": name, "level": 100}
            for mk in USER_META_KEYS:
                if mk in metadata and metadata[mk] is not None:
                    new_entry[mk] = metadata[mk]
            self.users[key] = new_entry
            needs_update = True
            logger.info(
                "sync_super_admin: created new SuperAdmin entry",
                extra={"user_id": user_id, "display_name": name, "level": 100},
            )
        else:
            if entry.get("level") != 100:
                entry["level"] = 100
                needs_update = True
                logger.info(
                    "sync_super_admin: promoted user to level 100",
                    extra={"user_id": user_id, "display_name": name},
                )
            if entry.get("name") != name:
                entry["name"] = name
                needs_update = True
                logger.info(
                    "sync_super_admin: updated display name",
                    extra={"user_id": user_id, "new_name": name},
                )
            for mk in USER_META_KEYS:
                if mk in metadata and metadata[mk] is not None and entry.get(mk) != metadata[mk]:
                    entry[mk] = metadata[mk]
                    needs_update = True

        if needs_update:
            await self._save_users()

    def _load_chats(self) -> dict:
        """Load managed chats from db_chats.json."""
        try:
            if os.path.exists(self.chats_path):
                with open(self.chats_path, "r") as f:
                    data = json.load(f)
                    return data.get("chat_tracking", {})
            return {}
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("Failed to load chats", extra={"chats_path": self.chats_path, "error": str(e)})
            return {}

    def _save_chats_sync(self) -> None:
        """Synchronous atomic write for chats — called inside a thread."""
        dir_name = os.path.dirname(self.chats_path) or "."
        try:
            data = {"chat_tracking": self.chats}
            with tempfile.NamedTemporaryFile(
                "w", dir=dir_name, delete=False, suffix=".tmp"
            ) as tmp:
                json.dump(data, tmp, indent=2)
                tmp_path = tmp.name
            os.replace(tmp_path, self.chats_path)
            logger.debug("Persisted chats to disk", extra={"chat_count": len(self.chats), "chats_path": self.chats_path})
        except OSError as exc:
            logger.error("Failed to persist chats", extra={"chats_path": self.chats_path, "error": str(exc)})

    async def _save_chats(self) -> None:
        """Write chats to disk atomically, guarded by an asyncio lock."""
        async with self._lock:
            await asyncio.to_thread(self._save_chats_sync)

    def register_chat(self, chat_id: int, chat_type: str, title: str | None = None) -> None:
        """Register a new group/channel the bot has joined."""
        from datetime import datetime, timezone
        chat_key = str(chat_id)
        self.chats[chat_key] = {
            "id": chat_id,
            "type": chat_type,
            "title": title or f"Chat {chat_id}",
            "registered_at": datetime.now(timezone.utc).isoformat()
        }
        asyncio.create_task(self._save_chats())
        logger.info("Registered chat", extra={"chat_id": chat_id, "chat_type": chat_type, "title": title})

    def register_chat_member(self, chat_id: int, user_id: int, name: str, **metadata: object) -> None:
        """Register a user as a member of a specific chat (for future group-level permissions)."""
        # For now, we register users globally in db_users.json
        # In future, this could track per-chat membership
        chat_key = str(chat_id)
        if chat_key not in self.chats:
            logger.warning("Chat not registered before member registration", extra={"chat_id": chat_id, "user_id": user_id})
            return
        
        # Register in global users dictionary
        asyncio.create_task(self.set_user_level(user_id, 0, name=name, **metadata))
        logger.info("Registered chat member", extra={"chat_id": chat_id, "user_id": user_id, "name": name})

    async def sync_chat_members(self, chat_id: int, administrators: list[dict] | None = None) -> int:
        """Sync members from a group/channel into db_users.json.
        
        When bot joins existing group, fetch and register all admins as Members.
        
        Args:
            chat_id: The chat ID
            administrators: Optional list of admin user objects from getChatAdministrators
        
        Returns:
            Number of users registered/updated
        """
        if not administrators:
            logger.warning("No administrators provided for sync", extra={"chat_id": chat_id})
            return 0
        
        count = 0
        for admin_obj in administrators:
            try:
                user = admin_obj.get("user", {})
                user_id = user.get("id")
                if not user_id or user_id < 0:
                    continue
                
                first_name = user.get("first_name", str(user_id))
                username = user.get("username")
                is_bot = user.get("is_bot", False)
                
                # Skip bots
                if is_bot:
                    continue
                
                # Register as Member (level 10) if not already higher
                existing_level = self.get_user_level(user_id)
                if existing_level == 0:  # Only register if Guest (level 0)
                    await self.set_user_level(
                        user_id,
                        10,  # Member level
                        name=first_name,
                        username=username,
                        first_name=first_name,
                        language_code=user.get("language_code"),
                        is_premium=user.get("is_premium", False),
                    )
                    count += 1
                    logger.info("Auto-registered chat member as Member", extra={
                        "chat_id": chat_id,
                        "user_id": user_id,
                        "first_name": first_name,
                    })
            except (KeyError, TypeError) as exc:
                logger.warning("Error processing admin object", extra={"chat_id": chat_id, "error": str(exc), "admin_obj": admin_obj})
                continue
        
        logger.info("Chat member sync complete", extra={"chat_id": chat_id, "registered_count": count})
        return count

    def unregister_chat(self, chat_id: int) -> None:
        """Unregister a chat (bot removed from group/channel)."""
        chat_key = str(chat_id)
        if chat_key in self.chats:
            del self.chats[chat_key]
            asyncio.create_task(self._save_chats())
            logger.info("Unregistered chat", extra={"chat_id": chat_id})

    def get_managed_chats(self) -> list[dict]:
        """Get all managed groups and channels sorted by registration time."""
        return sorted(
            self.chats.values(),
            key=lambda x: x.get("registered_at", ""),
            reverse=True
        )

    def get_chat_info(self, chat_id: int) -> dict | None:
        """Get info about a specific chat."""
        return self.chats.get(str(chat_id))

    def get_all_users(self) -> list[tuple[int, dict]]:
        """Return all users as a sorted list of (user_id, user_data) tuples."""
        users_list = []
        for uid_str, data in self.users.items():
            try:
                uid = int(uid_str)
                if uid > 0:  # Exclude negative IDs (groups/channels)
                    users_list.append((uid, data))
            except ValueError:
                continue
        return sorted(users_list, key=lambda x: x[0])

    async def _save_users(self) -> None:
        """Write users to disk atomically, guarded by an asyncio lock."""
        async with self._lock:
            await asyncio.to_thread(self._save_users_sync)

    def _save_users_sync(self) -> None:
        """Synchronous atomic write — called inside a thread by ``_save_users``."""
        dir_name = os.path.dirname(self.users_path) or "."
        try:
            with tempfile.NamedTemporaryFile(
                "w", dir=dir_name, delete=False, suffix=".tmp"
            ) as tmp:
                json.dump(self.users, tmp, indent=2)
                tmp_path = tmp.name
            os.replace(tmp_path, self.users_path)
            logger.debug("Persisted users to disk", extra={"user_count": len(self.users), "users_path": self.users_path})
        except OSError as exc:
            logger.error("Failed to persist users", extra={"users_path": self.users_path, "error": str(exc)})
            raise

