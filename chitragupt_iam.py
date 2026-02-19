import json
import os


class ChitraguptIAM:
    """Identity and Access Management for Telegram groups."""

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
                self.users_data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Users file not found: {users_path}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in users file '{users_path}': {exc}")

        self.users_path = users_path

    def identify_entity(self, update):
        """Extract entity ID from an update.

        Returns the sender_chat ID (negative group ID) for anonymous admins,
        or the from.id for regular users.
        """
        message = (
            update.get("message")
            or update.get("edited_message")
            or update.get("channel_post")
        )
        if not message:
            return None

        # Anonymous admins send messages as the group (sender_chat.id is negative)
        sender_chat = message.get("sender_chat")
        if sender_chat:
            return sender_chat.get("id")

        from_user = message.get("from")
        if from_user:
            return from_user.get("id")

        return None

    def can_perform(self, entity_id, action):
        """Check whether entity_id has a sufficient level to perform action.

        Negative IDs represent Special Entities (anonymous admins identified by
        group ID). They still require a sufficient rank level for the action.
        """
        required_level = self.rules.get(action)
        if required_level is None:
            return False

        entity = self.users_data["entities"].get(str(entity_id))
        if entity is None:
            return False

        entity_level = entity.get("level", 0)
        return entity_level >= required_level

    def get_entity_level(self, entity_id):
        """Return the current level of an entity, or 0 if unknown."""
        entity = self.users_data["entities"].get(str(entity_id))
        if entity is None:
            return 0
        return entity.get("level", 0)

    def update_entity_level(self, entity_id, new_level, name=None):
        """Update (or create) an entity's level and persist it to users.json."""
        key = str(entity_id)
        if key not in self.users_data["entities"]:
            self.users_data["entities"][key] = {
                "name": name or str(entity_id),
                "level": new_level,
            }
        else:
            self.users_data["entities"][key]["level"] = new_level

        # Mark negative IDs as Special Entities (anonymous / group-level actors)
        if entity_id < 0:
            self.users_data["entities"][key]["special"] = True

        with open(self.users_path, "w") as f:
            json.dump(self.users_data, f, indent=2)
