---
name: clean-obsidian-note-titles
description: Clean titles for Markdown notes under a specified Obsidian vault folder. Use when the user asks to process all notes in a folder such as strategy/, investment/, or research/ by removing redundant first H1 headings and renaming files to meaningful, globally useful, search-friendly note titles.
---

# Clean Obsidian Note Titles

## Goal

For every Markdown note under a specified folder, remove a redundant first top-level heading and improve the filename when the current title is vague, awkward, duplicated, path-dependent, or not good for search.

Only process Markdown note files. Ignore non-note sidecar files such as `manifest.json`, export logs, indexes, cache files, and other metadata files.

Process notes recursively unless the user explicitly asks for only direct children.

## Workflow

1. Identify the vault root and target folder.
   - Treat the folder path on disk as authoritative.
   - If the user's casing differs, inspect the filesystem and choose the matching real path.

2. Inventory all Markdown files under the folder.
   - Use `find <target> -type f -name '*.md'`.
   - Skip hidden/system folders if present, such as `.obsidian`, `.trash`, `.git`, or template/cache directories.
   - Do not inspect, edit, validate, or synchronize non-Markdown files such as `manifest.json`. They are outside the title-cleanup scope.

3. Remove a redundant first H1 at the top.
   - Inspect only the first substantial heading at the very top of the note.
   - Remove it when it is basically the same as the filename stem after normalizing case, punctuation, whitespace, hyphens/underscores, and obvious Markdown escaping.
   - Also remove it when it is only a trivial variant of the filename, such as added title case, removed punctuation, or repeated folder context.
   - Do not remove an H1 that adds meaningful disambiguation, a subtitle, a date, a source, or a different framing from the filename.
   - Preserve YAML frontmatter if present. If frontmatter exists, consider the first H1 immediately after the frontmatter.

4. Review each filename for quality.
   - Prefer filenames that are meaningful and read naturally.
   - Prefer globally unique titles when practical, especially for notes likely to be searched or summarized by AI agents.
   - When the original filename has useful subject words, reuse those words in the improved title whenever they still match the note. Add concise context from ancestor folders and the note's actual content instead of replacing the title with a totally different framing.
   - Keep the core subject first; add a short qualifier only when needed to disambiguate.
   - Use folder paths for grouping, not identity. Avoid titles that only make sense because of the folder path.
   - If a title is out of context but the original words are meaningful, prepend or append the missing domain context. For example, in `Strategy/Writing - presentation/Sections and parts.md`, prefer `Research Paper Sections and Parts.md` over a broader rewrite like `Research Paper Structure and Figures.md`.
   - Prefer `GEV Quick Screen`, `John Schulman on KL Divergence Estimator`, or `Entropy (RL)` over generic names like `quick_screen`, `summary`, `notes`, `overview`, or `thoughts`.
   - Keep `Overview` in the name for notes that are intentionally folder overviews, unless the user says otherwise.

5. Apply filename-safe rename rules.
   - Do not use characters that are awkward or invalid in filenames: `^`, `|`, `[`, `]`, `\\`, `/`, `:`.
   - Avoid leading punctuation, trailing punctuation, and excessive whitespace.
   - Avoid path-heavy names that duplicate folder hierarchy unless needed for uniqueness.
   - Keep the `.md` extension.
   - Before renaming, check for collisions in the destination folder and likely global title collisions in the vault.
   - If a rename would collide, add a short qualifier in parentheses or after the core subject.

6. Execute edits safely.
   - Use normal filesystem moves for renames after collision checks.
   - Do not overwrite files.
   - Avoid unrelated content edits beyond the redundant H1 removal.
   - If there are many renames, keep a mapping of old path to new path for the final report.

7. Verify.
   - Confirm no processed note still starts with a redundant H1 matching its filename.
   - Confirm renamed files exist and old paths are gone.
   - Report any ambiguous notes left unchanged.

## Title Judgment

Rename when the current filename is:

- Generic: `summary`, `thoughts`, `quick_screen`, `untitled`, `notes`.
- Too dependent on the folder path for meaning.
- A clipped import title that does not read naturally.
- Duplicated or likely to be confused with another note.
- Contains unsafe filename characters.
- Misleading compared with the note's actual subject.

Keep the current name when it is already meaningful, natural, specific enough, and filename-safe.

When renaming, prefer conservative enrichment over semantic replacement:

- Preserve meaningful original words such as `sections`, `parts`, `practice`, or `resources` when they accurately describe the note.
- Add context from parent folders and content, such as `Research Paper`, `Hyperfocus`, `Learning`, or `FB Advancing`, so the title works outside its folder.
- Avoid discarding the user's original vocabulary unless it is misleading, generic filler, misspelled beyond recognition, or unsafe for filenames.

## Reporting

At the end, summarize:

- H1 headings removed.
- Files renamed, with old path -> new path.
- Notes intentionally left unchanged because the H1 or filename carried meaningful information.
- Any conflicts or ambiguous renames that need user judgment.
