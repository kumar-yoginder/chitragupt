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
    ) -> None:
        logger.info("Initialising RBAC", extra={"rules_path": rules_path, "users_path": users_path})
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

