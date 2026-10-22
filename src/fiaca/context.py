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
STRUCTURED_TASK_INSTRUCTIONS = """Respond using this exact structure:

Understanding:
  Restate the requested outcome and important boundaries.

Evidence:
  List observed facts from the supplied files. Cite concrete file paths and
  symbols or line areas when possible. Separate facts from assumptions.

Plan:
  Give the smallest prioritized and ordered plan. Do not implement it.

Files to change:
  List likely files and explain why. If no changes are requested, say
  "None - analysis only."

Risks:
  State compatibility, safety, uncertainty, and scope risks.

Validation:
  Describe how the proposal would be verified. Do not run commands.

Recommendations:
  Give the final prioritized recommendations and relevant trade-offs.

Rules:
- This is read-only analysis. Do not claim to have modified files or run commands.
- Base conclusions on the supplied evidence.
- Do not invent files, symbols, test results, or capabilities.
- Keep observed facts, assumptions, and recommendations distinct.
- Prefer concrete, actionable details over generic advice.
"""


@dataclass(frozen=True)
class WorkspaceContext:
    workspace: Path
    files: tuple[tuple[str, str], ...]
    summary: str

    @property
    def file_names(self) -> list[str]:
        return [path for path, _ in self.files]

    def as_prompt(self, task: str, planning: bool = False) -> str:
        instructions = STRUCTURED_TASK_INSTRUCTIONS
        if planning:
            instructions += """

Planning mode:
- Produce an implementation proposal, not a general design discussion.
- Identify the smallest concrete set of file changes.
- Describe the intended edits by file and symbol without writing a patch yet.
- Include a clear approval boundary: no files may be modified in this task.
"""
        sections = [
            "You are analyzing a local software workspace through Fiaca.",
            "This is a read-only task. Do not claim to have changed files or run commands.",
            "Base your answer on the supplied evidence and state uncertainty explicitly.",
            instructions,
            f"Workspace: {self.workspace}",
            f"Workspace summary:\n{self.summary}",
            f"User task:\n{task}",
            "Selected files:",
        ]
        for path, content in self.files:
            sections.append(f"\n--- {path} ---\n{content}")
        return "\n".join(sections)


def build_context(
    root: Path, task: str, selected_files: list[str] | None = None
) -> WorkspaceContext:
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
