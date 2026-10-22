import argparse
import json
import os
import sys
from pathlib import Path

import httpx

from .config import load_config, save_config
from .input import create_prompt_session, read_message
from .providers import get_provider, provider_names
from .rendering import print_markdown
from .storage import SessionStore
from .tools import execute_tool
from .ui import run_ui


def _chat(
    provider_name: str | None,
    model: str | None,
    prompt: str | None,
    session_id: str | None = None,
) -> None:
    if session_id and not provider_name:
        with SessionStore() as store:
            session = store.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        provider_name = session["provider"]
        model = model or session["model"]
    provider = get_provider(provider_name)
    workspace = os.getcwd()
    with SessionStore() as store:
        if session_id:
            session = store.get_session(session_id)
            if session is None:
                raise ValueError(f"Session not found: {session_id}")
            messages = [
                {"role": message["role"], "content": message["content"]}
                for message in store.get_messages(session_id)
                if message["role"] in {"user", "assistant"}
            ]
            print(f"Resuming session: {session_id}")
        else:
            session_id = store.create_session(
                workspace,
                provider.name,
                model or provider.default_model,
                prompt or "Interactive chat",
            )
            messages = []
            print(f"Session: {session_id}")
        if not prompt:
            print(f"Connected to {provider.name}. Type /exit to quit.")
        prompt_session = create_prompt_session()
        while True:
            if not prompt:
                prompt = read_message(prompt_session)
                if prompt is None:
                    print()
                    continue
            if prompt in {"/exit", "/quit"}:
                return
            if prompt.startswith("/"):
                try:
                    handled = _chat_tool_command(prompt, session_id, provider.name, model)
                except (ValueError, OSError) as error:
                    print(f"Tool failed: {error}", file=sys.stderr)
                    handled = True
                if handled:
                    if prompt.startswith("/task "):
                        with SessionStore() as refreshed_store:
                            messages = [
                                {"role": message["role"], "content": message["content"]}
                                for message in refreshed_store.get_messages(session_id)
                                if message["role"] in {"user", "assistant"}
                            ]
                    prompt = None
                    continue
            if prompt:
                messages.append({"role": "user", "content": prompt})
                store.add_message(session_id, "user", prompt)
                print("Sending...", flush=True)
                try:
                    answer = provider.complete(messages, model=model)
                except httpx.TimeoutException:
                    print(
                        "The provider request timed out. Check the model availability "
                        "or try again.",
                        file=sys.stderr,
                    )
                    prompt = None
                    continue
                except httpx.RequestError as error:
                    print(f"Provider connection failed: {error}", file=sys.stderr)
                    prompt = None
                    continue
                messages.append({"role": "assistant", "content": answer})
                store.add_message(session_id, "assistant", answer)
                print()
                print_markdown(answer, title="ai")
            prompt = None


def _chat_tool_command(prompt: str, session_id: str, provider_name: str, model: str | None) -> bool:
    """Run an explicit read-only tool command from an interactive chat."""
    command, _, argument = prompt.partition(" ")
    root = Path.cwd()
    if command == "/help":
        print("Read-only tools: /inspect, /files, /read <path>, /find <regex>, /task <request>")
        print("Conversation: /exit or /quit")
        return True
    if command == "/inspect":
        result = execute_tool("inspect_workspace", root).result
        print(f"Workspace: {result.root}")
        print(f"Git branch: {result.git_branch or 'not a Git repository'}")
        print(f"Modified files: {len(result.git_status)}")
        print(f"Validation commands: {', '.join(result.validation_commands) or 'none'}")
        with SessionStore() as store:
            store.add_action(
                session_id,
                "tool_completed",
                json.dumps({"tool": "inspect_workspace", "scope": str(root), "read_only": True}),
            )
        return True
    if command == "/files":
        limit = int(argument) if argument.isdigit() else 50
        paths = execute_tool("list_files", root, limit=limit).result
        print(f"Readable files ({len(paths)} shown):")
        print("\n".join(f"- {path}" for path in paths))
        with SessionStore() as store:
            store.add_action(
                session_id,
                "tool_completed",
                json.dumps(
                    {"tool": "list_files", "scope": str(root), "read_only": True, "limit": limit}
                ),
            )
        return True
    if command == "/read":
        if not argument.strip():
            raise ValueError("Usage: /read <workspace-relative-path>")
        content = execute_tool("read_file", root, relative_path=argument.strip()).result
        print(f"--- {argument.strip()} ---\n{content}", end="" if content.endswith("\n") else "\n")
        with SessionStore() as store:
            store.add_action(
                session_id,
                "tool_completed",
                json.dumps(
                    {
                        "tool": "read_file",
                        "scope": str(root),
                        "read_only": True,
                        "file": argument.strip(),
                    }
                ),
            )
        return True
    if command == "/find":
        if not argument.strip():
            raise ValueError("Usage: /find <regular-expression>")
        results = execute_tool("search_files", root, pattern=argument.strip()).result
        print(f"Matches ({len(results)} shown):")
        for path, line_number, line in results:
            print(f"{path}:{line_number}:{line}")
        with SessionStore() as store:
            store.add_action(
                session_id,
                "tool_completed",
                json.dumps(
                    {
                        "tool": "search_files",
                        "scope": str(root),
                        "read_only": True,
                        "pattern": argument.strip(),
                        "matches": len(results),
                    }
                ),
            )
        return True
    if command == "/task":
        if not argument.strip():
            raise ValueError("Usage: /task <read-only request>")
        _task(provider_name, model, argument.strip(), None, session_id=session_id)
        return True
    print(f"Unknown chat command: {command}. Type /help for available tools.")
    return True


def _task(
    provider_name: str | None,
    model: str | None,
    task: str,
    selected_files: list[str] | None,
    approved: bool = False,
    session_id: str | None = None,
    planning: bool = False,
) -> None:
    resuming_task = session_id is not None and not task
    if resuming_task:
        with SessionStore() as store:
            session = store.get_session(session_id)
            actions = store.get_actions(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        context_action = next(
            (action for action in actions if action["action_type"] == "context_built"),
            None,
        )
        if context_action is None:
            raise ValueError(f"Session is not a read-only task: {session_id}")
        details = json.loads(context_action["details"])
        task = str(details["task"])
        selected_files = list(details["files"])
        planning = bool(details.get("planning", False))
        provider_name = session["provider"]
        model = model or session["model"]
        approved = True
    if not task:
        raise ValueError("A task message is required unless --session is provided.")
    provider = get_provider(provider_name)
    workspace = Path.cwd()
    context = execute_tool(
        "build_context", workspace, task=task, selected_files=selected_files
    ).result
    print("Read-only implementation plan" if planning else "Read-only task")
    print(f"Workspace: {context.workspace}")
    print("Selected files:")
    for path in context.file_names:
        print(f"  - {path}")
    if not approved and input("Send this context to the provider? [y/N] ").lower() != "y":
        print("Context approval declined.")
        print("Task cancelled.")
        return
    with SessionStore() as store:
        if not session_id:
            session_id = store.create_session(
                str(context.workspace), provider.name, model or provider.default_model, task
            )
            details = json.dumps(
                {
                    "task": task,
                    "files": context.file_names,
                    "mode": "planning" if planning else "read-only",
                    "planning": planning,
                }
            )
            store.add_action(session_id, "context_built", details)
            store.add_message(session_id, "user", task)
        else:
            if resuming_task:
                store.add_action(
                    session_id, "task_resumed", json.dumps({"files": context.file_names})
                )
            else:
                details = json.dumps(
                    {
                        "task": task,
                        "files": context.file_names,
                        "mode": "planning" if planning else "read-only",
                        "planning": planning,
                    }
                )
                store.add_action(session_id, "context_built", details)
                store.add_message(session_id, "user", task)
        store.add_action(
            session_id,
            "tool_completed",
            json.dumps(
                {
                    "tool": "build_context",
                    "scope": str(context.workspace),
                    "read_only": True,
                    "files": context.file_names,
                    "bytes": sum(len(content.encode("utf-8")) for _, content in context.files),
                }
            ),
        )
        store.add_action(
            session_id,
            "context_approved",
            json.dumps({"files": context.file_names, "explicit": not approved}),
            approved=True,
        )
        store.add_action(
            session_id,
            "provider_request_started",
            json.dumps({"provider": provider.name, "model": model or provider.default_model}),
            approved=True,
        )
        print(f"Session: {session_id}\nSending...")
        try:
            answer = provider.complete(
                [{"role": "user", "content": context.as_prompt(task, planning)}], model=model
            )
        except httpx.TimeoutException as error:
            store.add_action(
                session_id,
                "provider_request_failed",
                json.dumps({"error": "timeout", "message": str(error)}),
                approved=True,
            )
            raise ValueError("The provider request timed out. The session was saved.") from error
        except httpx.RequestError as error:
            store.add_action(
                session_id,
                "provider_request_failed",
                json.dumps({"error": "connection", "message": str(error)}),
                approved=True,
            )
            raise ValueError(f"Provider connection failed: {error}") from error
        store.add_message(session_id, "assistant", answer)
        store.add_action(
            session_id,
            "provider_request_completed",
            json.dumps({"provider": provider.name, "model": model or provider.default_model}),
            approved=True,
        )
    print()
    print_markdown(answer, title="ai")


def main() -> None:
    """Run the provider-neutral terminal client."""
    parser = argparse.ArgumentParser(prog="fiaca")
    sub = parser.add_subparsers(dest="command")

    chat_p = sub.add_parser("chat", help="Send a message to the AI model")
    chat_p.add_argument("message", nargs="*", help="Message to send, or omit for interactive mode")
    chat_p.add_argument("--provider", help="Configured provider name")
    chat_p.add_argument("--model", help="Model identifier")
    chat_p.add_argument("--session", help="Resume a saved session")
    task_p = sub.add_parser("task", help="Run a read-only task with workspace context")
    task_p.add_argument("message", nargs="*", help="Task to send to the AI")
    task_p.add_argument("--file", action="append", dest="files", help="File to include")
    task_p.add_argument("--provider", help="Configured provider name")
    task_p.add_argument("--model", help="Model identifier")
    task_p.add_argument("--yes", action="store_true", help="Skip context approval")
    task_p.add_argument("--session", help="Resume a saved read-only task")
    task_p.add_argument(
        "--plan",
        action="store_true",
        help="Request a concrete implementation plan without modifying files",
    )

    sub.add_parser("providers", help="List configured providers")
    sub.add_parser("ui", help="Open the interactive terminal dashboard")
    sub.add_parser("inspect", help="Inspect the current workspace")
    sub.add_parser("doctor", help="Check workspace and project validation details")
    files_p = sub.add_parser("files", help="List readable files in the current workspace")
    files_p.add_argument("--limit", type=int, default=200)
    read_p = sub.add_parser("read", help="Read a text file in the current workspace")
    read_p.add_argument("path")
    read_p.add_argument("--markdown", action="store_true", help="Render the file as Markdown")
    find_p = sub.add_parser("find", help="Search readable text files in the current workspace")
    find_p.add_argument("pattern")
    find_p.add_argument("--limit", type=int, default=50)
    sub.add_parser("sessions", help="List saved chat sessions")
    history_p = sub.add_parser("history", help="Show messages from a saved session")
    history_p.add_argument("session_id")
    search_p = sub.add_parser("search", help="Search saved messages")
    search_p.add_argument("query")
    cleanup_p = sub.add_parser(
        "cleanup", help="Delete all local sessions and reclaim their storage"
    )
    cleanup_p.add_argument("--yes", action="store_true", help="Skip the confirmation prompt")
    config_p = sub.add_parser("config", help="Create or update the configuration")
    config_p.add_argument("--provider", default="openrouter")
    config_p.add_argument("--model", default="openrouter/free")
    config_p.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    config_p.add_argument("--base-url", default="https://openrouter.ai/api/v1")

    args = parser.parse_args()

    if args.command == "chat":
        try:
            _chat(args.provider, args.model, " ".join(args.message) or None, args.session)
        except httpx.HTTPStatusError as error:
            detail = error.response.text.strip()
            message = f"Provider request failed ({error.response.status_code})"
            if detail:
                message += f": {detail}"
            parser.error(message)
        except (ValueError, OSError, httpx.RequestError) as error:
            parser.error(str(error))
    elif args.command == "task":
        try:
            _task(
                args.provider,
                args.model,
                " ".join(args.message),
                args.files,
                args.yes,
                args.session,
                args.plan,
            )
        except httpx.HTTPStatusError as error:
            parser.error(
                f"Provider request failed ({error.response.status_code}): {error.response.text}"
            )
        except (ValueError, OSError) as error:
            parser.error(str(error))
    elif args.command == "providers":
        names = provider_names()
        print("\n".join(names) if names else "No providers configured.")
    elif args.command == "ui":
        run_ui(
            _chat,
            lambda value, resume: _task(
                None,
                None,
                "" if resume else value,
                None,
                resume,
                value if resume else None,
            ),
        )
    elif args.command in {"inspect", "doctor"}:
        report = execute_tool("inspect_workspace", Path.cwd()).result
        print(f"Workspace: {report.root}")
        print(f"Git branch: {report.git_branch or 'not a Git repository'}")
        print(f"Project files: {', '.join(report.project_files) or 'none detected'}")
        print(f"Modified files: {len(report.git_status)}")
        if args.command == "inspect" and report.git_status:
            print("\nGit status:")
            print("\n".join(report.git_status))
        print("\nValidation commands:")
        if report.validation_commands:
            print("\n".join(f"- {command}" for command in report.validation_commands))
        else:
            print("No validation commands detected.")
    elif args.command == "files":
        for path in execute_tool("list_files", Path.cwd(), limit=args.limit).result:
            print(path)
    elif args.command == "read":
        content = execute_tool("read_file", Path.cwd(), relative_path=args.path).result
        if args.markdown or Path(args.path).suffix.lower() in {".md", ".markdown"}:
            print_markdown(content, title=args.path)
        else:
            print(content, end="")
    elif args.command == "find":
        results = execute_tool(
            "search_files", Path.cwd(), pattern=args.pattern, limit=args.limit
        ).result
        for path, line_number, line in results:
            print(f"{path}:{line_number}:{line}")
    elif args.command == "sessions":
        with SessionStore() as store:
            for session in store.list_sessions():
                print(
                    f"{session['id']}  {session['updated_at']}  "
                    f"{session['title']}  [{session['workspace']}]"
                )
    elif args.command == "history":
        with SessionStore() as store:
            messages = store.get_messages(args.session_id)
        if not messages:
            parser.error(f"Session not found or contains no messages: {args.session_id}")
        for message in messages:
            print(f"\n[{message['role']}] {message['created_at']}")
            if message["role"] == "assistant":
                print_markdown(message["content"])
            else:
                print(message["content"])
    elif args.command == "search":
        with SessionStore() as store:
            results = store.search(args.query)
        for result in results:
            excerpt = " ".join(result["content"].split())
            print(f"{result['session_id']}  [{result['role']}]  {excerpt}")
    elif args.command == "cleanup":
        with SessionStore() as store:
            sessions = store.list_sessions(limit=1_000_000)
            if not args.yes:
                answer = (
                    input(
                        f"This will permanently delete {len(sessions)} saved session(s). "
                        "Continue? [y/N] "
                    )
                    .strip()
                    .lower()
                )
                if answer != "y":
                    print("Cleanup cancelled.")
                    return
            deleted = store.clear_sessions()
        print(f"Deleted {deleted} saved session(s) and reclaimed local storage.")
    elif args.command == "config":
        config = load_config()
        providers = config.setdefault("providers", {})
        providers[args.provider] = {
            "api_key_env": args.api_key_env,
            "base_url": args.base_url,
            "default_model": args.model,
        }
        config["provider"] = args.provider
        save_config(config)
        print(f"Configuration saved to ~/.fiaca.yml for '{args.provider}'.")
    else:
        run_ui(
            _chat,
            lambda value, resume: _task(
                None, None, "" if resume else value, None, True, value if resume else None
            ),
        )
