---
name: organize-obsidian-folder-notes
description: Organize loose Markdown notes in an Obsidian vault folder into appropriate existing or newly created subfolders. Use when the user asks to clean up a folder such as investment/, strategy/, research/, or any specified vault directory by moving notes that are directly under that folder into more specific subfolders, while preserving Obsidian links and note contents.
---

# Organize Obsidian Folder Notes

## Goal

Move Markdown notes that sit directly inside a specified Obsidian folder into the most appropriate subfolder. Prefer existing folders when they fit. Create new folders when the current folder structure does not provide a meaningful home.

Only organize the direct loose notes in the specified folder unless the user explicitly asks for recursive cleanup.

## Workflow

1. Identify the vault root and target folder from the user request.
   - Examples: `investment/`, `Strategy/`, `strategy/research skills/`.
   - Treat folder names case-sensitively on disk; inspect the filesystem if the user's casing differs.

2. Inventory the target folder.
   - List direct child Markdown files: `find <target> -maxdepth 1 -type f -name '*.md'`.
   - List existing subfolders: `find <target> -mindepth 1 -maxdepth 2 -type d`.
   - If there are no loose Markdown files, report that no moves are needed.

3. Read enough context to classify each loose note.
   - Inspect filename, frontmatter if present, headings, wiki links, tags, and the first substantial content.
   - For ambiguous notes, read more of the file before deciding.
   - Avoid relying only on the filename; Obsidian note names are often shorthand.

4. Choose the destination.
   - Prefer the most specific existing subfolder that matches the note's subject.
   - Use a second-level destination when it is clearly better, for example `investment/Stocks/Semiconductors/`.
   - Create a new subfolder only when no existing folder is a natural fit.
   - Name new folders by durable topics, not temporary actions. Prefer `Portfolio construction`, `Company research`, or `Macro` over `misc`, `notes`, or `new`.
   - Avoid burying notes too deeply unless the folder hierarchy is already that specific or the topic clearly warrants it.

5. Move files safely.
   - Create needed folders with `mkdir -p`.
   - Move notes with `mv`.
   - Preserve filenames unless the user also asked for renaming.
   - If a destination file already exists, do not overwrite it. Stop and choose a safe disambiguation or ask the user if the conflict is meaningful.

6. Verify the result.
   - Re-run the direct loose-note listing for the target folder.
   - Confirm new folders contain the moved notes.
   - Optionally scan for broken relative Markdown links if notes used local paths; plain Obsidian wiki links usually survive moves.

## Classification Heuristics

Use the note's actual meaning as the primary signal:

- Company or ticker research goes under the most specific company, sector, or equity-research folder available.
- Portfolio, allocation, valuation, or risk notes go under portfolio or investing-process folders.
- Macro, rates, inflation, credit, or geopolitics notes go under macro or market-environment folders.
- Resources, reading lists, templates, and workflows should go under resource/process folders instead of being mixed with substantive research.
- Overview notes for a folder should stay near the folder they summarize. If the user asks to move loose notes and an overview note describes the target folder itself, leave it directly in the target folder unless the target folder convention puts overviews elsewhere.

When several destinations are plausible, choose the folder that will make future Obsidian backlinks and search most useful. Prefer semantic fit over merely matching a word in the title.

## Reporting

At the end, summarize:

- Which loose notes were moved and where.
- Which new folders were created.
- Which notes, if any, were left in place and why.
- Any conflicts, empty notes, or ambiguous classifications that need user judgment.
