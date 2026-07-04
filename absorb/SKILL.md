---
name: absorb
description: Absorb one or more notes from raw/ — or insights from elsewhere — into the wiki/ knowledgebase so it compounds instead of accumulates. Decomposes each source into insights and decides merge vs create vs cite per insight, so one rich source can update several wiki notes. Use when the user says "absorb this note", "promote this note", "inject this into the wiki", "merge this raw note into the wiki", "add this clipping to my knowledgebase", "/absorb <note path or topic>", or asks to distill recent raw notes into the wiki.
---

# Absorb: raw → wiki Injection

Inject knowledge from `raw/` source notes (or the current conversation) into the `wiki/` knowledgebase, following the compounding workflow defined in `~/notes/wiki/Wiki Organization Conventions.md` (the single source of truth — read it if a rule here seems ambiguous).

**Core principle: merge > create > cite.** The wiki compounds by deepening existing conclusions, not by adding siblings. Creating a new note is the exception, not the default.

## Inputs

- One or more raw note paths (e.g. `raw/AI/Agent/some clipping.md`), or
- A topic/folder (e.g. "absorb my recent notes on RL entropy" → find candidates first), or
- Insights from the current session that reference raw notes.

Read each source note fully before deciding anything — **and read the title together with the body as one unit.** Here "title" means whatever carries it: frontmatter `title`, else the **filename stem**, else the first H1 (same precedence the parser uses) — often it's the filename, not a frontmatter field, and for a note with no frontmatter the filename stem is the *only* carrier. In this vault, clipped forum posts and tweets often carry the thesis or framing in the (concept-level) title and only a short elaboration in the body; the title is content, not a label. So decompose title + body jointly — the title supplies context the body assumes.

This has a limiting case: a **degenerate source** whose body is empty or near-empty but whose title is a self-contained claim. Handle by branch:
- **Recoverable** — empty body but a `source:` URL that's a failed clip or an un-expanded link-stub → stop and route to refetch / `expand-link-stubs`; don't absorb the lossy title when the real content is one fetch away.
- **Title is a self-contained claim**, no recoverable body → treat the title as legitimate promotable content and run the normal merge > create > cite decision on it (still apply the delta test in Step 2; annotate any resulting `## References` entry as title-derived).
- **Title is only a topic label** (no claim) → Skip; say so in the report.

Routing (Step 1) and decomposition (Step 2) are **interleaved, not sequential**: the source's candidate topics drive which wiki regions to survey, and the surveyed structure drives how the source is split. For a rich source, expect a second, narrower Step 1 pass once decomposition reveals a unit whose subject wasn't in the initial survey.

## Step 1: Route

Find where in `wiki/` this knowledge belongs and whether a note on the subject already exists:

1. **Candidate discovery** — delegate retrieval to the **`/research-notes` skill**; it owns the strategy (index browsing + multi-query expansion + union/dedupe/rerank). Invoke it with these constraints (they override its defaults):
   - **Lookup-only mode** — return ~top 10 titles + paths; no synthesis.
   - **Console-only** — do NOT persist a wiki (that default would recurse through `/wiki`).
   - **Scoped to `wiki/`** — browse `index/wiki/root_index.md` only and restrict searches with `--folder wiki`.
2. **Folder routing** — from the same `index/wiki/root_index.md` browsing, pick the target section by its `Description`, using the **Section Tree** at the top of the root index to see the hierarchy. **Prefer the deepest section whose Description fits** — a subject that fits a subsection belongs there, not in the parent. Curated descriptions (from `Overview of <Folder>` notes) are authoritative and state boundaries ("X lives elsewhere") — respect them; generated descriptions are hints. **The Section Tree is coarser than the real folder tree**: small folder subtrees (≤20 notes) don't get their own section — their notes are absorbed into the nearest ancestor section — so the deepest *section* may be shallower than the deepest existing *folder*. Before settling on a create-target, open the chosen section's index under `~/notes/index/wiki/section_indices/` and check the listed note `Path`s: if an existing subfolder there fits the subject better than the section's own folder, create the note in that subfolder. The chosen folder prefix is the create-target if no merge candidate exists; also check the section's `Subsections:` line before settling on a level.

Read the top candidate wiki notes (at least skim overview blockquote + headings) before deciding.

## Step 2: Decompose Against the Knowledgebase, Then Decide (per insight)

**The unit of promotion is the insight, not the source file — and an insight is a *delta* relative to the existing knowledgebase, not an intrinsic property of the source.** Do not decompose the source in isolation. Decompose it *against* the structure surfaced in Step 1:

- **Segment along existing boundaries.** Use the candidate wiki notes and section scopes from Step 1 as the segmentation grid: a passage that maps onto an existing note (or a section of one) is its own unit; passages with no existing home stay aggregated, and form a separate unit only if they cohere into a genuinely new subject.
- **Extract the delta, not the content.** Before merging a unit, check what its target note already says — promote only what is new relative to it (new evidence, a stronger formulation, an update, a counterpoint). If the wiki already covers it, that unit becomes Skip or Cite.
- **Let the KB force splits the source doesn't make.** If the source treats two things as one thread but your wiki keeps them in different homes (e.g. an essay mixing an AI coding workflow with career strategy), that structural mismatch is itself the signal to split.

Most sources yield one unit; rich sources (interviews, long threads, conversation logs) often yield several with *different* wiki destinations. Then decide per insight:

| Decision | When | Action |
|----------|------|--------|
| **Merge** (default) | An existing wiki note covers the same subject and the insight adds evidence, nuance, an update, or a counterpoint | Edit that wiki note in place |
| **Create** | Genuinely new subject — no wiki note covers it and it doesn't fit as a section of an existing one | New article via the `/wiki` skill |
| **Cite** | Insight is only marginally useful — worth a pointer, not integration | Add one annotated reference line to the closest wiki note |
| **Skip** | Insight adds nothing (duplicate content, no lasting value) | Do nothing; say so in the report |

A single source note may therefore fan out to several targets — e.g. an interview clipping contributing a framework to `Investment/Investment system/...`, a ticker fact to its `Micro fundamentals/.../<TICKER>/` note, and a workflow idea to `Strategy/...`. Every note receiving an integrated insight (merge or create) gets the same `source:` reference entry (Step 3), so the raw note's backlinks show everywhere it contributed; Cite targets instead get a plain annotated entry without the `source:` prefix, since the raw note is a pointer there, not integrated source material.

**Guard against over-splitting.** Split only when the insights are genuinely separable and each has a *different* clear home. A coherent argument must stay intact in one note — put the full argument in its best home and let the other notes link to it (`[[...]]` in their References or body) rather than scattering fragments that are individually meaningless. When torn:

- merge vs create → prefer merge (a new `## Section` inside an existing note beats a new sibling note)
- split vs single-home → prefer single-home with cross-links (a link is cheaper than a fragment, and reversible)

## Step 3: Execute

**Language:** Write in the **dominant language of the material**. For **Merge/Cite**, match the destination wiki note's existing language (don't flip a Chinese note to English because one new source differs). For **Create**, use the source note(s)' dominant language — mainly-Chinese sources → a Chinese article (prose, headings, title/filename/H1); mostly-English sources → English. `## 📚 目录` and `## References` stay verbatim regardless; keep tool/API/product names in their original form. (`/wiki` applies the same rule in its Step 2c.)

**Merge:**
- Integrate the insight into the right section of the existing wiki note (or add a new section). Preserve the note's voice and structure; be specific and concrete, not a bolted-on summary.
- Add the source to `## References` annotated with a `source:` prefix: `- [[raw note title]] — source: <what it contributed>`.
- If the note still uses the legacy `## 参考资料` heading, rename it to `## References` as part of the update.
- Bump `updated:` in frontmatter (add the field if missing; keep `date` unchanged).
- Update the note's TOC (`## 📚 目录`) if headings changed.

**Create:**
- Invoke the `/wiki` skill with: the routed target folder, the source note path(s), and a note that the merge-over-create duplicate check has already been done (so it doesn't repeat Step 2 of that skill).

**Cite:**
- Add one line to the closest wiki note's `## References`: `- [[raw note title]] — <one-line relevance>`. Bump `updated:` only if the reference is substantive.

**Never:**
- Modify or move the raw source note — `raw/` is append-only evidence; the watcher and `notes-organize` own its placement.
- Add a `sources:` frontmatter field — provenance lives only in `## References`.
- Keep two wiki copies of the same subject — if you find an existing duplicate pair, merge them (or flag it in the report if the merge is large).

## Step 4: Report

For each source note, report its insight breakdown: per insight, the decision (merge/create/cite/skip), the target wiki note path, and a one-line rationale. For merges, summarize what changed in each touched wiki note. Flag any structural issues noticed along the way (duplicate homes, overloaded folders, missing Overview notes) for the periodic review — do not restructure folders as part of an absorb.

## Batch Mode

For "absorb my recent notes about X" style requests, find candidates the same way Step 1 does — delegate to the **`/research-notes` skill** (it owns multi-query expansion + union/dedupe; a single `notes-search` call would miss synonym and bilingual notes) with these constraints:

- **Lookup-only mode** — return ~top 20 titles + paths; no synthesis.
- **Console-only** — do NOT persist a wiki.
- **Scoped to `raw/`** — restrict searches with `--folder raw`, sorted by time (most recent first).

List the candidates with your proposed per-note decisions, then execute. For large batches (>10 notes), show the decision list and get user confirmation before executing.
