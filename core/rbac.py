import json


class RBAC:
    """Role-Based Access Control backed by local JSON flat-files."""

    def __init__(
        self,
        rules_path="data/rules.json",
        users_path="data/users.json",
    ):
        try:
            with open(rules_path, "r") as f:
                self.rules = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Rules file not found: {rules_path}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in rules file '{rules_path}': {exc}")

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

        The lookup walks rules.json: each key is a numeric level string and its
        value contains an "actions" list.  A user may perform an action if the
        action_slug appears in the actions list of their exact level entry.
        """
        level = self.get_user_level(user_id)
        role = self.rules.get(str(level))
        if role is None:
            return False
        return action_slug in role.get("actions", [])

    def set_user_level(self, user_id, level, name=None):
        """Update (or create) a user entry and persist it to users.json."""
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

        with open(self.users_path, "w") as f:
            json.dump(self.users, f, indent=2)
