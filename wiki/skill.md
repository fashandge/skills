---
name: wiki
description: Generate a wiki article in the user's Obsidian vault. Use when the user asks to "write a wiki", "create a wiki", "generate a wiki", or wants to turn a discussion into a structured knowledge article. Accepts a description of what to generate in the prompt.
---

# Wiki Generator for Obsidian Vault

Generate structured wiki articles in the user's Obsidian vault at `~/notes/wiki/`.

> **Vault schema**: `~/notes/wiki/Wiki Organization Conventions.md` is the single source of truth for vault structure (tree-first organization, MECE at top 2 levels, Overview notes, merge-over-create compounding). This skill implements those conventions for article creation; read that note when a placement or structure decision is ambiguous. For injecting an existing `raw/` note into the wiki, prefer the `/absorb` skill, which decides merge vs create vs cite.

> **Obsidian syntax**: This skill's defaults stay conservative — frontmatter, wikilinks, tables, plain prose. For richer Obsidian-specific syntax (callouts, embeds, block IDs, highlights, footnotes, Mermaid), consult the `obsidian-markdown` skill as a reference. Reach for **callouts** (`> [!abstract]`, `> [!note]`, `> [!warning]`) when the Overview block or a key-insight call-out would read better than a plain blockquote, and for **section embeds** (`![[Note Name#Heading]]`) when surfacing a source paragraph verbatim is clearer than paraphrasing it.

## When to Use This Skill

Trigger when user:
- Says "write a wiki", "create a wiki", "generate a wiki"
- Asks to turn a conversation or discussion into a wiki article
- Says "/wiki" followed by a topic or description
- Wants to document learnings, insights, or synthesized knowledge from the current session

## Step 1: Determine Content

The user provides a description of what to generate. This is typically based on **previous discussions in the current session** — synthesizing answers, insights, and references that have already been explored.

**Gather source material:**
- Review the current conversation for relevant answers, analysis, and references
- If the user mentions specific notes (via `@filename` or `<current_note>`), read those files
- If backlinks or source documents are referenced, read them for additional context
- Calling skills (e.g. `ask-chatbots`, `research-notes`) may hand over a temp-file path as the body source, and/or a coverage caveat to include — read the file yourself rather than expecting inlined content, and carry any caveat into the overview or body

## Step 2: Check for an Existing Note to Update (Merge-over-Create)

Per the vault conventions, the wiki compounds by **updating existing notes in place** rather than accumulating near-duplicate siblings. Before creating a new article, find existing wiki notes on the same subject by delegating retrieval to the **`/research-notes` skill** — it owns the retrieval strategy (index browsing + multi-query expansion + union/dedupe/rerank); do not reinvent it with ad-hoc `notes-search` calls. Invoke it with these constraints (they override its defaults):

- **Lookup-only mode** — return ~top 10 titles + paths; no reading of note bodies, no synthesis.
- **Console-only** — do NOT persist a wiki (its default output destination is this very skill; persisting would recurse).
- **Scoped to `wiki/`** — browse `index/wiki/root_index.md` only and restrict searches with `--folder wiki`.

Then judge the returned candidates yourself (read the top few — overview blockquote + headings suffice):

- If an existing wiki note covers the same subject, **update that note** (integrate the new material, bump `updated:` in frontmatter, extend `## References`) instead of creating a duplicate.
- Only create a new article for a genuinely new subject.
- **If the requested content spans multiple distinct subjects**, don't produce one grab-bag article — propose splitting into separate articles/updates (one per subject, each with its own unique title and folder home, cross-linked in their References), confirm the split with the user, then handle each subject through this workflow. One coherent argument = one note; wiki notes are single-subject so titles stay unique and linkable.
- Skip this step only when the check was already done by the caller (e.g. the `/absorb` skill states it routed and deduped already).

## Step 2a: Choose Folder Location

The wiki goes under `~/notes/wiki/`. If the caller already routed a target folder (e.g. the `/absorb` skill passes the folder it chose in its own routing step), use that folder and skip rules 1–2 below — re-deriving it would second-guess a decision the caller owns. Otherwise follow these rules **in order**:

1. **Route via the generated wiki index first** — read `~/notes/index/wiki/root_index.md`. It opens with a **Section Tree** (each section linked with its assigned-note count), followed by one block per section with a `Description` — curated from the folder's `Overview of <Folder>` note where one exists (authoritative, states boundaries), otherwise generated (a hint). Pick the section whose Description fits the topic, **preferring the deepest section that fits**, and respect stated boundaries (e.g., market investing → `Investment/`, but taxes/benefits → `Life/`). **The Section Tree is coarser than the real folder tree**: small folder subtrees (≤20 notes) don't get their own section — their notes are listed in the nearest ancestor section — so the deepest section may be shallower than the deepest existing folder. Before finalizing, open the chosen section's index under `~/notes/index/wiki/section_indices/` and scan its notes' `Path`s and `Subsections:` line: if an existing deeper subfolder fits the topic better, place the note there instead of the section's own folder.

2. **Fall back to listing folders** when the index is missing or ambiguous:
   ```bash
   find ~/notes/wiki -maxdepth 4 -type d | sort
   ```
   Judge only from live output (index or `find`) — the vault changes often, so never rely on a remembered snapshot of its folders.

3. **Create a new folder** if no existing folder fits. New folders must be:
   - At least **2 levels deep** under `wiki/` (e.g., `wiki/Topic/subtopic/`)
   - Ideally **3 levels deep** for specificity (e.g., `wiki/Topic/subtopic/area/`)
   - Never a single flat folder directly under `wiki/` (e.g., NOT `wiki/my-new-topic/`)
   - Never a new **top-level** topic without asking the user — that is a rare, deliberate act per the conventions

4. **Naming conventions:**
   - Top-level topic folders: Title Case English (`AI`, `Investment`, `Software Engineering`)
   - Deeper folder names: lowercase with spaces or hyphens, English preferred (e.g., `Software Engineering/skills/`)

## Step 2b: Choose Title and Filename

The title, filename, and `# H1` heading must all be **identical**.

**Title rules:**
- Must be **globally unique** across the vault — specific enough to never collide
- Lead with the core subject, add a short qualifier only if needed to disambiguate
- Include concrete nouns (names, technologies, concepts) rather than generic words
- Must be valid for Obsidian backlinking: **no `/`, `\`, `#`, `^`, `[`, `]`, `|`, `:` characters** (`#` in a title breaks `[[Title#Heading]]` links)
- English or Chinese per the language rule in Step 2c (title, filename, and H1 follow the article's language)

**Good titles:** `DHH on Agent-First Programming and Engineer Value Shifts`, `Kent Beck Smalltalk Best Practice Patterns`, `CLI as the Ideal Agent Interface`
**Bad titles:** `AI Summary`, `Design Notes`, `Interview Thoughts`, `wiki entry`

**Filename** = title + `.md`. Example: `DHH on Agent-First Programming and Engineer Value Shifts.md`

**Verify uniqueness** before writing — the title must not collide with any existing note in the vault:

```bash
find ~/notes -name "<Title>.md"
```

If this returns a hit, add a qualifier to the title and re-check.

This enables clean backlinking: `[[DHH on Agent-First Programming and Engineer Value Shifts]]` — no path needed when the title is unambiguous.

## Step 2c: Choose Article Language

Write the article in the **dominant language of the material**, not a fixed default:

- If the source note(s) being written up — or, when updating in place, the destination wiki note — are **mainly Chinese**, write the article in Chinese (prose, section headings, and the title/filename/H1).
- When **most sources are English**, write in English.
- When updating an existing note, match that note's existing language; don't flip a Chinese note to English (or vice versa) just because one new source differs.

The fixed convention headings `## 📚 目录` and `## References` stay verbatim regardless of language. Keep technical terms (tool names, API params, code, product names) in their original form inline.

## Step 3: Generate the Wiki Article

Use the following structure. All sections are required unless noted.

The section headings `## 📚 目录` and `## References` are fixed conventions — use them verbatim for **both English and Chinese** articles (do not switch to `## Table of Contents` or `## 参考资料`). Existing notes written before this convention may still use `## 参考资料`; treat it as equivalent when reading or merging, and rename it to `## References` when substantively updating such a note.

### 3a. Frontmatter

```yaml
---
title: <same as filename, without .md>
date: <today's date, YYYY-MM-DD — take it from the session context or `date +%F`, don't guess>
updated: <today's date, YYYY-MM-DD>
tags:
  - <relevant tag 1>
  - <relevant tag 2>
  - <...3-6 tags total>
---
```

`date` is the creation date and never changes; `updated` is bumped on every substantive edit of the article. Do **not** add a `sources:` frontmatter field — provenance lives only in the `## References` section.

For tag consistency, check what sibling articles in the chosen folder already use before inventing new tags:

```bash
awk '/^tags:/{f=1;next} /^---/{f=0} f&&/^  - /' "<chosen folder>"/*.md | sort | uniq -c | sort -rn
```

### 3b. Title and Overview

```markdown
# <same title again>

> **<2-3 sentence overview>**: What is this wiki about? Why was it written?
> What question does it answer or what insight does it capture?
> This should be enough for someone to decide in 5 seconds whether to keep reading.
```

The overview is critical — when revisiting months later, the reader needs to immediately know **what this is, why it exists, and what value it provides** without reading the full article.

### 3c. Table of Contents

Use Obsidian wikilink heading references for clickable navigation:

```markdown
## 📚 目录

- [[#Section Title 1]]
    - [[#Subsection Title 1a]]
- [[#Section Title 2]]
- [[#Section Title 3]]
```

**Rules for the table of contents:**
- Include **all h2 (`##`) and h3 (`###`) headings** — up to two levels deep, with h3 entries indented under their h2
- Use the `[[#Exact Heading Text]]` format (Obsidian native heading links)
- The heading text inside `[[#...]]` must **exactly match** the actual heading in the document
- Heading text must be **unique document-wide** — `[[#...]]` resolves to the *first* matching heading, so repeated h3 text under different h2s (e.g. two `### 示例` sections) silently mislinks; qualify the heading text instead
- Do NOT use markdown anchor links (`[text](#anchor)`) — they don't work in Obsidian
- Do NOT use block IDs (`^id`) — unnecessary complexity
- Do NOT put quotes (「」、""、 etc.) in heading text — they break anchor links

### 3d. Body Content

Write the main content with:
- Clear `##` section headers and `###` subsections
- Tables for comparisons, summaries, and structured data
- Code blocks where relevant
- Blockquotes for key insights or direct quotes from sources
- Bullet lists for actionable items
- Bold for emphasis on key terms or conclusions

**Content guidelines:**
- Be **specific and concrete** — include names, dates, numbers, examples
- Include **direct quotes** from source material when available (with attribution)
- Use **tables** for any comparison or structured information
- Add **practical/actionable takeaways** where appropriate
- Avoid vague generalities — every paragraph should convey a distinct insight
- **Inline every hyperlink onto the phrase it describes** — write `[Source Title](url)`
  or `[[Note Name]]` directly on the title/term in the prose, table cell, or list
  item. Never leave bare `https://…` URLs or dump a standalone list of raw links
  under a table/section as an afterthought. A reader should click the words, not a
  URL string. (Raw URLs are acceptable inside code blocks where the literal
  string matters, and in the `## References` section, which is a link index by
  design.)

### 3e. References Section

End with a references section containing backlinks to relevant notes in the vault:

```markdown
---

## References

- [[source raw note]] — source: original interview transcript this wiki is built from
- [[related note 1]] — brief description of relevance
- [[related note 2]] — brief description of relevance
- [External Link Title](https://url) — for external sources (markdown link, NOT `[[...]](url)`)
```

**Rules for references:**
- **All backlinks go here** — this is the single place for all links (no source backlinks at the top, no `sources:` frontmatter)
- Link to the original source document(s) that informed this wiki, annotated with a `source:` prefix in the annotation so sources are distinguishable from see-also links
- Link to related wiki articles in the vault
- Link to any notes mentioned or quoted in the body
- Include external URLs for books, articles, or tools mentioned
- Each reference should have a brief annotation explaining its relevance

## Step 4: Verify and Report

After writing the file:

1. **Verify the file was created** by reading back the first 10 lines
2. **Report to the user:**
   - The file path and folder structure
   - A brief summary of what was generated
   - The table of contents as a preview
   - Any related wiki articles that already exist in the vault

## Quality Checklist

Before finishing, verify:

- [ ] Checked for an existing wiki note on the same subject first (merge-over-create)
- [ ] **Title = filename = H1** — all three are identical
- [ ] Title is globally unique (verified with `find ~/notes -name "<Title>.md"`), concrete, and contains no `/`, `\`, `#`, `^`, `[`, `]`, `|`, `:` characters
- [ ] Overview section answers "what is this, why does it exist?"
- [ ] Table of contents uses `[[#Heading Text]]` with exact heading matches, and heading text is unique document-wide
- [ ] No quotes or special characters in heading text that could break links
- [ ] `## References` section has all backlinks (source docs annotated `source:`, related wikis, external URLs)
- [ ] Frontmatter has `updated:`; no `sources:` field
- [ ] Tags in frontmatter are relevant and consistent with existing vault tags
- [ ] Folder is at least 2 levels deep under `wiki/`
- [ ] Content is specific and concrete, not vague generalities

## Example Output Structure

```
wiki/Software Engineering/skills/DHH on Improving Software Design Skill in the Agent Era.md
```

```markdown
---
title: DHH on Improving Software Design Skill in the Agent Era
date: 2026-04-11
updated: 2026-04-11
tags:
  - 软件工程
  - 设计能力
  - AI时代
---

# DHH on Improving Software Design Skill in the Agent Era

> **概述**：基于 DHH 对 AI 时代软件工程的观点，总结提升软件设计能力的
> 五个关键步骤。核心观点是：在 Agent 时代，实现能力贬值，判断能力升值，
> 设计能力正在成为工程师最重要的竞争力。

---

## 📚 目录

- [[#什么是软件设计能力]]
- [[#第一步：理解材料]]
- [[#References]]

---

## 什么是软件设计能力

...body content...

---

## References

- [[从拒绝AI到一切先问Agent，DHH]] — source: 原始访谈全文
- [[DHH on Agent-First Programming and Engineer Value Shifts]] — DHH 观点的完整 wiki
- [Shape Up](https://basecamp.com/shapeup) — Basecamp 的产品开发方法论
```
