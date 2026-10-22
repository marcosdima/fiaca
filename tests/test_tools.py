from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fiaca.tools import execute_tool, get_tool


class ReadOnlyToolTests(unittest.TestCase):
    def test_registry_exposes_safe_workspace_operations(self) -> None:
        self.assertEqual(
            {"inspect_workspace", "list_files", "read_file", "search_files", "build_context"},
            set(
                name
                for name in (
                    "inspect_workspace",
                    "list_files",
                    "read_file",
                    "search_files",
                    "build_context",
                )
                if get_tool(name).name == name
            ),
        )

    def test_tool_result_identifies_scope_and_safety(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Fiaca\n", encoding="utf-8")
            result = execute_tool("read_file", root, relative_path="README.md")

        self.assertEqual(result.tool_name, "read_file")
        self.assertEqual(result.scope, str(root.resolve()))
        self.assertTrue(result.read_only)
        self.assertEqual(result.result, "# Fiaca\n")

    def test_unknown_tool_is_explicitly_rejected(self) -> None:
        with self.assertRaises(ValueError):
            get_tool("apply_patch")
