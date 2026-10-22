from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
import re


IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".fiaca",
}
SENSITIVE_NAMES = {".env", ".env.local", "id_rsa", "id_ed25519"}
MAX_READ_BYTES = 256 * 1024
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


def resolve_workspace_path(root: Path, relative_path: str) -> Path:
    workspace = root.expanduser().resolve()
    candidate = (workspace / relative_path).resolve()
    if candidate != workspace and workspace not in candidate.parents:
        raise ValueError(f"Path is outside the workspace: {relative_path}")
    if candidate.name in SENSITIVE_NAMES:
        raise ValueError(f"Sensitive file access is not allowed: {relative_path}")
    if any(part in IGNORED_DIRECTORIES for part in candidate.relative_to(workspace).parts):
        raise ValueError(f"Access to ignored workspace paths is not allowed: {relative_path}")
    return candidate


def list_files(root: Path, limit: int = 200) -> list[str]:
    workspace = root.expanduser().resolve()
    paths: list[str] = []
    for path in sorted(workspace.rglob("*")):
        relative = path.relative_to(workspace)
        if path.is_file() and not any(part in IGNORED_DIRECTORIES for part in relative.parts):
            if path.name not in SENSITIVE_NAMES:
                paths.append(relative.as_posix())
        if len(paths) >= limit:
            break
    return paths


def read_file(root: Path, relative_path: str) -> str:
    path = resolve_workspace_path(root, relative_path)
    if not path.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    if path.stat().st_size > MAX_READ_BYTES:
        raise ValueError(f"File is larger than the {MAX_READ_BYTES} byte read limit: {relative_path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"File is not valid UTF-8 text: {relative_path}") from error


def search_files(root: Path, pattern: str, limit: int = 50) -> list[tuple[str, int, str]]:
    try:
        expression = re.compile(pattern, re.IGNORECASE)
    except re.error as error:
        raise ValueError(f"Invalid regular expression: {error}") from error
    results: list[tuple[str, int, str]] = []
    for relative in list_files(root, limit=1000):
        try:
            content = read_file(root, relative)
        except ValueError:
            continue
        for line_number, line in enumerate(content.splitlines(), 1):
            if expression.search(line):
                results.append((relative, line_number, line.strip()))
                if len(results) >= limit:
                    return results
    return results
