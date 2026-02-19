import json
import os
import tempfile

from core.logger import ChitraguptLogger

logger = ChitraguptLogger.get_logger()


class RBAC:
    """Role-Based Access Control backed by local JSON flat-files."""

    def __init__(
        self,
        rules_path: str = "data/db_rules.json",
        users_path: str = "data/db_users.json",
    ) -> None:
        logger.info("Initialising RBAC (rules=%s, users=%s)", rules_path, users_path)
        try:
            with open(rules_path, "r") as f:
                raw_rules = json.load(f)
        except FileNotFoundError:
            logger.critical("Rules file not found: %s", rules_path)
            raise FileNotFoundError(f"Rules file not found: {rules_path}")
        except json.JSONDecodeError as exc:
            logger.critical("Invalid JSON in rules file '%s': %s", rules_path, exc)
            raise ValueError(f"Invalid JSON in rules file '{rules_path}': {exc}")

        # Build a dict keyed by numeric level for fast lookup.
        self._rules_by_level = {
            role["level"]: role for role in raw_rules.get("roles", [])
        }
        logger.info("Loaded %d role definitions", len(self._rules_by_level))

        try:
            with open(users_path, "r") as f:
                self.users = json.load(f)
        except FileNotFoundError:
            logger.critical("Users file not found: %s", users_path)
            raise FileNotFoundError(f"Users file not found: {users_path}")
        except json.JSONDecodeError as exc:
            logger.critical("Invalid JSON in users file '%s': %s", users_path, exc)
            raise ValueError(f"Invalid JSON in users file '{users_path}': {exc}")

        logger.info("Loaded %d user entries", len(self.users))
        self.users_path = users_path

    def get_user_level(self, user_id: int) -> int:
        """Return the numeric role level for user_id, defaulting to 0 (Guest)."""
        entry = self.users.get(str(user_id))
        if entry is None:
            logger.debug("User %s not found in registry, defaulting to level 0", user_id)
            return 0
        level = entry.get("level", 0)
        logger.debug("User %s has level %d", user_id, level)
        return level

    def has_permission(self, user_id: int, action_slug: str) -> bool:
        """Return True if user_id's role level permits action_slug.

        A level whose actions list contains ``"*"`` grants all permissions
        (SuperAdmin wildcard).
        """
        level = self.get_user_level(user_id)
        role = self._rules_by_level.get(level)
        if role is None:
            logger.warning("No role definition for level %d (user %s) — denying '%s'", level, user_id, action_slug)
            return False
        actions = role.get("actions", [])
        granted = "*" in actions or action_slug in actions
        if granted:
            logger.info("Permission GRANTED: user %s (level %d) -> '%s'", user_id, level, action_slug)
        else:
            logger.warning("Permission DENIED: user %s (level %d) -> '%s'", user_id, level, action_slug)
        return granted

    def set_user_level(self, user_id: int, level: int, name: str | None = None) -> None:
        """Update (or create) a user entry and persist it to db_users.json atomically."""
        key = str(user_id)
        if key not in self.users:
            self.users[key] = {
                "name": name or str(user_id),
                "level": level,
            }
            logger.info("Created new user entry: user_id=%s, level=%d, name=%s", user_id, level, name)
        else:
            old_level = self.users[key].get("level")
            self.users[key]["level"] = level
            if name:
                self.users[key]["name"] = name
            logger.info("Updated user %s: level %s -> %d", user_id, old_level, level)

        self._save_users()

    def _save_users(self) -> None:
        """Write users to disk atomically to prevent file corruption."""
        dir_name = os.path.dirname(self.users_path) or "."
        try:
            with tempfile.NamedTemporaryFile(
                "w", dir=dir_name, delete=False, suffix=".tmp"
            ) as tmp:
                json.dump(self.users, tmp, indent=2)
                tmp_path = tmp.name
            os.replace(tmp_path, self.users_path)
            logger.debug("Persisted %d users to %s", len(self.users), self.users_path)
        except OSError as exc:
            logger.error("Failed to persist users to %s: %s", self.users_path, exc)
            raise

