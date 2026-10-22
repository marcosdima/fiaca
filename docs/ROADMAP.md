# Roadmap

## Current phase

Stabilize the focused conversation experience:

1. simplify the dashboard to Chat, Sessions, Settings, and cleanup;
2. keep existing read-only tools available internally and through compatibility
   commands;
3. unify chat and read-only task sessions;
4. show structured tool activity in the conversation;
5. preserve explicit context and approval boundaries.

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
