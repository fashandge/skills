---
name: format-one-note
description: Rewrite OneNote-exported or OneNote-style Markdown notes that are dominated by nested bullet points into readable heading-based Markdown. Use when Codex is asked to reformat a note by converting top-level bullets into sections with h1/h2/h3 headings while preserving all data points, URLs, examples, wording, and meaning; for short notes do the work locally to save tokens, and for long notes or explicit user requests use subagents in bounded parallel batches.
---

# Format OneNote

## Goal

Convert a nested-bullet note into regular Markdown structure without changing its substance. Treat the task as formatting and light organization, not summarization or rewriting for style.

## Core Rules

- Preserve every data point, URL, example, caveat, quoted phrase, and meaning.
- Keep the original language mix and terminology unless a tiny grammatical join is needed to turn bullets into prose.
- Convert each top-level bullet and everything nested under it into one independent section.
- Use `#` for each original top-level bullet title. Use `##` and at most `###` for internal structure.
- Use bullets sparingly when lists are genuinely clearer, but avoid recreating deep nested bullet trees.
- Do not collapse separate ideas if doing so would lose nuance or sequence.
- Write to a new output file when requested; do not overwrite the original unless explicitly asked.

## Workflow

1. Inspect the source note and identify exact top-level bullet boundaries.
2. Split the file into chunks where each chunk is one top-level bullet section and its nested content.
3. Decide whether to use subagents based on note size and user instructions. For long and very long notes, use subagents by default unless the user explicitly asks you to work locally or subagents are unavailable.
4. For local work, rewrite the sections directly into the requested output file or a temporary merged file.
5. For subagent work, assign disjoint section ranges to workers, instruct each worker to preserve order and meaning, then merge intermediate files in original section order.
6. Validate the result before finalizing.

## Size Criteria

Use concrete thresholds so token use stays proportional to the task:

- Short: under 300 lines or under 10 top-level bullet sections. Do the rewrite locally; do not spawn subagents unless the user explicitly asks.
- Medium: 300-800 lines or 10-40 top-level bullet sections. Usually do the rewrite locally; use subagents only if sections are unusually dense or the user asks.
- Long: over 800 lines or over 40 top-level bullet sections. Use subagents by default. Do not skip subagents merely because the user did not explicitly request them.
- Very long: over 1,500 lines or over 100 top-level bullet sections. Use batched subagents and validate carefully after merging. Do not skip subagents merely because the user did not explicitly request them.

When using subagents, limit concurrency to the user's requested number. If no limit is given, run at most 5 workers in parallel. If you intentionally do not use subagents for a long or very long note, state the reason before continuing.

## Splitting Guidance

For Markdown notes whose top-level bullets begin at column 1, section boundaries are lines that start with `* ` or `- `. Nested bullets are indented and belong to the current section.

Use a deterministic split script or shell/Python snippet when the file is long. In this repository, follow local Python interpreter instructions if present. Keep split artifacts in a temporary folder such as `.codex_tmp/format_one_note/`.

## Subagent Prompt Pattern

Give each worker a narrow, non-overlapping write target:

```text
You are rewriting a slice of a long Markdown note. You are not alone in the codebase; do not revert or touch edits made by others.

Your sole write target is <temporary-output-file>.
Read <section-range> in order. For each original top-level bullet section, rewrite it independently into regular Markdown headings: make the top-level bullet title an `#` heading, use `##` and at most `###` for nested structure, and use bullets only when they are genuinely clearer.

Preserve every data point, URL, example, nuance, and meaning. This is mainly a formatting rewrite, not summarization. Keep the original language mix and wording as much as possible while converting nested bullet shape into readable paragraphs/headings. Combine sections in original order into your target file.
```

## Validation

Before final response, check:

- The output has the same number of `#` sections as the source has top-level bullet sections.
- The `#` headings match the original top-level bullet titles in order.
- No heading is deeper than `###`.
- There are no deeply indented leftover nested bullets.
- URLs from the source still appear in the output.
- The output path requested by the user exists.

If validation finds a mismatch, repair the affected section directly or ask the relevant subagent for a targeted correction.
