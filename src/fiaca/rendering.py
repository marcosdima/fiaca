from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown


def print_markdown(content: str, *, title: str | None = None) -> None:
    console = Console()
    if title:
        console.print(f"[bold cyan]{title}[/bold cyan]\n")
    console.print(Markdown(content))
