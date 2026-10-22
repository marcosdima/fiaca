import argparse
import httpx
import os

from .config import load_config, save_config
from .providers import get_provider, provider_names
from .storage import SessionStore


def _chat(provider_name: str | None, model: str | None, prompt: str | None) -> None:
    provider = get_provider(provider_name)
    workspace = os.getcwd()
    with SessionStore() as store:
        session_id = store.create_session(
            workspace, provider.name, model or provider.default_model, prompt or "Interactive chat"
        )
        print(f"Session: {session_id}")
        messages: list[dict[str, str]] = []
        if prompt:
            messages.append({"role": "user", "content": prompt})
            store.add_message(session_id, "user", prompt)
        else:
            print(f"Connected to {provider.name}. Type /exit to quit.")
        while True:
            if not prompt:
                try:
                    prompt = input("\nyou> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    return
            if prompt in {"/exit", "/quit"}:
                return
            if prompt:
                messages.append({"role": "user", "content": prompt})
                store.add_message(session_id, "user", prompt)
                answer = provider.complete(messages, model=model)
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

    sub.add_parser("providers", help="List configured providers")
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
            _chat(args.provider, args.model, " ".join(args.message) or None)
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
        parser.print_help()