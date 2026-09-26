---
name: absorb
description: Absorb one or more notes from raw/ — or insights from elsewhere — into the wiki/ knowledgebase so it compounds instead of accumulates. Decomposes each source into insights and decides merge vs create vs cite per insight, so one rich source can update several wiki notes. Use when the user says "absorb this note", "promote this note", "inject this into the wiki", "merge this raw note into the wiki", "add this clipping to my knowledgebase", "/absorb <note path or topic>", or asks to distill recent raw notes into the wiki.
---

# Absorb: raw → wiki Injection

Inject knowledge from `raw/` source notes (or the current conversation) into the `wiki/` knowledgebase, following the compounding workflow defined in `~/notes/wiki/Wiki Organization Conventions.md` (the single source of truth — read it if a rule here seems ambiguous).

**Core principle: merge > create > cite.** The wiki compounds by deepening existing conclusions, not by adding siblings. Creating a new note is the exception, not the default.

## Inputs

- One or more raw note paths (e.g. `raw/AI/Agent/some clipping.md`), or
- A topic/folder (e.g. "absorb my recent notes on RL entropy" → see Batch Mode), or
- Insights from the current session that reference raw notes.

Read each source fully, **treating title + body as one unit**. Title means the frontmatter `title`, else the **filename stem**, else the first H1 (the parser's precedence) — for a note without frontmatter the filename is the only carrier. Clipped posts and tweets often put the thesis in the title and only a short elaboration in the body, so the title is content to decompose, not a label.

**Degenerate source** (empty or near-empty body):
- **Recoverable** — a `source:` URL that's a failed clip or un-expanded link-stub → stop and route to a refetch / `notes-search expand-link-stubs`; don't absorb the lossy title when the real content is one fetch away.
- **Title is a self-contained claim** → promotable content; run the normal decision on it (delta test still applies; annotate any resulting `## References` entry as title-derived).
- **Title is only a topic label** → Skip; say so in the report.

## Calling `/research-notes`

Both Step 1 and Batch Mode delegate candidate retrieval to the **`/research-notes` skill** — it owns the strategy (index browsing + multi-query expansion + union/dedupe/rerank); a single `notes-search` call would miss synonym and bilingual notes. Invoke it with these constraints (they override its defaults):

- **Lookup-only mode** — return titles + paths only; no synthesis.
- **Console-only** — do NOT persist a wiki (that default would recurse through `/wiki`).
- **Scoped** — one tree only, via `--folder wiki` or `--folder raw` (and browse only that tree's index).

## Step 1: Route

Find where in `wiki/` this knowledge belongs and whether a note on the subject already exists:

1. **Candidate discovery** — `/research-notes` as above, scoped to `wiki/` (browse `index/wiki/root_index.md` only), ~top 10.
2. **Folder routing** — from the same root index, pick the target section by its `Description`, using the **Section Tree** at the top to see the hierarchy:
   - **Prefer the deepest section whose Description fits** — a subject that fits a subsection belongs there, not in the parent. Check the section's `Subsections:` line before settling on a level.
   - Curated descriptions (from `Overview of <Folder>` notes) are authoritative and state boundaries ("X lives elsewhere") — respect them; generated descriptions are hints.
   - **The Section Tree is coarser than the folder tree**: subtrees of ≤20 notes are absorbed into the nearest ancestor section, so the deepest *section* may be shallower than the deepest existing *folder*. Before settling on a create-target, open the chosen section's index under `~/notes/index/wiki/section_indices/` and check the listed note `Path`s — if an existing subfolder fits the subject better than the section's own folder, create there.
   - The chosen folder is the create-target if no merge candidate exists.

Read the top candidate wiki notes (at least skim overview blockquote + headings) before deciding.

## Step 2: Decompose Against the Knowledgebase, Then Decide (per insight)

**The unit of promotion is the insight, not the source file — and an insight is a *delta* relative to the existing knowledgebase, not an intrinsic property of the source.** Decompose the source *against* the structure surfaced in Step 1, not in isolation:

- **Segment along existing boundaries.** Use the candidate wiki notes and section scopes as the segmentation grid: a passage that maps onto an existing note (or a section of one) is its own unit; passages with no existing home stay aggregated, and form a separate unit only if they cohere into a genuinely new subject.
- **Extract the delta, not the content.** Check what the target note already says — promote only what is new relative to it (new evidence, a stronger formulation, an update, a counterpoint). Already covered → Skip or Cite.
- **Let the KB force splits the source doesn't make.** If the source treats two things as one thread but the wiki keeps them in different homes (e.g. an essay mixing an AI coding workflow with career strategy), that mismatch is the signal to split.
- **Rerun Step 1 when needed.** If decomposition surfaces a unit whose subject wasn't in the initial survey, do a second, narrower routing pass for it — the two steps interleave.

Most sources yield one unit; rich sources (interviews, long threads, conversation logs) often yield several with *different* wiki destinations — e.g. an interview clipping contributing a framework to `Investment/Investment system/...`, a ticker fact to its `Micro fundamentals/.../<TICKER>/` note, and a workflow idea to `Strategy/...`. Then decide per insight:

| Decision | When | Action |
|----------|------|--------|
| **Merge** (default) | An existing wiki note covers the same subject and the insight adds evidence, nuance, an update, or a counterpoint | Edit that wiki note in place |
| **Create** | Genuinely new subject — no wiki note covers it and it doesn't fit as a section of an existing one | New article via the `/wiki` skill |
| **Cite** | Insight is only marginally useful — worth a pointer, not integration | Add one annotated reference line to the closest wiki note |
| **Skip** | Insight adds nothing (duplicate content, no lasting value) | Do nothing; say so in the report |

**Guard against over-splitting.** Split only when the insights are genuinely separable and each has a *different* clear home. A coherent argument stays intact in one note — put it in its best home and let other notes link to it (`[[...]]` in their References or body) rather than scattering fragments that are individually meaningless. When torn:

- merge vs create → prefer merge (a new `## Section` inside an existing note beats a new sibling note)
- split vs single-home → prefer single-home with cross-links (a link is cheaper than a fragment, and reversible)

## Step 3: Execute

**Language (Merge/Cite):** match the destination wiki note's existing language — don't flip a Chinese note to English because one new source differs. `## 📚 目录` and `## References` stay verbatim; keep tool/API/product names in their original form. (Create follows `/wiki`'s Step 2c: dominant language of the sources.)

**Merge:**
- Integrate the insight into the right section of the existing wiki note (or add a new section). Preserve the note's voice and structure; be specific and concrete, not a bolted-on summary.
- Add the source to `## References` with a `source:` prefix: `- [[raw note title]] — source: <what it contributed>`. Every note receiving an integrated insight gets this entry, so the raw note's backlinks show everywhere it contributed.
- If the note still uses the legacy `## 参考资料` heading, rename it to `## References` as part of the update.
- Bump `updated:` in frontmatter (add the field if missing; keep `date` unchanged).
- Update the note's TOC (`## 📚 目录`) if headings changed.

**Create:**
- Invoke the `/wiki` skill with: the routed target folder, the source note path(s), and a note that the merge-over-create duplicate check has already been done (so it doesn't repeat its Step 2).

**Cite:**
- Add one line to the closest wiki note's `## References` **without** the `source:` prefix (the raw note is a pointer there, not integrated material): `- [[raw note title]] — <one-line relevance>`. Bump `updated:` only if the reference is substantive.

**Never:**
- Modify or move the raw source note — `raw/` is append-only evidence; the watcher and `notes-organize` own its placement.
- Add a `sources:` frontmatter field — provenance lives only in `## References`.
- Keep two wiki copies of the same subject — if you find an existing duplicate pair, merge them (or flag it in the report if the merge is large).

## Step 4: Report

For each source note, report its insight breakdown: per insight, the decision (merge/create/cite/skip), the target wiki note path, and a one-line rationale. For merges, summarize what changed in each touched wiki note. Flag structural issues noticed along the way (duplicate homes, overloaded folders, missing Overview notes) for the periodic review — do not restructure folders as part of an absorb.

## Batch Mode

For "absorb my recent notes about X" style requests, find candidates via `/research-notes` as above, scoped to `raw/`, sorted by time (most recent first), ~top 20. List the candidates with your proposed per-note decisions, then execute. For large batches (>10 notes), show the decision list and get user confirmation before executing.
