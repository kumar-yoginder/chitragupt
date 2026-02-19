import json
import os
import tempfile


class RBAC:
    """Role-Based Access Control backed by local JSON flat-files."""

    def __init__(
        self,
        rules_path="data/db_rules.json",
        users_path="data/db_users.json",
    ):
        try:
            with open(rules_path, "r") as f:
                raw_rules = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Rules file not found: {rules_path}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in rules file '{rules_path}': {exc}")

        # Build a dict keyed by numeric level for fast lookup.
        self._rules_by_level = {
            role["level"]: role for role in raw_rules.get("roles", [])
        }

        try:
            with open(users_path, "r") as f:
                self.users = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Users file not found: {users_path}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in users file '{users_path}': {exc}")

        self.users_path = users_path

    def get_user_level(self, user_id):
        """Return the numeric role level for user_id, defaulting to 0 (Guest)."""
        entry = self.users.get(str(user_id))
        if entry is None:
            return 0
        return entry.get("level", 0)

    def has_permission(self, user_id, action_slug):
        """Return True if user_id's role level permits action_slug.

        A level whose actions list contains ``"*"`` grants all permissions
        (SuperAdmin wildcard).
        """
        level = self.get_user_level(user_id)
        role = self._rules_by_level.get(level)
        if role is None:
            return False
        actions = role.get("actions", [])
        return "*" in actions or action_slug in actions

    def set_user_level(self, user_id, level, name=None):
        """Update (or create) a user entry and persist it to db_users.json atomically."""
        key = str(user_id)
        if key not in self.users:
            self.users[key] = {
                "name": name or str(user_id),
                "level": level,
            }
        else:
            self.users[key]["level"] = level
            if name:
                self.users[key]["name"] = name

        self._save_users()

    def _save_users(self):
        """Write users to disk atomically to prevent file corruption."""
        dir_name = os.path.dirname(self.users_path) or "."
        with tempfile.NamedTemporaryFile(
            "w", dir=dir_name, delete=False, suffix=".tmp"
        ) as tmp:
            json.dump(self.users, tmp, indent=2)
            tmp_path = tmp.name
        os.replace(tmp_path, self.users_path)

