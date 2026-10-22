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

The current implementation provides a shared internal registry for these
read-only operations. Compatibility commands and dashboard actions use the
same registry, so their workspace safety rules remain consistent. Context
building is also represented as a read-only tool and remains separate from
provider transmission.

## Approval boundaries

Read-only inspection can be automatic when the scope is clear. Sending a
selected workspace context to an external provider should remain visible and,
when appropriate, require approval.

Read-only task sessions record structured activity for context completion,
context approval, provider request start, provider completion, and provider
failure. A failed or cancelled operation must not be represented as a
successful result.

File writes, patch application, and command execution are future capabilities.
They require separate approval design and must not be smuggled into a
read-only tool.
