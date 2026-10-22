from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".fiaca",
}
PROJECT_FILES = (
    "README.md",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "Makefile",
)


@dataclass(frozen=True)
class WorkspaceReport:
    root: Path
    git_branch: str | None
    git_status: list[str]
    project_files: list[str]
    validation_commands: list[str]


def _git(root: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip()


def _project_files(root: Path) -> list[str]:
    return [name for name in PROJECT_FILES if (root / name).is_file()]


def _validation_commands(root: Path, project_files: list[str]) -> list[str]:
    commands: list[str] = []
    if "pyproject.toml" in project_files:
        if (root / "uv.lock").is_file():
            commands.append("uv run pytest")
            commands.append("uv run python -m compileall -q src")
        else:
            commands.append("python -m pytest")
    if "package.json" in project_files:
        commands.append("npm test")
    if "Cargo.toml" in project_files:
        commands.append("cargo test")
    if "go.mod" in project_files:
        commands.append("go test ./...")
    if "Makefile" in project_files:
        commands.append("make test")
    return list(dict.fromkeys(commands))


def inspect_workspace(root: Path | None = None) -> WorkspaceReport:
    workspace = (root or Path.cwd()).expanduser().resolve()
    if not workspace.is_dir():
        raise ValueError(f"Workspace directory does not exist: {workspace}")
    project_files = _project_files(workspace)
    branch = _git(workspace, "branch", "--show-current")
    status_output = _git(workspace, "status", "--short")
    return WorkspaceReport(
        root=workspace,
        git_branch=branch or None,
        git_status=status_output.splitlines() if status_output else [],
        project_files=project_files,
        validation_commands=_validation_commands(workspace, project_files),
    )
