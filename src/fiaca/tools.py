from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .context import WorkspaceContext, build_context
from .workspace import inspect_workspace, list_files, read_file, search_files


@dataclass(frozen=True)
class ToolResult:
    """A user-visible result from a safe workspace operation."""

    tool_name: str
    scope: str
    read_only: bool
    result: Any


ToolHandler = Callable[..., Any]


@dataclass(frozen=True)
class ReadOnlyTool:
    name: str
    description: str
    handler: ToolHandler

    def execute(self, root: Path, **arguments: Any) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            scope=str(root.expanduser().resolve()),
            read_only=True,
            result=self.handler(root, **arguments),
        )


def _build_context(root: Path, **arguments: Any) -> WorkspaceContext:
    task = arguments.get("task")
    if not isinstance(task, str) or not task.strip():
        raise ValueError("The context tool requires a non-empty task.")
    selected_files = arguments.get("selected_files")
    if selected_files is not None and not isinstance(selected_files, list):
        raise ValueError("selected_files must be a list of workspace-relative paths.")
    return build_context(root, task, selected_files)


READ_ONLY_TOOLS: dict[str, ReadOnlyTool] = {
    "inspect_workspace": ReadOnlyTool(
        "inspect_workspace", "Inspect Git and project validation details.", inspect_workspace
    ),
    "list_files": ReadOnlyTool(
        "list_files", "List readable files inside the workspace.", list_files
    ),
    "read_file": ReadOnlyTool("read_file", "Read one bounded UTF-8 text file.", read_file),
    "search_files": ReadOnlyTool(
        "search_files", "Search readable text files with a regular expression.", search_files
    ),
    "build_context": ReadOnlyTool(
        "build_context", "Build bounded context for an approved provider request.", _build_context
    ),
}


def get_tool(name: str) -> ReadOnlyTool:
    try:
        return READ_ONLY_TOOLS[name]
    except KeyError as error:
        raise ValueError(f"Unknown workspace tool: {name}") from error


def execute_tool(name: str, root: Path, **arguments: Any) -> ToolResult:
    return get_tool(name).execute(root, **arguments)
