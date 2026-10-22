# Security and privacy boundaries

## Credentials

- Keep API keys in environment variables or local `.env` files.
- Never store keys in SQLite sessions, prompts, commits, or documentation.
- `.env` is excluded from Git.
- Treat accidentally exposed keys as compromised and rotate them.

## Workspace access

Read-only tools must remain inside the selected workspace. They must reject
sensitive files, ignored dependency directories, binary files, and files over
the configured size limits.

## Provider transmission

Workspace context is sent to an external provider only when the user approves
the operation or explicitly uses a trusted non-interactive option. The UI
should identify the files included in that context.

## Destructive actions

Deleting local history requires explicit confirmation. Applying patches,
executing commands, or changing configuration must use a separate approval
boundary.

## Failure behavior

Provider, parsing, and storage failures must be visible and recoverable. Fiaca
must not report a successful tool result when an operation failed or was not
performed.
