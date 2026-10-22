from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class SessionStore:
    """Persist local sessions, messages, and tool activity in SQLite."""

    def __init__(self, path: Path | None = None) -> None:
        data_dir = Path(os.environ.get("FIACA_DATA_DIR", "~/.fiaca")).expanduser()
        self.path = path or data_dir / "sessions.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._initialize()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                workspace TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'tool')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                content,
                session_id UNINDEXED,
                message_id UNINDEXED
            );
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                action_type TEXT NOT NULL,
                details TEXT NOT NULL,
                approved INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def create_session(
        self, workspace: str, provider: str, model: str | None, title: str
    ) -> str:
        session_id = uuid.uuid4().hex[:12]
        timestamp = _now()
        self.connection.execute(
            """
            INSERT INTO sessions (id, workspace, provider, model, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, workspace, provider, model, title, timestamp, timestamp),
        )
        self.connection.commit()
        return session_id

    def add_message(self, session_id: str, role: str, content: str) -> int:
        timestamp = _now()
        cursor = self.connection.execute(
            """
            INSERT INTO messages (session_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, role, content, timestamp),
        )
        message_id = int(cursor.lastrowid)
        self.connection.execute(
            "INSERT INTO messages_fts (content, session_id, message_id) VALUES (?, ?, ?)",
            (content, session_id, str(message_id)),
        )
        self.connection.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?", (timestamp, session_id)
        )
        self.connection.commit()
        return message_id

    def add_action(
        self, session_id: str, action_type: str, details: str, approved: bool = False
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO actions (session_id, action_type, details, approved, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, action_type, details, int(approved), _now()),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def get_actions(self, session_id: str) -> list[sqlite3.Row]:
        cursor = self.connection.execute(
            """
            SELECT action_type, details, approved, created_at FROM actions
            WHERE session_id = ? ORDER BY id
            """,
            (session_id,),
        )
        return list(cursor.fetchall())

    def list_sessions(self, limit: int = 20) -> list[sqlite3.Row]:
        cursor = self.connection.execute(
            """
            SELECT id, title, workspace, provider, model, created_at, updated_at
            FROM sessions ORDER BY updated_at DESC LIMIT ?
            """,
            (limit,),
        )
        return list(cursor.fetchall())

    def get_messages(self, session_id: str) -> list[sqlite3.Row]:
        cursor = self.connection.execute(
            """
            SELECT role, content, created_at FROM messages
            WHERE session_id = ? ORDER BY id
            """,
            (session_id,),
        )
        return list(cursor.fetchall())

    def get_session(self, session_id: str) -> sqlite3.Row | None:
        cursor = self.connection.execute(
            """
            SELECT id, title, workspace, provider, model, created_at, updated_at
            FROM sessions WHERE id = ?
            """,
            (session_id,),
        )
        return cursor.fetchone()

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        cursor = self.connection.execute(
            """
            SELECT messages.session_id, messages.role, messages.content,
                   messages.created_at, sessions.title
            FROM messages_fts
            JOIN messages ON messages.id = CAST(messages_fts.message_id AS INTEGER)
            JOIN sessions ON sessions.id = messages.session_id
            WHERE messages_fts MATCH ?
            ORDER BY messages.created_at DESC LIMIT ?
            """,
            (query, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> SessionStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
