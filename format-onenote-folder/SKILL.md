---
name: format-onenote-folder
description: Format all OneNote-exported or OneNote-style Markdown notes under a folder or section into a mirrored output folder. Use when Codex is asked to process an input section such as Strategy/ with the existing format-one-note skill, preserve filenames and subfolder structure, choose a default output folder when unspecified, and parallelize multiple notes or long-note slices with bounded subagents.
---

# Format OneNote Folder

## Inputs

- Source section/folder: use the user-provided folder. 
- Output folder: use the user-provided output folder. If unspecified, use `<source-folder-name>-formatted/`
- File scope: process Markdown files (`*.md`) recursively under the source folder. Ignore non-Markdown files unless the user explicitly asks to copy them.

Resolve relative paths from the current workspace. Preserve the source tree under the output folder with the same filenames.

## Required Companion Skill

Use the existing `format-one-note` skill for per-note formatting rules. If it has not already been loaded in the turn, read:

`/Users/jianfuchen/skills/format-one-note/SKILL.md`

Follow its core rules exactly: preserve every data point, URL, example, caveat, quoted phrase, and meaning; convert original top-level bullet sections into `#` headings; use `##` and at most `###` internally; write only to the requested output location.

## Workflow

1. Discover Markdown files under the source folder with `find` or `rg --files`.
2. Count lines and top-level bullet sections for each note.
3. Create the mirrored output directories.
4. Format short and medium notes locally unless the user explicitly asks for subagents.
5. Use subagents for long or very long notes according to `format-one-note` thresholds.
6. When processing many notes, parallelize by assigning disjoint batches to at most 5 workers total. Do not spawn a worker per note when there are many notes.
7. Ensure workers are told they are not alone in the workspace, must not revert others' edits, and may write only to their assigned output files or temporary files.
8. Merge any temporary worker outputs in original section order.
9. Validate the finished output before final response.

## Parallelization Rules

- Keep global concurrency bounded at 5 workers unless the user gives a smaller limit.
- Prefer batching many short notes into folder or filename ranges.
- For one long note, split by top-level bullet section and use up to 5 workers for non-overlapping section ranges.
- If several long notes exist, avoid multiplying 5 workers by each note. Schedule batches so no more than 5 workers run at once.
- Do not use subagents for short notes under 300 lines or under 10 top-level sections unless the user explicitly requests parallelization; when they do, batch short notes together.

## Validation

For every processed Markdown file, check:

- The output file exists at the mirrored path.
- If the source has column-1 top-level bullets, output `#` headings match those titles in order.
- No heading is deeper than `###`.
- No deeply indented nested bullets remain, such as lines matching `^ {4,}[-*] `.
- URLs from the source are still present in the output.
- The number of output Markdown files equals the number of source Markdown files in scope.

If validation fails, repair the affected file directly or ask the relevant subagent for a targeted correction, then rerun validation.

## Final Response

Report the source folder, output folder, number of notes processed, whether subagents were used, and validation status. Mention any skipped non-Markdown files only if relevant.
