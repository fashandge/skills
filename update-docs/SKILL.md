---
name: update-docs
description: This skill should be used when the user asks to "update docs", "update documentation", "sync docs with changes", "update CLAUDE.md", or after making code changes that may require documentation updates.
---

# Update Documentation Skill

Update relevant documentation to reflect code changes made in the current conversation.

## Workflow

1. **Identify changes**: Review code modifications made in the conversation (edits, new files, behavior changes)

2. **Find relevant docs**: Locate documentation files that might need updates:
   - **CLAUDE.md files**:
     - Project-level: `./CLAUDE.md` in the current working directory
     - Parent-level: `../CLAUDE.md` if the project is nested
     - User-level: `~/.claude/CLAUDE.md` for cross-project changes
   - **Architecture docs**: `docs/architecture*.md`, `docs/*.md`
   - **README files**: `README.md` at project root
   - **API docs**: Files documenting APIs, contracts, or interfaces

3. **Check each doc**: Read each file and identify sections that describe the changed behavior

4. **Update if needed**: Edit sections that are now outdated or incomplete due to the code changes

5. **Report**: Summarize what was updated or confirm docs are already accurate

## Guidelines

- Only update sections directly affected by the code changes
- Preserve existing formatting and style
- Keep updates minimal and focused
- If docs are already accurate, report "No documentation updates needed"
- Do not add new sections unless the change introduces entirely new functionality
- Check CLAUDE.md files first (used by AI agents), then architecture docs and README — check all of them, not just the first match
