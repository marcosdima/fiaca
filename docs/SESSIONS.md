# Sessions and local history

## What is stored

Fiaca stores local data in:

```text
~/.fiaca/sessions.db
```

The location can be changed with `FIACA_DATA_DIR`.

The database contains:

- session metadata;
- user, assistant, and tool messages;
- internal action records;
- a local full-text search index.

API keys are not stored in the database.

## Resume behavior

Sessions are identified by a short local ID. The dashboard supports numbered
selection so users do not need to paste a long ID.

The intended behavior is that every saved session is a conversation. Current
read-only task sessions retain metadata that lets Fiaca reconstruct their
original context while the unified follow-up flow is implemented.

## Cleanup

`fiaca cleanup` permanently deletes all sessions, messages, actions, and search
data, then reclaims SQLite space. It does not remove configuration, provider
credentials, or workspace files.

Cleanup requires confirmation unless `--yes` is supplied. The dashboard uses a
stronger `DELETE` confirmation.

## Future storage boundaries

Session storage may later support archived or scoped histories, but a reset
must remain explicit. Do not silently delete sessions as part of normal UI
refactoring.
