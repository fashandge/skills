---
name: close-workspaces
description: Close every other Herdr workspace, keeping only the workspace this agent runs in. Use when the user invokes "/close-workspaces" or asks to close all the other Herdr workspaces.
---

# Close Workspaces

Invoking this skill is the user's explicit request to close the other workspaces, so no confirmation is needed. Always run it in the invoking session, even in orchestrator mode — never delegate it to a worker, whose workspace would be the one kept.

Require Herdr (`HERDR_ENV=1`); if it is unset, say this agent is not running inside Herdr and stop. Otherwise run:

```bash
herdr workspace list \
  | jq -r --arg me "$HERDR_WORKSPACE_ID" '.result.workspaces[] | select(.workspace_id != $me) | "\(.workspace_id)\t\(.label)"' \
  | while IFS=$'\t' read -r ws label; do herdr workspace close "$ws" && echo "closed $ws ($label)"; done
```

Report which workspaces were closed, or that there were none.
