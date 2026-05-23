---
name: research-notes
description: Use when the user asks to research a topic, find information, or answer questions using their local Obsidian notes vault, or wants research findings written up as a wiki article in their vault
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

This workflow has **two modes**:

1. **Default mode: index + search.** Use two parallel data sources: index browsing and keyword search. Run them concurrently (read section indices in parallel with search queries), then merge results in the union step.
2. **Search-only mode: skip index.** If the user explicitly asks to skip the index, avoid index browsing, use only `notes-search`, and say in the final answer that index coverage was intentionally skipped.

- **Index browsing** gives complete coverage of relevant folders and catches notes that use different vocabulary than any search query. It also provides note-type metadata and one-line summaries for quick relevance assessment without reading the full note.
- **Keyword search** catches notes scattered across OTHER folders that index browsing wouldn't surface, and provides BM25 scores for ranking.

In default mode, neither source alone is sufficient. The index misses notes in unexpected folders; search misses notes that use synonyms not in any query.

Use **search-only mode** when the user's prompt contains instructions such as:
- "skip index"
- "search only"
- "just use notes-search"
- "don't browse the index"
- "use the search engine only"

When using search-only mode, compensate by running a broader query sweep than usual: add extra synonyms, title variants, bilingual terms, ticker/company variants when relevant, and sub-concepts. For top-N requests, still apply the final top-N cap only after unioning and deduping all search-query results.

### Output Destinations

Independent of the two search modes above, there is a second axis: **where the findings go**.

1. **Console (default).** The synthesis is written to the response only. Right for quick lookups, exploratory questions, and any prompt that doesn't ask for a persisted artifact.
2. **Wiki (opt-in).** After the normal console synthesis, the findings are also persisted as a wiki article in the user's Obsidian vault by delegating to the `/wiki` skill. See **Step 7: Persist as Wiki** below for the handoff details.

Use **wiki output** when the user's prompt contains instructions such as:
- "save as a wiki" / "save it as a wiki"
- "write up" / "write it up" the findings
- "turn it into a wiki" / "turn this into a wiki article"
- "then `/wiki` it" / "and `/wiki` the result"
- "document what my notes say about …"
- "create a wiki article on …" (when paired with research)

A bare "research X" or "find notes about X" stays console-only. When the user's intent is ambiguous, default to console — do not auto-promote to a wiki, since the vault should not fill up with throwaway summaries.

### Track A: Index Browsing

#### Step A1: Identify Relevant Sections

Read the root index to find sections related to the research topic. **Use the Read tool** (not `cat`) so the full file is loaded without rtk rewriting or any output truncation:

```
Read ~/notes/index/raw/root_index.md
```

The root index is ~1100 lines; the Read tool's default 2000-line limit covers it. Do not pipe it through `cat`, `head`, or any shell tool — the rtk PreToolUse hook rewrites `cat` to `rtk read`, and any caller that wraps the output (subagent summaries, etc.) may clip it.

The root index lists sections with:
- Folder prefix (e.g., `raw/AI/Agent/harness`)
- Note count
- Section themes
- Representative notes with wiki-links

Scan for sections whose folder name, themes, or representative notes relate to the topic. Include adjacent sections — for CPU investment, check not only `AI Chips & Foundry` but also sub-folders like `AMD/`, `INTC/`, `ARM/`, and related sections like `macro analysis/AI/`.

#### Step A2: Select Candidates from Section Indices

For each relevant section, read the section index with the **Read tool** (not `cat`):

```
Read ~/notes/index/raw/section_indices/raw-investment-candidates-ai-chips-foundry.md
```

Largest section indices are ~1100 lines, within the Read tool's default 2000-line limit. Same reason as the root index: avoid `cat`/`head` so nothing in the rewrite/wrap chain can truncate the file.

Section indices contain per-note metadata:
- Path: exact file path
- Tags: note tags
- Type: `note`, `clipping`, `research paper`, `personal synthesis`, etc.
- Summary: one-line summary of the note

**Scan summaries and titles to select candidates.** Pick notes whose title or summary is relevant to the research topic — even if they wouldn't match any keyword search. This is the index's main advantage: it catches vocabulary mismatches (e.g., a note titled "AMD FA 大涨的部分原因" is about a CPU company's stock but wouldn't match "CPU" searches).

**Adaptive index budget.** How many candidates to select from the index depends on the requested top-N:
- **N ≤ 15:** select up to **2×N** candidates from index summaries
- **15 < N ≤ 50:** select up to **1.5×N** candidates (rounded up)
- **N > 50:** select up to **N** candidates

These are upper bounds — only select notes that are genuinely relevant based on their summary. The budget is generous because deduplication with search results will shrink the pool, and having more index candidates improves recall for notes that search would miss.

### Track B: Keyword Search

#### Step B1: Construct Search Queries

For normal keyword searches, `notes-search` treats multi-word queries as **AND** — every word must appear in the note for it to match. It is not OR, not phrase match. This shapes how to design queries.

**The default is always multiple queries, then union + dedupe.** This applies even to seemingly simple asks like "latest 10 notes about X" or "top N notes on Y". A single query — no matter how well-chosen — only surfaces notes containing that exact term. Notes using a synonym (光互连 vs 光通信), the other language (optical communications vs 光通信), or a sub-concept (CPO, silicon photonics, EML) will be missed. **Never satisfy a research request with a single `notes-search` call unless prompted to do so.** Run at least 5–8 separate queries (10–15 for broad or bilingual investment topics) covering synonyms, both languages, and key sub-terms, then union and dedupe results before applying any `--limit` or top-N cap.

**Advanced FTS5 syntax is an exception, not the default.** The FTS5 engine supports full FTS5 query syntax, but use it only when the user's prompt includes explicit search-query constraints that are awkward to express with ordinary multi-query sweeps, such as excluding titles containing a keyword or key phrase. Example: for "CPU investment but exclude quick screen notes", pair each normal query with an FTS5 exclusion such as `NOT (title:"quick screen")`. Always wrap field filters in parentheses, e.g. `(title:memory cycle)` or `(title:"memory cycle")`, so they parse robustly. For syntax details, read `references/fts5-search-syntax.md`; otherwise keep using the multi-query workflow above.

**How to build the query list — follow these steps in order:**

1. **Identify the research topic and its framing.** The user's prompt has two parts: the *subject* (e.g., 内存, 光通信, agent harness) and the *framing* (e.g., 周期/cycle, 产业趋势/industry trends, engineering). Both matter. A request about "内存周期" is about memory *cycles* specifically — not memory in general. Keep the framing in mind throughout.

2. **List topic-name synonyms in both languages.** Write down every way the topic is named — Chinese, English, abbreviations. Include synonyms of both the *subject* and the *framing*. For 内存周期: the subject (内存/存储/memory) and the framing (周期/cycle/supercycle/超级周期) combine into: 内存周期, 存储周期, memory cycle, 存储超级周期, memory supercycle. For 光通信产业趋势: 光通信, 光互连, optical communications, optical networking.

3. **For each compound Chinese term, also create a word-split variant.** CJK unigram tokenization indexes `内存周期` as `内 存 周 期` — four separate tokens. In practice, `内存` and `周期` may appear in different parts of a note. Searching `内存 周期` (two words, AND) catches these. **Always run both**: the unsplit compound and the meaningful word-split. More examples: `光通信` + `光 通信`, `存储周期` + `存储 周期`, `人工智能` + `人工 智能`. Split at word boundaries, not into single characters.

4. **Identify 3–5 core sub-concepts.** These are the major sub-segments or technical pillars of the topic. For memory/storage: DRAM, HBM, NAND. For optical communications: CPO, silicon photonics, 光模块, 硅光. For agent harness: harness engineering, agent loop, coding agent.

5. **Qualify sub-concept queries based on how specific the research framing is.** The decision depends on the *framing* part of the topic (周期, 产业趋势, engineering, etc.):
   - **Specific framing (e.g., 周期/cycle, 估值/valuation, 缺货/shortage):** The framing narrows what the user cares about — they don't want all notes mentioning the sub-concept, only those discussing it in that specific context. Pair each sub-concept with the framing: `HBM 周期`, `HBM cycle`, `NAND 周期`, `NAND cycle`, `NAND supercycle`, `DRAM 周期`, `DRAM cycle`. Bare `HBM` or `NAND` would flood results with notes about the technology in general (specs, products, supply chain) that have nothing to do with cycles.
   - **General framing (e.g., 产业趋势/industry trends, 产业链/value chain, landscape):** The framing is broad enough that any note primarily about a sub-concept is likely relevant. Use sub-concepts standalone: `CPO`, `silicon photonics`, `光模块`, `硅光`. A note about CPO is inherently a note about optical communications industry trends.
   - **Rule of thumb:** If the framing term would meaningfully filter out irrelevant notes when paired with the sub-concept, pair them. If the sub-concept alone already implies the topic, use it bare.

6. **Do NOT add ticker-specific queries unless the research topic is about that ticker or company.** A request about "内存周期" is about the memory cycle thesis, not about MU or SK Hynix specifically. Ticker queries (MU, SNDK, 000XXXX) pull in earnings notes, price targets, and portfolio commentary that mention the ticker but aren't about the cycle thesis. Only add tickers when the user's topic names a specific company or stock.

7. **Compile the final query list.** You should have:
   - 2–4 topic-synonym queries (step 2), each with word-split variants (step 3)
   - 3–5 qualified sub-concept queries (step 5), in both languages where applicable
   - Total: ~10–15 queries for bilingual investment topics, ~5–8 for focused technical topics

**Query construction principles:**

1. **Run multiple narrow queries, not one long one.** A query like `光通信 CPO silicon photonics` only matches notes containing *all three* terms. Use 1–2 carefully chosen terms per query.

2. **Search both Chinese and English keywords in separate queries.** The vault contains notes in both languages. `光通信` and `optical communications` surface different populations.

3. **Mixed Chinese + English in one query is fine when the English term is a term-of-art that Chinese authors leave untranslated.** Queries like `光通信 CPO`, `存储 HBM`, `硅光 InP` usefully narrow to Chinese-language notes engaging with the English vocabulary.

4. **Avoid pairing a Chinese term with its direct English translation** in the same query (e.g. `光通信 optical communications`). Authors pick one or the other, so AND returns near-empty.

#### Step B2: Run Searches with CLI

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

### Step 4: Union, Deduplicate, and Rerank

You now have candidates from one or two sources:
- **Default mode:** index browsing (Track A) and keyword search (Track B)
- **Search-only mode:** keyword search (Track B) only

Candidates are **unioned**, not intersected — a note appearing in *any* enabled source is a candidate.

1. **Union all candidates** — concatenate filepaths from every search query's results and, in default mode, from index selections into one list. Do NOT filter to notes that appeared in multiple queries; that defeats the purpose of running synonym/sub-term sweeps.
2. **Dedupe by filepath** — collapse exact-path duplicates. For each note, track:
   - Which source(s) it came from: index-only, search-only, or both. In search-only mode, every candidate is search-only.
   - Which search queries it matched and its best BM25 score
   - Its summary from the index, if available and if index browsing was enabled
3. **Filter out generic and cross-sector notes.** Before ranking, remove or demote two categories:
   - **Generic meta-notes** whose primary subject is not any specific topic: watchlists, portfolio summaries, PEG/valuation screens, glossaries, and other broad reference notes that mention many topics. A note titled "Watchlist Competitive Landscape" will match queries for memory, optical, AI, etc. — but it's not *about* any of those topics.
   - **Cross-sector notes** whose primary subject is a DIFFERENT or BROADER sector but that mention the research topic as one of several areas. For example, a note about the entire semiconductor supply chain that mentions optical communications should rank below notes specifically about optical communications. A note about "AI infrastructure" that mentions memory should rank below notes specifically about memory cycles. The research topic should be the note's PRIMARY subject, not a secondary mention.
4. **Rerank the merged pool.** Use all available signals:
   - **Appeared in both sources** — strong relevance signal. A note selected from the index AND matched by search queries is almost certainly on-topic.
   - **Title relevance:** Does the note's title directly reference the research topic or its core concepts? Notes with topic keywords in the title are almost always more relevant than notes that only mention the topic in passing within the body.
   - **Best `bm25_score`** across queries (lower is better in this CLI). For index-only notes that have no BM25 score, use title and summary relevance instead.
   - **Summary relevance** (for index-sourced notes): The section index provides a one-line summary — use it to judge topical fit for notes that search didn't surface.
   - **Number of search queries matched** — a useful signal but not dominant.
   - Note type (prefer `personal synthesis` and `research paper` for depth)
   - Recency — for time-sorted asks ("latest", "recent"), sort by `frontmatter_sort_time` or `file_mtime` across the unioned set, NOT within a single query's results
5. **Apply top-N cap AFTER union** — if the user asked for "latest 10" or "top N", apply the cap to the unioned/deduped/reranked list. Never apply `--limit N` to a single query and call that the answer.
6. **Verify sub-concept coverage.** After selecting the top N, check that each core sub-concept from your query plan has at least one representative in the list. For example, if you ran queries for CPO, silicon photonics, 光模块, and 光互连, verify that the top 10 includes notes covering each of these angles — not just notes that happened to match the broadest query. If a sub-concept query returned a strong result (top 3 of that query with a good BM25 score) but no note from that sub-concept made the final list, replace the weakest entry in the top N with the best result from the underrepresented sub-concept. This prevents the broadest queries from monopolizing the top N and ensures the final list covers the topic's full breadth. **In default mode, also check that index-only notes got fair consideration** — if the index surfaced relevant notes that no search query matched, at least one should appear in the top N if its summary is clearly on-topic.
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
2. Identify key themes and insights across notes; note any contradictions or nuances
3. Lead with the main insight or answer
4. Support with specific evidence from notes — cite note titles when making claims
5. Report coverage breadth (e.g., "Based on 45 notes across 3 batches from your vault...")
6. Highlight any gaps or areas with limited coverage
7. If search-only mode was used, mention that index browsing was intentionally skipped
8. If wiki output mode was active (Step 7), also report the wiki's final file path returned by `/wiki`, so the user can open the persisted article

### Step 7: Persist as Wiki (Conditional)

Run this step **only when the user's prompt triggered wiki output mode** (see **Output Destinations** above). Otherwise, the workflow ends at Step 6.

Console output happens first — the user always sees the synthesis in the response. The wiki is an *additional* artifact, not a replacement.

Delegate to the `/wiki` skill via the Skill tool rather than writing the wiki file directly. `/wiki` owns folder selection, title uniqueness, frontmatter, the `[[#Heading]]` TOC format, and the References section convention — reimplementing any of that here would drift.

**Keep the invocation prompt deliberately slim.** The synthesis was just printed in this same turn, so it is already the most recent assistant content in the conversation; `/wiki`'s Step 1 ("Review the current conversation for relevant answers, analysis, and references") will pull from it via recency. Inlining the synthesis again duplicates content and dilutes `/wiki`'s own SKILL.md instructions in its attention budget — which empirically produces worse articles than calling `/wiki` fresh in a follow-up turn. The slim handoff approximates that follow-up-turn behavior while keeping the workflow single-shot.

Invoke `/wiki` with a prompt containing only:

1. **Topic pointer.** One line stating the research topic and instructing `/wiki` to base the article on the synthesis just printed above in this conversation. Do **not** re-inline the synthesis.

2. **Source notes list.** Every note read in Step 5, with its vault path and (where available) one-line description of why it's relevant. This is the one item `/wiki` cannot reliably reconstruct from recency — Step 5 note paths are scattered across earlier tool results. Format each entry so `/wiki` can drop it into the `## 参考资料` section with minimal transformation:
   ```
   - [[<note title>]] — <why it's relevant to this research>
   ```

3. **Coverage caveat (only if search-only mode was used).** Pass a single-sentence flag so `/wiki` includes the standard caveat ("index browsing was intentionally skipped, so notes that use unusual vocabulary may be undercovered") in the wiki body or overview. Omit entirely when default mode was used.

Do **not** pass a title hint or folder suggestion — `/wiki` derives the title from the body content per its uniqueness rules, and picks the folder via its own `find ~/notes/wiki -type d` check. Leave both decisions entirely to `/wiki`.

After `/wiki` returns, append its reported file path to the console output so the user knows where the artifact landed.

## Example Usage

### Small research: "Research what my notes say about agent harnesses"

**Track A (index):** N is open-ended, treat as ~20. Budget: 2×20 = 40 index candidates.
1. Read `~/notes/index/raw/root_index.md` → find `raw/AI/Agent/harness` section (21 notes)
2. Read `~/notes/index/raw/section_indices/raw-ai-agent-harness.md` → scan summaries, select all 21 (all relevant to topic)

**Track B (search):** Run in parallel with Track A.
3. Run `notes-search search "agent harness" --limit 30 --json`, `"coding agent"`, `"agent loop"`, etc.

**Merge:**
4. Union index candidates + search results, dedupe → ~30 unique candidates
5. Rerank using BM25 scores (search hits) + summary relevance (index hits)
6. Check sizes: `wc -c` → total ~60KB, fits in one batch
7. Read all notes, synthesize

### Top-N research: "Find the top 10 posts about CPU stock investment"

**Track A (index):** N=10, budget: 2×10 = 20 index candidates.
1. Read root index → find `raw/investment/candidates/AI Chips & Foundry` (74 notes), plus sub-sections for AMD, INTC, ARM, QCOM
2. Read section indices → scan all 74 summaries, select ~20 whose title/summary relates to CPU investment (e.g., "AMD FA 大涨的部分原因" wouldn't match "CPU" searches but IS about a CPU company)

**Track B (search):** Run in parallel with Track A.
3. Run 10–13 queries: `"CPU 投资"`, `"CPU stock"`, `"服务器 CPU"`, `"server CPU"`, `"CPU demand"`, `"CPU 需求"`, `"Intel investment"`, `"AMD investment"`, `"ARM CPU"`, `"CPU 芯片"`, etc.

**Merge:**
4. Union ~20 index candidates + ~60 search hits, dedupe by filepath → ~50 unique
5. Rerank: notes in both sources rank highest; then by title relevance + BM25 + summary; filter out generic watchlist/glossary notes
6. Verify sub-concept coverage (AMD, Intel, ARM, QCOM each represented)
7. Take top 10

### Large research: "Research my top 100 notes on investment"

**Track A (index):** N=100, budget: N = 100 index candidates.
1. Read root index → find all investment-related sections (candidates, macro analysis, trading strategy, etc.)
2. Read section indices for those sections → select ~100 most relevant by summary

**Track B (search):** Run in parallel.
3. Run `notes-search search "investment" --limit 100 --json` plus topic-specific queries

**Merge:**
4. Union index + search, dedupe → ~150 candidates
5. Rerank, take top 100
6. Check sizes: `wc -c` → total ~400KB → split into 5 batches of ~80KB
7. Process each batch, merge summaries, synthesize

### Recent-focused: "What are my latest 10 notes on AI agents?"

Even though the user asked for just 10 notes, **do not** run a single query and cap at 10 — that misses notes using synonym terms.

**Track A (index):** N=10, budget: 2×10 = 20 index candidates.
1. Read root index → find `raw/AI/Agent` and sub-sections
2. Read section indices → select ~20 notes, noting their timestamps for recency sorting

**Track B (search):** Run in parallel with Track A.
3. Run multiple time-sorted queries, each with `--sort time --limit 30 --json`:
   ```bash
   notes-search search "AI agents" --sort time --limit 30 --json
   notes-search search "agent" --sort time --limit 30 --json
   notes-search search "autonomous agents" --sort time --limit 30 --json
   notes-search search "agent harness" --sort time --limit 30 --json
   notes-search search "LLM agent" --sort time --limit 30 --json
   ```

**Merge:**
4. Union index + search, dedupe by filepath
5. Sort the unioned set by `frontmatter_sort_time` (fallback `file_mtime`) descending
6. Take the top 10 from the unioned sorted list

The same pattern applies for bilingual topics — add Chinese synonym queries alongside English ones before unioning.

### Search-only: "Find the top 10 notes about CPU stock investment, skip index"

When the user explicitly asks to skip the index, do not read `root_index.md` or section indices.

1. Run a broader-than-usual set of search queries with generous per-query limits:
   ```bash
   notes-search search "CPU 投资" --limit 30 --json
   notes-search search "CPU stock" --limit 30 --json
   notes-search search "服务器 CPU" --limit 30 --json
   notes-search search "server CPU" --limit 30 --json
   notes-search search "CPU demand" --limit 30 --json
   notes-search search "CPU 需求" --limit 30 --json
   notes-search search "Intel investment" --limit 30 --json
   notes-search search "AMD investment" --limit 30 --json
   notes-search search "ARM CPU" --limit 30 --json
   notes-search search "QCOM CPU" --limit 30 --json
   notes-search search "CPU 芯片" --limit 30 --json
   notes-search search "AI CPU" --limit 30 --json
   ```
2. Union all search results, dedupe by filepath, and rerank by title relevance, best BM25 score, number of matched queries, sub-concept coverage, note depth, and recency if relevant.
3. Filter generic meta-notes and cross-sector notes whose primary subject is not CPU stock investment.
4. Verify coverage across the major CPU angles surfaced by the query plan (for example AMD, Intel, ARM, QCOM, server CPU demand, AI inference/agentic AI).
5. Read the selected notes and synthesize as usual.
6. In the final answer, include a brief coverage note such as: "Search-only mode used; index browsing was intentionally skipped, so notes that use unusual vocabulary may be undercovered."

### Wiki output: "Research the memory cycle thesis and save it as a wiki"

The trigger phrase "save it as a wiki" activates wiki output mode (in addition to the default index + search mode).

1. Run Steps 1–6 as usual: index browsing + multi-query search on `内存周期`, `存储周期`, `memory cycle`, `memory supercycle`, `HBM 周期`, `NAND 周期`, `DRAM 周期`, etc.; union, dedupe, rerank; read the top candidates; produce a synthesis.
2. Print the console synthesis as usual — the user always sees this first.
3. **Step 7**: Invoke `/wiki` via the Skill tool with a slim prompt containing:
   - Topic pointer: one line — "Write a wiki for the research on the memory cycle thesis just synthesized above in this conversation." Do **not** re-inline the synthesis; `/wiki` picks it up from conversation recency.
   - Source notes list: each note read in Step 5, formatted as `- [[<title>]] — <relevance>`
   - Coverage caveat: omitted (default mode was used, not search-only)
   - No title or folder hint — `/wiki` derives both itself
4. When `/wiki` returns the new file path, append it to the console output so the user can open the persisted article.
