---
name: init-agents
description: Initialize CLAUDE.md with AGENTS.md symlink for multi-agent compatibility
---

Run /init to generate CLAUDE.md, then:

1. Change the first line from `# CLAUDE.md` to `# AGENTS.md`
2. Change the description line from "This file provides guidance to Claude Code (claude.ai/code)" to "This file provides guidance to AI coding agents (Claude Code, Codex, OpenClaw, Hermes, and similar tools)"
3. Create a symbolic link: `ln -sf CLAUDE.md AGENTS.md`

This makes the file compatible with multiple AI coding agents that may look for either CLAUDE.md or AGENTS.md.
