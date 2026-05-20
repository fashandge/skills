---
name: update-docs-and-push-code
description: Run the update-docs workflow, then commit and push relevant code and documentation changes. Use when the user asks for "/update-docs-and-push-code", "update docs and push", "update docs then commit and push", "commit&push after docs", or wants a shorthand for updating documentation, committing the current work, and pushing the active branch.
---

# Update Docs and Push Code

## Overview

Use this skill as a compact end-of-workflow routine: sync relevant docs with the current code changes, verify the resulting diff, commit only the intended files, and push the current branch.

## Workflow

1. Inspect the repository state with `git status --short`, `git diff --stat`, and targeted `git diff` reads as needed.

2. Run the `update-docs` skill workflow:
   - Review the code or behavior changes made in the current conversation.
   - Check project `CLAUDE.md`, parent `CLAUDE.md`, relevant `docs/architecture*.md`, other `docs/*.md`, README files, and API/contract docs.
   - Update only documentation that is directly affected.
   - If docs are already accurate, report that no documentation updates were needed.

3. Run focused verification appropriate to the changed files when practical. Use the repo’s documented commands and pinned runtimes. If verification is skipped or unavailable, say why.

4. Review the final diff before staging:
   - Keep unrelated user changes out of the commit.
   - Do not revert files you did not intentionally change.
   - Do not stage secrets, local databases, logs, generated caches, or unrelated artifacts.

5. Stage only the intended files with explicit paths.

6. Commit with a concise message that reflects the code/docs change. If there are no changes to commit, do not create an empty commit unless the user explicitly requested one.

7. Push the active branch to its upstream when configured. If no upstream exists, push to `origin <current-branch>` unless repo instructions say otherwise.

8. In the final response, summarize:
   - documentation updated, or that none was needed
   - verification run
   - commit hash, if a commit was created
   - push result

## Git Directives

When working in the Codex desktop app, emit the relevant final-response directives only after the matching Git action succeeds:

- `::git-stage{...}` after staging succeeds
- `::git-commit{...}` after committing succeeds
- `::git-push{...}` after pushing succeeds
