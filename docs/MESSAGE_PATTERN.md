# Common Message Pattern

Fiaca uses a project-independent message pattern for requests, plans, and
execution results. The pattern is intended to be reusable in any software
project, regardless of language, framework, or provider.

## Message envelope

Every meaningful project message should make these parts explicit:

```text
Context:
Goal:
Constraints:
Evidence:
Plan:
Action:
Result:
Next:
```

Not every message needs every field. Keep only the fields that add information.
The order is stable so messages remain easy to scan, search, summarize, and
retrieve across sessions.

## Request pattern

```text
Context:
  Describe the relevant project area and current behavior.

Goal:
  State one measurable outcome.

Constraints:
  State compatibility, scope, safety, style, or approval requirements.

Evidence:
  Include commands, errors, files, or observations that support the request.

Expected result:
  Describe how success will be verified.
```

Example:

```text
Context:
  Fiaca stores provider settings in YAML and loads API keys from .env.

Goal:
  Add persistent local sessions without sending stored messages to a provider.

Constraints:
  Keep the feature local, use the standard library where practical, and do not
  store API keys in the database.

Evidence:
  The current chat process loses its history when it exits.

Expected result:
  A new session appears in `fiaca sessions` and can be inspected with
  `fiaca history <session-id>`.
```

## Agent response pattern

Fiaca should structure work-oriented responses as:

```text
Understanding:
  Restate the requested outcome and important boundaries.

Plan:
  List the smallest ordered steps.

Changes:
  List files, commands, or external effects that will be involved.

Approval:
  Ask before applying patches, executing risky commands, or changing scope.

Validation:
  State the checks that will be run and their expected evidence.

Result:
  Report what actually happened, including failures.

Next:
  State the remaining work or the next decision.
```

## Rules

1. One message should have one primary goal.
2. Separate facts from assumptions.
3. Mention uncertainty instead of inventing evidence.
4. Prefer file paths, symbols, commands, and test results over vague claims.
5. Record decisions and rejected alternatives when they may matter later.
6. Keep secrets, tokens, and private credentials out of messages.
7. Use explicit approval before irreversible or externally visible actions.

This pattern is a documentation convention, not a provider-specific prompt
format. It can be used in chat, session summaries, issue descriptions, commits,
and future Fiaca tool results.
