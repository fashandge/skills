---
name: close-others
description: Close every other Herdr workspace and every other tab here, keeping only this agent's tab. Use for "/close-others" or "close everything except this tab in Herdr".
---

Run this yourself, now, without confirming; never delegate it to a worker, whose tab would be the one kept. Report its output.

```bash
[ "$HERDR_ENV" = 1 ] || { echo "not running inside Herdr"; exit 0; }
herdr workspace list | jq -r --arg me "$HERDR_WORKSPACE_ID" '.result.workspaces[] | select(.workspace_id != $me) | "\(.workspace_id)\t\(.label)"' \
  | while IFS=$'\t' read -r w l; do herdr workspace close "$w" && echo "closed workspace $w ($l)"; done
herdr tab list --workspace "$HERDR_WORKSPACE_ID" | jq -r --arg me "$HERDR_TAB_ID" '.result.tabs[].tab_id | select(. != $me)' \
  | while read -r t; do herdr tab close "$t" && echo "closed tab $t"; done
```
