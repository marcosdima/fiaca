import argparse
import httpx
import os
import sys
from pathlib import Path

from .config import load_config, save_config
from .input import create_prompt_session, read_message
from .providers import get_provider, provider_names
from .storage import SessionStore
from .ui import run_ui
from .workspace import inspect_workspace, list_files, read_file, search_files


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
        if prompt:
            messages.append({"role": "user", "content": prompt})
            store.add_message(session_id, "user", prompt)
        else:
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
                print(f"\nai> {answer}")
            prompt = None


def main() -> None:
    """Run the provider-neutral terminal client."""
    parser = argparse.ArgumentParser(prog="fiaca")
    sub = parser.add_subparsers(dest="command")

    chat_p = sub.add_parser("chat", help="Send a message to the AI model")
    chat_p.add_argument("message", nargs="*", help="Message to send, or omit for interactive mode")
    chat_p.add_argument("--provider", help="Configured provider name")
    chat_p.add_argument("--model", help="Model identifier")
    chat_p.add_argument("--session", help="Resume a saved session")

    sub.add_parser("providers", help="List configured providers")
    sub.add_parser("ui", help="Open the interactive terminal dashboard")
    sub.add_parser("inspect", help="Inspect the current workspace")
    sub.add_parser("doctor", help="Check workspace and project validation details")
    files_p = sub.add_parser("files", help="List readable files in the current workspace")
    files_p.add_argument("--limit", type=int, default=200)
    read_p = sub.add_parser("read", help="Read a text file in the current workspace")
    read_p.add_argument("path")
    find_p = sub.add_parser("find", help="Search readable text files in the current workspace")
    find_p.add_argument("pattern")
    find_p.add_argument("--limit", type=int, default=50)
    sub.add_parser("sessions", help="List saved chat sessions")
    history_p = sub.add_parser("history", help="Show messages from a saved session")
    history_p.add_argument("session_id")
    search_p = sub.add_parser("search", help="Search saved messages")
    search_p.add_argument("query")
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
    elif args.command == "providers":
        names = provider_names()
        print("\n".join(names) if names else "No providers configured.")
    elif args.command == "ui":
        run_ui(_chat)
    elif args.command in {"inspect", "doctor"}:
        report = inspect_workspace()
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
        for path in list_files(Path.cwd(), limit=args.limit):
            print(path)
    elif args.command == "read":
        print(read_file(Path.cwd(), args.path), end="")
    elif args.command == "find":
        for path, line_number, line in search_files(Path.cwd(), args.pattern, limit=args.limit):
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
            print(f"\n[{message['role']}] {message['created_at']}\n{message['content']}")
    elif args.command == "search":
        with SessionStore() as store:
            results = store.search(args.query)
        for result in results:
            excerpt = " ".join(result["content"].split())
            print(f"{result['session_id']}  [{result['role']}]  {excerpt}")
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
        run_ui(_chat)