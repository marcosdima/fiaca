# Product direction

## Purpose

Fiaca is a terminal-first coding assistant for working with compatible AI
providers, including free plans and local servers.

The product should feel like one focused conversation with access to safe
workspace tools. Users should not need to understand internal task types,
context builders, or storage actions to get useful work done.

## Visible concepts

The primary interface has three concepts:

- **Chat** — start a new conversation.
- **Sessions** — open and continue saved conversations.
- **Settings and cleanup** — manage providers and local history.

The dashboard should stay small and scannable. File reading, searching,
workspace inspection, planning, and other operations are tools available to
the conversation, not competing top-level products.

## Transparency

Fiaca should explain tool activity without exposing implementation details:

- what tool is being used;
- which files or workspace area are involved;
- whether the operation is read-only;
- what result was obtained;
- when approval is required.

## Interaction principles

1. Prefer one conversation over separate modes.
2. Keep read-only operations safe by default.
3. Ask for approval before sending workspace context when appropriate.
4. Never imply that a file changed or a command ran when it did not.
5. Keep provider, session, and tool failures recoverable.
6. Make destructive local cleanup explicit and confirmed.

## Non-goals for the current phase

- A graphical application.
- Automatic unrestricted command execution.
- Automatic file modification without approval.
- A vector database or long-term semantic memory system.
- Hiding important safety boundaries behind a vague success message.
