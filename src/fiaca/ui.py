from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .providers import provider_names
from .storage import SessionStore
from .tools import execute_tool

console = Console()


def _dashboard() -> None:
    report = execute_tool("inspect_workspace", Path.cwd()).result
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
    paths = execute_tool("list_files", Path.cwd(), limit=limit).result
    console.print(Panel(f"{len(paths)} files shown (limit: {limit})", title="Readable files"))
    for path in paths:
        console.print(f"  [cyan]{path}[/cyan]")


def _read_file() -> None:
    path = console.input("[bold]File path (or blank to cancel): [/bold]").strip()
    if not path:
        return
    content = execute_tool("read_file", Path.cwd(), relative_path=path).result
    if Path(path).suffix.lower() in {".md", ".markdown"}:
        console.print(Panel(Markdown(content), title=path, border_style="green"))
    else:
        console.print(Panel(content, title=path, border_style="green"))


def _search() -> None:
    pattern = console.input("[bold]Search pattern (or blank to cancel): [/bold]").strip()
    if not pattern:
        return
    results = execute_tool("search_files", Path.cwd(), pattern=pattern).result
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
    task_handler: Callable[[str, bool], None] | None = None,
) -> None:
    with SessionStore() as store:
        sessions = store.list_sessions()
    if not sessions:
        console.print("[yellow]No saved sessions.[/yellow]")
        return
    table = Table(title="Saved sessions", expand=True)
    table.add_column("#", justify="right", style="blue", no_wrap=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Updated", no_wrap=True)
    table.add_column("Provider")
    table.add_column("Title")
    for index, session in enumerate(sessions, 1):
        table.add_row(
            str(index), session["id"], session["updated_at"], session["provider"], session["title"]
        )
    console.print(table)
    selection = console.input(
        "\nEnter a session number or ID to open, or press Enter to return: "
    ).strip()
    if not selection:
        return
    if selection.isdigit() and 1 <= int(selection) <= len(sessions):
        session_id = sessions[int(selection) - 1]["id"]
    else:
        session_id = selection
    with SessionStore() as store:
        session = store.get_session(session_id)
        messages = store.get_messages(session_id) if session else []
        actions = store.get_actions(session_id) if session else []
    if session is None:
        raise ValueError(f"Session not found: {session_id}")
    console.print(Panel(session["title"], title=f"Session {session_id}", border_style="cyan"))
    for message in messages:
        console.print(f"\n[bold]{message['role']}[/bold] [dim]{message['created_at']}[/dim]")
        if message["role"] == "assistant":
            console.print(Markdown(message["content"]))
        else:
            console.print(message["content"])
    if actions:
        activity = Table(title="Tool activity", expand=True)
        activity.add_column("Operation", style="cyan")
        activity.add_column("Approved", justify="center")
        activity.add_column("Details")
        for item in actions:
            details = item["details"]
            if len(details) > 100:
                details = details[:97] + "..."
            activity.add_row(
                item["action_type"],
                "yes" if item["approved"] else "no",
                details,
            )
        console.print(activity)
    console.print(
        Panel(
            "Enter c to continue this session.\nEnter b to return to the dashboard.",
            title="Next action",
            border_style="blue",
        )
    )
    action = console.input(Text("\nChoice: ", style="bold")).strip().lower()
    if action == "c":
        chat_handler(session["provider"], session["model"], None, session_id)


def _task(task_handler: Callable[[str, bool], None]) -> None:
    task = console.input("Task (or blank to cancel): ").strip()
    if task:
        task_handler(task, False)


def _cleanup() -> None:
    with SessionStore() as store:
        sessions = store.list_sessions(limit=1_000_000)
        if not sessions:
            console.print("[dim]No saved sessions to clean up.[/dim]")
            return
        console.print(
            Panel(
                f"This permanently deletes {len(sessions)} saved session(s), "
                "including their messages and internal tool history.\n"
                "Provider configuration and API keys are not affected.",
                title="Clear local history",
                border_style="yellow",
            )
        )
        answer = console.input("Type DELETE to continue, or press Enter to cancel: ").strip()
        if answer != "DELETE":
            console.print("[dim]Cleanup cancelled.[/dim]")
            return
        deleted = store.clear_sessions()
    console.print(f"[green]Deleted {deleted} saved session(s) and reclaimed local storage.[/green]")


def run_ui(
    chat_handler: Callable[[str | None, str | None, str | None, str | None], None] | None = None,
    task_handler: Callable[[str, bool], None] | None = None,
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
                    "[7] New read-only task (compatibility)\n"
                    "[8] Clear local history\n"
                    "[r] Refresh             [q] Quit"
                ),
                title="Actions",
                border_style="blue",
            )
        )
        choice = console.input("[bold]Select an action: [/bold]").strip().lower()
        try:
            if choice == "1":
                report = execute_tool("inspect_workspace", Path.cwd()).result
                console.print(
                    Panel("\n".join(report.git_status) or "No modified files", title="Git status")
                )
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
                _sessions(chat_handler, task_handler)
                console.input("\nPress Enter to return...")
            elif choice == "6":
                if chat_handler is None:
                    console.print("[yellow]Chat is not available in this UI context.[/yellow]")
                    console.input("\nPress Enter to return...")
                else:
                    chat_handler(None, None, None, None)
            elif choice == "7":
                if task_handler is None:
                    console.print("[yellow]Tasks are not available in this UI context.[/yellow]")
                    console.input("\nPress Enter to return...")
                else:
                    _task(task_handler)
            elif choice == "8":
                _cleanup()
                console.input("\nPress Enter to return...")
            elif choice in {"q", "quit", "exit"}:
                return
        except httpx.HTTPStatusError as error:
            console.print(
                f"[red]Provider request failed ({error.response.status_code}): "
                f"{error.response.text.strip()}[/red]"
            )
            console.input("\nPress Enter to return...")
        except (OSError, ValueError, httpx.RequestError) as error:
            console.print(f"[red]Error: {error}[/red]")
            console.input("\nPress Enter to return...")
