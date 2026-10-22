# Roadmap

## Current phase

Stabilize the focused conversation experience. The baseline safety tests and
the first internal read-only tool registry are now in place. The remaining
work in this phase is to route conversation requests through the registry and
persist structured activity consistently.

1. simplify the dashboard to Chat, Sessions, Settings, and cleanup;
2. keep existing read-only tools available internally and through compatibility
   commands;
3. unify chat and read-only task sessions;
4. show structured tool activity in the conversation;
5. preserve explicit context and approval boundaries.

Completed foundations:

- workspace safety regression tests;
- explicit read-only tool result contract;
- shared registry for inspection, listing, reading, searching, and context
  building;
- compatibility commands routed through the registry.
- read-only task activity records for context completion, approval, and
  provider request outcomes.
- explicit read-only tool commands available inside interactive chat;
- task sessions resumable through the normal chat entry point.

## Next phase

Add safe change proposals:

1. generate a patch or diff;
2. display the proposed changes;
3. request explicit approval;
4. apply only the approved patch;
5. run selected validation commands only after approval.

## Deferred

- vector databases and semantic memory;
- unrestricted command execution;
- automatic writes;
- provider-specific optimization beyond the compatible baseline.

## Definition of focus

Every new feature should answer: does it make the main conversation safer,
clearer, or more useful? If it introduces a new top-level mode without a
strong reason, it should remain an internal tool instead.
