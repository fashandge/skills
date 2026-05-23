---
name: wiki
description: Generate a wiki article in the user's Obsidian vault. Use when the user asks to "write a wiki", "create a wiki", "generate a wiki", or wants to turn a discussion into a structured knowledge article. Accepts a description of what to generate in the prompt.
---

# Wiki Generator for Obsidian Vault

Generate structured wiki articles in the user's Obsidian vault at `~/notes/wiki/`.

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

## Step 2: Choose Folder Location

The wiki goes under `~/notes/wiki/`. Follow these rules **in order**:

1. **List existing folders first:**
   ```bash
   find ~/notes/wiki -type d -maxdepth 4 | sort
   ```

2. **Use an existing folder** if one clearly fits the topic. Existing folders include:
   - `wiki/Software Engineering/` (System Design, skills)
   - `wiki/ai/` (agent, reinforcement learning)
   - `wiki/ai_and_engineering/` (paradigm_shifts)
   - `wiki/investment/` (trading)
   - (Always re-check at generation time — the user may have added more)

3. **Create a new folder** if no existing folder fits. New folders must be:
   - At least **2 levels deep** under `wiki/` (e.g., `wiki/topic/subtopic/`)
   - Ideally **3 levels deep** for specificity (e.g., `wiki/topic/subtopic/area/`)
   - Never a single flat folder directly under `wiki/` (e.g., NOT `wiki/my-new-topic/`)

4. **Naming conventions:**
   - Folder names: lowercase with spaces or hyphens, English preferred (e.g., `Software Engineering/skills/`)

## Step 2b: Choose Title and Filename

The title, filename, and `# H1` heading must all be **identical**.

**Title rules:**
- Must be **globally unique** across the vault — specific enough to never collide
- Lead with the core subject, add a short qualifier only if needed to disambiguate
- Include concrete nouns (names, technologies, concepts) rather than generic words
- Must be valid for Obsidian backlinking: **no `/`, `\`, `^`, `[`, `]`, `|`, `:` characters**
- Can be English or Chinese depending on content language

**Good titles:** `DHH on Agent-First Programming and Engineer Value Shifts`, `Kent Beck Smalltalk Best Practice Patterns`, `CLI as the Ideal Agent Interface`
**Bad titles:** `AI Summary`, `Design Notes`, `Interview Thoughts`, `wiki entry`

**Filename** = title + `.md`. Example: `DHH on Agent-First Programming and Engineer Value Shifts.md`

This enables clean backlinking: `[[DHH on Agent-First Programming and Engineer Value Shifts]]` — no path needed when the title is unambiguous.

## Step 3: Generate the Wiki Article

Use the following structure. All sections are required unless noted.

### 3a. Frontmatter

```yaml
---
title: <same as filename, without .md>
date: <today's date, YYYY-MM-DD>
tags:
  - <relevant tag 1>
  - <relevant tag 2>
  - <...3-6 tags total>
---
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
- [[#Section Title 2]]
- [[#Section Title 3]]
```

**Rules for the table of contents:**
- Include **all h2 (`##`) and h3 (`###`) headings** — up to two levels deep
- Use the `[[#Exact Heading Text]]` format (Obsidian native heading links)
- The heading text inside `[[#...]]` must **exactly match** the actual heading in the document
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

### 3e. References Section

End with a references section containing backlinks to relevant notes in the vault:

```markdown
---

## 参考资料

- [[related note 1]] — brief description of relevance
- [[related note 2]] — brief description of relevance
- [[External Link Title]](https://url) — for external sources
```

**Rules for references:**
- **All backlinks go here** — this is the single place for all links (no source backlinks at the top)
- Link to the original source document(s) that informed this wiki
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

- [ ] **Title = filename = H1** — all three are identical
- [ ] Title is globally unique, concrete, and contains no `^`, `[`, `]`, `|`, `:` characters
- [ ] Overview section answers "what is this, why does it exist?"
- [ ] Table of contents uses `[[#Heading Text]]` with exact heading matches
- [ ] No quotes or special characters in heading text that could break links
- [ ] References section has all backlinks (source docs, related wikis, external URLs)
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
tags:
  - 软件工程
  - 设计能力
---

# DHH on Improving Software Design Skill in the Agent Era

> **概述**：基于 DHH 对 AI 时代软件工程的观点，总结提升软件设计能力的
> 五个关键步骤。核心观点是：在 Agent 时代，实现能力贬值，判断能力升值，
> 设计能力正在成为工程师最重要的竞争力。

---

## 📚 目录

- [[#什么是软件设计能力]]
- [[#第一步：理解材料]]
- [[#参考资料]]

---

## 什么是软件设计能力

...body content...

---

## 参考资料

- [[从拒绝AI到一切先问Agent，DHH]] — 原始访谈全文
- [[DHH on Agent-First Programming and Engineer Value Shifts]] — DHH 观点的完整 wiki
- [Shape Up](https://basecamp.com/shapeup) — Basecamp 的产品开发方法论
```
