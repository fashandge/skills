---
name: close-workspaces
description: Close every other Herdr workspace, keeping this agent's. Use for "/close-workspaces" or "close the other Herdr workspaces".
---

Run this yourself, now, without confirming; never delegate it to a worker, whose workspace would be the one kept.

```bash
[ "$HERDR_ENV" = 1 ] || { echo "not running inside Herdr"; exit 0; }
herdr workspace list | jq -r --arg me "$HERDR_WORKSPACE_ID" '.result.workspaces[] | select(.workspace_id != $me) | .workspace_id' \
  | while read -r w; do herdr workspace close "$w" >/dev/null; done
```
