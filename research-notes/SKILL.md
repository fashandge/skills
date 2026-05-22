---
name: research-notes
description: Use when the user asks to research a topic, find information, or answer questions using their local Obsidian notes vault
---

# research-notes

Research topics and answer questions using the local Obsidian notes vault.

## Trigger

Use when the user asks to:
- Research a topic using their notes
- Find information in their vault
- Answer questions based on their collected knowledge
- Synthesize insights from multiple notes

## Vault Location

- Path: `~/notes` (symlink to `/Users/jianfuchen/Library/Mobile Documents/iCloud~md~obsidian/Documents/notes`)

## Research Workflow

### Step 1: Check the Index

Start by reading the root index to find relevant sections:

```bash
cat ~/notes/index/raw/root_index.md
```

The root index lists sections with:
- Folder prefix (e.g., `raw/AI/Agent/harness`)
- Note count
- Section themes
- Representative notes with wiki-links

### Step 2: Drill into Section Indices

For relevant sections, read the section index for detailed note listings:

```bash
# Example: read a section index
cat ~/notes/index/raw/section_indices/raw-ai-agent-harness.md
```

Section indices contain per-note metadata:
- Path: exact file path
- Tags: note tags
- Type: `note`, `clipping`, `research paper`, `personal synthesis`, etc.
- Summary: one-line summary of the note

### Step 3: Construct Search Queries

`notes-search` treats multi-word queries as **AND** — every word must appear in the note for it to match. It is not OR, not phrase match. This shapes how to design queries.

**The default is always multiple queries, then union + dedupe.** This applies even to seemingly simple asks like "latest 10 notes about X" or "top N notes on Y". A single query — no matter how well-chosen — only surfaces notes containing that exact term. Notes using a synonym (光互连 vs 光通信), the other language (optical communications vs 光通信), or a sub-concept (CPO, silicon photonics, EML) will be missed. **Never satisfy a research request with a single `notes-search` call.** Run at least 5–8 separate queries (10–15 for broad or bilingual investment topics) covering synonyms, both languages, and key sub-terms, then union and dedupe results before applying any `--limit` or top-N cap.

**Core principles:**

1. **Run multiple narrow queries, not one long one.** A query like `光通信 CPO silicon photonics` only matches notes containing *all three* terms, missing notes that use 光互连 instead of 光通信, or InP-focused notes that never mention silicon photonics. Use 1–2 carefully chosen terms per query and iterate.

2. **Search both Chinese and English keywords for the same topic, in separate queries.** The vault contains notes in both languages. For an industry like optical communications, run `光通信` and `optical communications` as separate queries — each surfaces a different population of notes.

3. **Mixed Chinese + English in one query is fine — even useful — when the English term is a technical term-of-art that Chinese authors leave untranslated.** Chinese investment/tech notes routinely keep English acronyms inline (CPO, InP, HBM, EML, ZR+, hyperscaler capex, silicon photonics) because translation loses precision. Queries like `光通信 CPO`, `存储 HBM`, `硅光 InP` usefully narrow to Chinese-language notes engaging with the English vocabulary.

4. **Avoid pairing a Chinese term with its direct English translation** in the same query (e.g. `光通信 optical communications`, `硅光 silicon photonics`, `光互连 optical interconnect`). Authors pick one or the other for the same concept, so the AND constraint will return near-empty.

5. **For compound Chinese terms, also search with meaningful word splits.** CJK unigram tokenization inserts spaces between every character, so a compound like `内存周期` is indexed as `内 存 周 期` — four separate unigram tokens. FTS will match it, but only if all four characters appear near each other. In practice, `内存` and `周期` may appear in different parts of a note (e.g., "内存需求" in one paragraph and "超级周期" in another). Searching `内存 周期` (two words, AND semantics) catches these notes while `内存周期` (four unigrams that must all appear) may miss them or rank them poorly. **Always run both**: the unsplit compound as one query, and a space-split version breaking it into meaningful Chinese words as another query. More examples: `光通信` + `光 通信`, `存储周期` + `存储 周期`, `人工智能` + `人工 智能`. Use your knowledge of Chinese word boundaries to split — don't split into single characters.

6. **Give each core sub-concept its own standalone single-term query.** Don't only use sub-concepts as narrowing qualifiers (e.g. `光通信 CPO`); also run `CPO` alone. A standalone query for a sub-concept catches notes where that sub-concept is the primary subject. For memory/storage topics, fire standalone queries for each of: `DRAM`, `HBM`, `NAND`. For optical communications, fire standalone queries for `CPO`, `silicon photonics`, `光模块`. For any topic, identify 3–5 core sub-concepts and give each its own query.

7. **For investment thesis topics, include price/cycle action terms.** Terms like `存储 涨价` (storage price increase), `NAND 缺货` (NAND shortage), `超级周期` (supercycle) capture notes discussing the thesis dynamics rather than just the technology. These are high-signal queries that surface analyst commentary and investment reasoning notes.

**Generating keywords:** For any topic (not just seed-note-based research), apply the keyword selection strategy in `references/keyword-generation-from-seed.md`. The priority tiers (topic synonyms → core technical concepts → sub-segments → tickers → Chinese-market peers) and exclusion list (analyst names, generic macro terms, trading tactics) apply to all research queries. If the user provides a seed note, wiki article, or report, read it first to extract additional candidate keywords.

### Step 3b: Run Searches with CLI

Use the search CLI for keyword or semantic search:

```bash
# Basic FTS5 search (fast, keyword-based)
notes-search search "agent harness"

# JSON output for structured processing
notes-search search "agent harness" --json

# Limit results
notes-search search "reinforcement learning" --limit 10

# Restrict to a folder
notes-search search "fine-tuning" --folder "raw/AI"

# Sort by time (most recent first, uses frontmatter published/created/date then mtime)
notes-search search "agent harness" --sort time --limit 50

# Large research: fetch up to top N results by relevance
notes-search search "investment" --limit 100 --json

# QMD semantic search (slower, ~1.5s, finds conceptually related notes)
notes-search search "how to build autonomous agents" --engine qmd --mode vsearch

# QMD hybrid with LLM reranking (slowest, ~17s, best quality)
notes-search search "agent memory systems" --engine qmd --mode query
```

**Sort and limit guidance:**
- Use `--sort time` only when the user asks about "recent", "latest", or time-sensitive topics
- Use `--sort relevance` (default) for depth and quality
- **Per-query `--limit`:** Set `--limit` to at least 2–3x the requested top-N on each individual query. For "top 10" requests, use `--limit 20` or `--limit 30` per query. The top-N cap is applied AFTER union, not within any single query. Broad sub-concept queries (e.g., `NAND`, `HBM`, `CPO`) often return 30+ hits; use `--limit 30` for these to avoid losing relevant notes that rank lower in one query but would rank highly in the union.
- For large-scale research, use `--limit 100` or higher to get a broad candidate pool

### Step 4: Union and Deduplicate

You will have results from multiple `notes-search` calls (Step 3) plus index sections (Steps 1–2). These are **unioned**, not intersected — a note appearing in *any* query's results is a candidate.

1. **Union all candidates** — concatenate filepaths from every query's results and from index sections into one list. Do NOT filter to notes that appeared in multiple queries; that defeats the purpose of running synonym/sub-term sweeps.
2. **Dedupe by filepath** — collapse exact-path duplicates. Track which queries each note matched (useful for relevance signal).
3. **Filter out generic meta-notes.** Before ranking, remove or demote notes whose primary subject is clearly not the research topic. Common false positives include: watchlists, portfolio summaries, PEG/valuation screens, competitive landscapes, glossaries, and other broad reference notes that mention many topics and therefore match many queries. A note titled "Watchlist Competitive Landscape" or "Watchlist Stocks with PEG Below 1" will match queries for memory, optical, AI, etc. — but it's not *about* any of those topics. Demote these below notes whose titles directly reference the research topic.
4. **Prioritize** — rank candidates by:
   - **Title relevance:** Does the note's title directly reference the research topic or its core concepts? Notes with topic keywords in the title are almost always more relevant than notes that only mention the topic in passing within the body.
   - **Best `bm25_score`** across queries (lower is better in this CLI).
   - **Number of queries matched** — a useful signal but not dominant. Notes that match 3+ queries are often central, but a note matching only 1 query can still be highly relevant if its BM25 score is strong and its title is on-topic.
   - Note type (prefer `personal synthesis` and `research paper` for depth)
   - Recency — for time-sorted asks ("latest", "recent"), sort by `frontmatter_sort_time` or `file_mtime` across the unioned set, NOT within a single query's results
5. **Apply top-N cap AFTER union** — if the user asked for "latest 10" or "top N", apply the cap to the unioned/deduped/sorted list. Never apply `--limit N` to a single query and call that the answer.
6. **Verify sub-concept coverage.** After selecting the top N, check that each core sub-concept from your query plan has at least one representative in the list. For example, if you ran queries for CPO, silicon photonics, 光模块, and 光互连, verify that the top 10 includes notes covering each of these angles — not just notes that happened to match the broadest query. If a sub-concept query returned a strong result (top 3 of that query with a good BM25 score) but no note from that sub-concept made the final list, replace the weakest entry in the top N with the best result from the underrepresented sub-concept. This prevents the broadest queries from monopolizing the top N and ensures the final list covers the topic's full breadth.
7. **Select notes to read** — pick the top candidates (may be dozens or hundreds for large research)

### Step 5: Read Relevant Notes (Batched)

For small sets, read all notes directly. For large sets, batch by file size to stay within context limits.

**1. Estimate sizes** of candidate notes:

```bash
wc -c ~/notes/raw/AI/Agent/harness/*.md
# Or for a specific list of files:
wc -c ~/notes/raw/path/to/note1.md ~/notes/raw/path/to/note2.md
```

**2. Plan batches** by cumulative file size:
- **Under 80KB total**: read all at once (no batching needed)
- **80-240KB total**: split into 2-3 batches
- **240KB+ total**: split into 4+ batches

Group notes so each batch stays under ~80KB (~20K tokens). Order batches so highest-priority notes are in batch 1.

**3. Process each batch**:
- Read all notes in the batch
- Extract key findings, quotes, and insights relevant to the query
- Write a batch summary: bullet points of findings with note title citations

**4. Merge batch summaries** into a unified view before final synthesis.

### Step 6: Synthesize and Answer

After gathering information (directly or via batch summaries):
1. If batched: merge batch summaries first, noting which batches covered which sub-topics
2. Identify key themes and insights across notes
3. Note any contradictions or nuances
4. Cite specific notes when making claims
5. Synthesize a coherent answer or research summary
6. Report coverage (e.g., "Based on 45 notes across 3 batches from your vault...")

## Example Usage

### Small research: "Research what my notes say about agent harnesses"

1. Read `~/notes/index/raw/root_index.md` → find `raw/AI/Agent/harness` section (21 notes)
2. Read `~/notes/index/raw/section_indices/raw-ai-agent-harness.md` → get note summaries
3. Run `notes-search search "agent harness" --limit 50` for additional matches
4. Combine and dedupe → ~30 unique candidates
5. Check sizes: `wc -c` → total ~60KB, fits in one batch
6. Read all 30 notes directly
7. Synthesize findings into a research summary

### Large research: "Research my top 100 notes on investment"

1. Read root index → find investment-related sections
2. Read section indices for those sections
3. Run `notes-search search "investment" --limit 100 --json` for top 100 by relevance
4. Combine and dedupe → ~100 candidates
5. Check sizes: `wc -c` → total ~400KB
6. Split into 5 batches of ~80KB each
7. Process batch 1: read notes, extract key findings with citations
8. Process batches 2-5 similarly
9. Merge batch summaries, then synthesize final research summary

### Recent-focused: "What are my latest 10 notes on AI agents?"

Even though the user asked for just 10 notes, **do not** run a single query and cap at 10 — that misses notes using synonym terms. Instead:

1. Run multiple time-sorted queries in parallel, each with a generous limit (e.g., 30):
   ```bash
   notes-search search "AI agents" --sort time --limit 30 --json
   notes-search search "agent" --sort time --limit 30 --json
   notes-search search "autonomous agents" --sort time --limit 30 --json
   notes-search search "agent harness" --sort time --limit 30 --json
   notes-search search "LLM agent" --sort time --limit 30 --json
   ```
2. Union results, dedupe by filepath, sort the unioned set by `frontmatter_sort_time` (fallback `file_mtime`) descending
3. Take the top 10 from the unioned sorted list — that is the answer
4. (Optional) Read section indices for additional context if synthesizing

The same pattern applies for bilingual topics — add Chinese synonym queries alongside English ones before unioning.

## Output Format

When presenting research findings:
- Lead with the main insight or answer
- Support with specific evidence from notes (cite note titles)
- Note the breadth of coverage (e.g., "Based on 20 notes from your vault...")
- Highlight any gaps or areas with limited coverage
