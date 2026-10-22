from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fiaca.workspace import list_files, read_file, resolve_workspace_path, search_files


class WorkspaceSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "module.py").write_text("SessionStore()\n", encoding="utf-8")
        (self.root / ".env").write_text("SECRET=value\n", encoding="utf-8")
        (self.root / ".git").mkdir()
        (self.root / ".git" / "config").write_text("private", encoding="utf-8")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_lists_only_readable_non_sensitive_files(self) -> None:
        self.assertEqual(list_files(self.root), ["src/module.py"])

    def test_rejects_sensitive_and_external_paths(self) -> None:
        with self.assertRaises(ValueError):
            resolve_workspace_path(self.root, ".env")
        with self.assertRaises(ValueError):
            resolve_workspace_path(self.root, "../outside.txt")

    def test_reads_and_searches_text_files(self) -> None:
        self.assertEqual(read_file(self.root, "src/module.py"), "SessionStore()\n")
        self.assertEqual(
            search_files(self.root, "sessionstore"), [("src/module.py", 1, "SessionStore()")]
        )

    def test_rejects_invalid_regular_expression(self) -> None:
        with self.assertRaises(ValueError):
            search_files(self.root, "[")
