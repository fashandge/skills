---
name: init-agents
description: Initialize CLAUDE.md with AGENTS.md symlink for multi-agent compatibility, then simplify the generated file into a concise router over docs/
---

Run /init to generate CLAUDE.md, then:

1. Change the first line from `# CLAUDE.md` to `# AGENTS.md`
2. Change the description line from "This file provides guidance to Claude Code (claude.ai/code)" to "This file provides guidance to AI coding agents (Claude Code, Codex, OpenClaw, Hermes, and similar tools)"
3. Create a symbolic link: `ln -sf CLAUDE.md AGENTS.md`
4. Run the /simplify-agents skill on the fresh CLAUDE.md to restructure it into a concise router over docs/ (keep step 1's header conventions). Two call-site overrides: it may rightly conclude a freshly generated file is already lean — accept that and stop; and **skip its final commit step** — whether/when to commit the newly initialized files is the user's call, consistent with /init.

5. If the repo is under `~/projects`, add it to the dependency manifest `~/dotfiles/projects-dependencies.toml`: a `[projects.<repo dir name>]` entry with `depends_on` (the sibling repos it imports or references, from `projects-deps-check edges --project <name>`; `[]` for none) and a `test = { cmd = "..." }` when it has a suite. Then run `projects-deps-check check --project <name>` (it must pass) and `projects-deps-check install-hook --project <name>`. Rules: `~/.claude/docs/project-dependencies.md`. Like step 4, leave committing the manifest (in `~/dotfiles`) to the user.

This makes the file compatible with multiple AI coding agents that may look for either CLAUDE.md or AGENTS.md, and keeps it lean from day one.
