from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fiaca.storage import SessionStore


class SessionStoreTests(unittest.TestCase):
    def test_persists_ordered_tool_activity_and_approval(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            SessionStore(Path(directory) / "sessions.db") as store,
        ):
            session_id = store.create_session("/workspace", "local", "model", "Task")
            store.add_action(
                session_id,
                "tool_completed",
                json.dumps({"tool": "read_file", "read_only": True}),
            )
            store.add_action(
                session_id,
                "context_approved",
                json.dumps({"files": ["README.md"]}),
                approved=True,
            )
            actions = store.get_actions(session_id)

        self.assertEqual(
            [action["action_type"] for action in actions],
            [
                "tool_completed",
                "context_approved",
            ],
        )
        self.assertEqual(actions[1]["approved"], 1)
        self.assertEqual(json.loads(actions[0]["details"])["read_only"], True)
