# User guide

## Start Fiaca

From a project directory:

```bash
uv run fiaca
```

This opens the terminal dashboard. `uv run fiaca ui` is equivalent.

The focused user flow is:

1. Start a chat.
2. Ask Fiaca to inspect or explain something.
3. Continue from a saved session.
4. Clean up local history when it is no longer useful.

## Start a chat

```bash
uv run fiaca chat
```

Use `Enter` to send, `Alt-Enter` for a new line, `Ctrl-C` to cancel a draft,
and `/exit` or `Ctrl-D` to leave the conversation.

During an interactive chat, explicit read-only workspace tools are available:

```text
/help
/inspect
/files
/read src/fiaca/ui.py
/find SessionStore
/task Review the current UI and suggest improvements
```

Tool commands show their result immediately and record the operation in the
session activity. They do not modify files or execute commands. Unknown slash
commands are rejected locally instead of being sent to the provider.

## Continue a session

```bash
uv run fiaca sessions
uv run fiaca chat --session <session-id>
```

The dashboard also lists sessions with numbered selection. Chat sessions resume
as interactive conversations. Read-only task sessions currently re-run their
original request and context for compatibility, and can now be continued
through the same interactive chat flow.

## Workspace tools

The current explicit commands remain available while the conversational tool
interface is developed:

```bash
uv run fiaca inspect
uv run fiaca files
uv run fiaca read path/to/file
uv run fiaca find "pattern"
```

These operations are read-only and stay inside the current workspace.

## Reset local history

To remove all saved conversations and internal tool history:

```bash
uv run fiaca cleanup
```

Confirm interactively, or use `uv run fiaca cleanup --yes` for an intentional
non-interactive reset. This does not remove provider configuration, `.env`
files, or workspace files.
