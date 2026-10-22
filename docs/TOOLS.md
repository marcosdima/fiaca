# Conversation tools

## Current read-only capabilities

Fiaca currently supports:

- workspace inspection;
- readable file listing;
- bounded text file reading;
- regular-expression search;
- bounded context building;
- read-only analysis and implementation planning.

Sensitive files, ignored directories, binary content, path traversal, and
oversized files are rejected by the workspace layer.

## Product direction

These capabilities should be invoked from a conversation rather than
presented as separate user modes. A future interaction may look like:

```text
You: Review the current UI and suggest a safer navigation flow.

Fiaca: I will inspect the relevant UI files. This is read-only.
        [read files]
        [analyze]
        Here is the result...
```

The tool result should identify its operation, scope, safety level, and result.

## Approval boundaries

Read-only inspection can be automatic when the scope is clear. Sending a
selected workspace context to an external provider should remain visible and,
when appropriate, require approval.

File writes, patch application, and command execution are future capabilities.
They require separate approval design and must not be smuggled into a
read-only tool.
