# Fiaca documentation

This directory is the durable project context for Fiaca. It is intentionally
split by topic so a new conversation can load only the documents relevant to
the current decision.

## Start here

1. [Product direction](PRODUCT.md) — what Fiaca is and how the user should
   experience it.
2. [User guide](USER_GUIDE.md) — the current commands and workflows.
3. [Architecture](ARCHITECTURE.md) — the main modules and data flow.
4. [Sessions](SESSIONS.md) — persistence, resume behavior, and cleanup.
5. [Tools](TOOLS.md) — read-only workspace capabilities and their intended
   evolution into conversation tools.
6. [Security](SECURITY.md) — boundaries for credentials, files, providers, and
   approvals.
7. [Roadmap](ROADMAP.md) — implementation order and deferred work.
8. [Message pattern](MESSAGE_PATTERN.md) — structure for project and agent
   communication.

## Loading context after a reset

For product or UX work, read `PRODUCT.md`, `USER_GUIDE.md`, and `ROADMAP.md`.

For persistence or resume work, read `ARCHITECTURE.md` and `SESSIONS.md`.

For workspace tools, read `TOOLS.md` and `SECURITY.md`.

For response or prompt changes, read `MESSAGE_PATTERN.md`.

These documents describe intended direction separately from current
implementation. When they disagree, the implementation must be verified and
the discrepancy should be recorded before changing behavior.
