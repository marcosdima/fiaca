from __future__ import annotations

from pathlib import Path
from collections.abc import Callable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import load_config
from .providers import provider_names
from .storage import SessionStore
from .workspace import inspect_workspace, list_files, read_file, search_files


console = Console()


def _dashboard() -> None:
    report = inspect_workspace()
    config = load_config()
    with SessionStore() as store:
        sessions = store.list_sessions(limit=5)

    overview = Table.grid(padding=(0, 2))
    overview.add_row("Workspace", str(report.root))
    overview.add_row("Git branch", report.git_branch or "not a Git repository")
    overview.add_row("Modified files", str(len(report.git_status)))
    overview.add_row("Providers", ", ".join(provider_names()) or "none configured")
    overview.add_row("Saved sessions", str(len(sessions)))
    console.print(Panel(overview, title="Fiaca workspace", border_style="cyan"))

    if sessions:
        table = Table(title="Recent sessions", expand=True)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Updated", no_wrap=True)
        table.add_column("Title")
        for session in sessions:
            table.add_row(session["id"], session["updated_at"], session["title"])
        console.print(table)


def _show_files() -> None:
    limit = 100
    paths = list_files(Path.cwd(), limit=limit)
    console.print(Panel(f"{len(paths)} files shown (limit: {limit})", title="Readable files"))
    for path in paths:
        console.print(f"  [cyan]{path}[/cyan]")


def _read_file() -> None:
    path = console.input("[bold]File path (or blank to cancel): [/bold]").strip()
    if not path:
        return
    content = read_file(Path.cwd(), path)
    console.print(Panel(content, title=path, border_style="green"))


def _search() -> None:
    pattern = console.input("[bold]Search pattern (or blank to cancel): [/bold]").strip()
    if not pattern:
        return
    results = search_files(Path.cwd(), pattern)
    if not results:
        console.print("[yellow]No matches found.[/yellow]")
        return
    table = Table(title=f"Matches for {pattern!r}", expand=True)
    table.add_column("File", style="cyan")
    table.add_column("Line", justify="right")
    table.add_column("Text")
    for path, line_number, line in results:
        table.add_row(path, str(line_number), line)
    console.print(table)


def _sessions(
    chat_handler: Callable[[str | None, str | None, str | None, str | None], None],
) -> None:
    with SessionStore() as store:
        sessions = store.list_sessions()
    if not sessions:
        console.print("[yellow]No saved sessions.[/yellow]")
        return
    table = Table(title="Saved sessions", expand=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Updated", no_wrap=True)
    table.add_column("Provider")
    table.add_column("Title")
    for session in sessions:
        table.add_row(
            session["id"], session["updated_at"], session["provider"], session["title"]
        )
    console.print(table)
    session_id = console.input(
        "\nEnter a session ID to open, or press Enter to return: "
    ).strip()
    if not session_id:
        return
    with SessionStore() as store:
        session = store.get_session(session_id)
        messages = store.get_messages(session_id) if session else []
    if session is None:
        raise ValueError(f"Session not found: {session_id}")
    history = "\n\n".join(
        f"[{message['role']}] {message['content']}" for message in messages
    )
    console.print(Panel(history or "No messages in this session.", title=session["title"]))
    action = console.input("\n[c] Continue  [b] Back: ").strip().lower()
    if action == "c":
        chat_handler(session["provider"], session["model"], None, session_id)


def run_ui(
    chat_handler: Callable[
        [str | None, str | None, str | None, str | None], None
    ]
    | None = None,
) -> None:
    """Run the interactive terminal dashboard."""
    while True:
        console.clear()
        console.print(
            Text("FIACA", style="bold bright_cyan", justify="center"),
            Text("Workspace assistant", style="dim", justify="center"),
        )
        _dashboard()
        console.print(
            Panel(
                Text(
                    "[1] Inspect workspace   [2] List files   [3] Read file\n"
                    "[4] Search files        [5] Sessions      [6] Chat\n"
                    "[r] Refresh             [q] Quit"
                ),
                title="Actions",
                border_style="blue",
            )
        )
        choice = console.input("[bold]Select an action: [/bold]").strip().lower()
        try:
            if choice == "1":
                report = inspect_workspace()
                console.print(Panel("\n".join(report.git_status) or "No modified files", title="Git status"))
                console.input("\nPress Enter to return...")
            elif choice == "2":
                _show_files()
                console.input("\nPress Enter to return...")
            elif choice == "3":
                _read_file()
                console.input("\nPress Enter to return...")
            elif choice == "4":
                _search()
                console.input("\nPress Enter to return...")
            elif choice == "5":
                _sessions(chat_handler)
                console.input("\nPress Enter to return...")
            elif choice == "6":
                if chat_handler is None:
                    console.print("[yellow]Chat is not available in this UI context.[/yellow]")
                    console.input("\nPress Enter to return...")
                else:
                    chat_handler(None, None, None, None)
            elif choice in {"q", "quit", "exit"}:
                return
        except (OSError, ValueError) as error:
            console.print(f"[red]Error: {error}[/red]")
            console.input("\nPress Enter to return...")
