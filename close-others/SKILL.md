---
name: close-others
description: Close every other Herdr workspace and every other tab in the current workspace, leaving only the tab this agent runs in — a shorthand for running close-workspaces then clean-workspace. Use when the user invokes "/close-others" or asks to close everything except this tab in Herdr.
---

# Close Others

Invoking this skill is the user's explicit request for both sub-skills, so no confirmation is needed. Run it in the invoking session, never a worker.

1. Follow the `close-workspaces` skill.
2. Then follow the `clean-workspace` skill.

If the first step stops because Herdr is unavailable, skip the second. Report what each step closed in one combined summary.
