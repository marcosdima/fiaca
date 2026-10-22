from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .workspace import MAX_READ_BYTES, inspect_workspace, read_file


DEFAULT_CONTEXT_FILES = (
    "README.md",
    "pyproject.toml",
    "src/fiaca/cli.py",
    "src/fiaca/ui.py",
    "docs/MESSAGE_PATTERN.md",
)
MAX_CONTEXT_BYTES = 120_000


@dataclass(frozen=True)
class WorkspaceContext:
    workspace: Path
    files: tuple[tuple[str, str], ...]
    summary: str

    @property
    def file_names(self) -> list[str]:
        return [path for path, _ in self.files]

    def as_prompt(self, task: str) -> str:
        sections = [
            "You are analyzing a local software workspace through Fiaca.",
            "This is a read-only task. Do not claim to have changed files or run commands.",
            "Base your answer on the supplied evidence and state uncertainty explicitly.",
            f"Workspace: {self.workspace}",
            f"Workspace summary:\n{self.summary}",
            f"User task:\n{task}",
            "Selected files:",
        ]
        for path, content in self.files:
            sections.append(f"\n--- {path} ---\n{content}")
        return "\n".join(sections)


def build_context(root: Path, task: str, selected_files: list[str] | None = None) -> WorkspaceContext:
    workspace = root.expanduser().resolve()
    report = inspect_workspace(workspace)
    candidates = selected_files or [
        path for path in DEFAULT_CONTEXT_FILES if (workspace / path).is_file()
    ]
    files: list[tuple[str, str]] = []
    total_bytes = 0
    for relative_path in candidates:
        content = read_file(workspace, relative_path)
        size = len(content.encode("utf-8"))
        if size > MAX_READ_BYTES or total_bytes + size > MAX_CONTEXT_BYTES:
            continue
        files.append((relative_path, content))
        total_bytes += size
    if not files:
        raise ValueError("No readable context files were selected.")
    summary = (
        f"Git branch: {report.git_branch or 'none'}\n"
        f"Modified files: {len(report.git_status)}\n"
        f"Detected project files: {', '.join(report.project_files) or 'none'}\n"
        f"Validation commands: {', '.join(report.validation_commands) or 'none'}"
    )
    return WorkspaceContext(workspace, tuple(files), summary)
