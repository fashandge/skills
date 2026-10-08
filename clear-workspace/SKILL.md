---
name: clear-workspace
description: Close every other Herdr tab in the current workspace, keeping only the tab this agent runs in. Use when the user invokes "/clear-workspace" or asks to clear, tidy, or close the other tabs in this Herdr workspace.
---

# Clear Workspace

Invoking this skill is the user's explicit request to close the other tabs, so no confirmation is needed. Always run it in the invoking session, even in orchestrator mode — never delegate it to a worker, whose tab would be the one kept.

Require Herdr (`HERDR_ENV=1`); if it is unset, say this agent is not running inside Herdr and stop. Otherwise run:

```bash
herdr tab list --workspace "$HERDR_WORKSPACE_ID" \
  | jq -r --arg me "$HERDR_TAB_ID" '.result.tabs[].tab_id | select(. != $me)' \
  | while read -r tab; do herdr tab close "$tab" && echo "closed $tab"; done
```

Report which tabs were closed, or that there were none.
