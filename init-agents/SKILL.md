---
name: init-agents
description: Initialize CLAUDE.md with AGENTS.md symlink for multi-agent compatibility, then simplify the generated file into a concise router over docs/
---

Run /init to generate CLAUDE.md, then:

1. Change the first line from `# CLAUDE.md` to `# AGENTS.md`
2. Change the description line from "This file provides guidance to Claude Code (claude.ai/code)" to "This file provides guidance to AI coding agents (Claude Code, Codex, OpenClaw, Hermes, and similar tools)"
3. Create a symbolic link: `ln -sf CLAUDE.md AGENTS.md`
4. Run the /simplify-agents skill on the fresh CLAUDE.md to restructure it into a concise router over docs/ (keep step 1's header conventions). Two call-site overrides: it may rightly conclude a freshly generated file is already lean — accept that and stop; and **skip its final commit step** — whether/when to commit the newly initialized files is the user's call, consistent with /init.

This makes the file compatible with multiple AI coding agents that may look for either CLAUDE.md or AGENTS.md, and keeps it lean from day one.
