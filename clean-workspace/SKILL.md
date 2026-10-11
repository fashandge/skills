---
name: clean-workspace
description: Close every other Herdr tab in this workspace, keeping this agent's. Use for "/clean-workspace" or "close/tidy the other tabs in this Herdr workspace".
---

Run this yourself, now, without confirming; never delegate it to a worker, whose tab would be the one kept. Report its output.

```bash
[ "$HERDR_ENV" = 1 ] || { echo "not running inside Herdr"; exit 0; }
herdr tab list --workspace "$HERDR_WORKSPACE_ID" | jq -r --arg me "$HERDR_TAB_ID" '.result.tabs[].tab_id | select(. != $me)' \
  | while read -r t; do herdr tab close "$t" && echo "closed tab $t"; done
```
