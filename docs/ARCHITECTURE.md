# Architecture

## Runtime layers

```text
CLI
 ├─ terminal dashboard
 ├─ chat and task entry points
 └─ read-only workspace commands
        │
        ├─ provider adapter
        ├─ workspace safety and context
        ├─ Rich rendering and terminal input
        └─ SQLite session store
```

## Main modules

- `src/fiaca/cli.py` — command parsing and top-level orchestration.
- `src/fiaca/ui.py` — interactive dashboard and session navigation.
- `src/fiaca/providers.py` — OpenAI-compatible provider requests.
- `src/fiaca/storage.py` — local sessions, messages, actions, and search.
- `src/fiaca/workspace.py` — workspace inspection and safe file operations.
- `src/fiaca/context.py` — bounded context assembly for read-only tasks.
- `src/fiaca/input.py` — multiline terminal input.
- `src/fiaca/rendering.py` — shared Markdown rendering.
- `src/fiaca/config.py` — provider configuration and environment loading.

## Current data flow

1. The CLI or dashboard receives a user request.
2. Configuration selects a provider and model.
3. Chat messages or bounded workspace context are sent to the provider.
4. User and assistant messages are persisted locally.
5. Rich renders the result in the terminal.

## Intended direction

The conversation should become the stable orchestration boundary. Internal
tools should report structured activity to the conversation, while storage
records both the user-visible messages and enough tool metadata to resume or
audit the session.
