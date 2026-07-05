---
name: research-notes
description: Use when the user asks to research a topic, find information, list matching notes, or answer questions using their local Obsidian notes vault, including lookup-only requests for top/latest/relevant note titles and paths or JSON-only result lists, or when the user wants research findings written up as a wiki article in their vault
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

This workflow has **three retrieval modes**:

1. **Default mode: index + search.** Use two parallel data sources: index browsing and keyword search. Run them concurrently (read section indices in parallel with search queries), then merge results in the union step.
2. **Search-only mode: skip index.** If the user explicitly asks to skip the index, avoid index browsing, use only `notes-search`, and say in the final answer that index coverage was intentionally skipped.
3. **Agent-engine mode: delegate retrieval to the AI agent search engine.** If the user explicitly asks to use the agent engine, skip index browsing and skip the multi-query FTS5 sweep. Instead, make a single call to `notes-search search "<topic>" --engine agent --json` and treat its results as the full candidate set. See **Track C** below.

- **Index browsing** gives complete coverage of relevant folders and catches notes that use different vocabulary than any search query. It also provides note-type metadata and one-line summaries for quick relevance assessment without reading the full note.
- **Keyword search** catches notes scattered across OTHER folders that index browsing wouldn't surface, and provides per-query rankings plus a DB-backed one-line `summary` field (when one exists) for reranking.

In default mode, neither source alone is sufficient. The index misses notes in unexpected folders; search misses notes that use synonyms not in any query.

Use **search-only mode** when the user's prompt contains instructions such as:
- "skip index"
- "search only"
- "just use notes-search"
- "don't browse the index"
- "use the search engine only"

When using search-only mode, compensate by running a broader query sweep than usual: add extra synonyms, title variants, bilingual terms, ticker/company variants when relevant, and sub-concepts. Search results include a `summary` field when a DB-backed note summary exists, so use that field to judge whether the topic is the note's primary subject instead of relying only on search rank, title, and snippets. For top-N requests, still apply the final top-N cap only after the `search-multi` fusion and the Step 1 shortlist filter.

Use **agent-engine mode** when the user's prompt contains instructions such as:
- "use the agent engine"
- "use the AI agent search engine"
- "use --engine agent"
- "use agent search"
- "delegate the search to the agent engine"

In agent-engine mode, the agent engine has already done its own multi-query retrieval and ranking internally, so do **not** read the index and do **not** run any additional `notes-search` queries (FTS5 or QMD). See **Track C**, which points to `references/agent-engine-mode.md` for the full guidance.

### Output Destinations

Independent of the retrieval modes above, there is a second axis: **where the findings go**.

1. **Wiki (default).** The synthesis is written to the response AND persisted as a wiki article in the user's Obsidian vault by delegating to the `/wiki` skill. Console output always happens first — the wiki is an *additional* artifact, never a replacement. See **Step 4: Persist as Wiki** below for the handoff details. This is the default for any synthesis-mode research request, so a bare "research X" or "find notes about X" produces both a console synthesis and a wiki. Phrases like "save as a wiki", "write it up", or "create a wiki article on …" just reinforce the default; behavior is identical without them.
2. **Console-only (opt-out).** The synthesis is written to the response only, with no wiki persisted. Right for quick lookups, exploratory questions, throwaway checks, and any case where the user signals they don't want a persisted artifact.

Use **console-only mode** (skip the wiki) when the user's prompt contains instructions such as:
- "no wiki" / "don't write a wiki" / "skip the wiki"
- "console only" / "just answer" / "don't save it"
- "quick lookup" / "just checking" / "don't persist"

Two cases are **always console-only** regardless of the above — never write a wiki for them:
- **Lookup-only mode** (see below): there is no synthesis to persist.
- Trivial or throwaway questions where a persisted article would just be vault clutter. When a request is clearly a quick factual check rather than research worth keeping, prefer console-only even without an explicit opt-out; if genuinely ambiguous whether the finding has lasting value, default to writing the wiki rather than silently dropping it.

### Output Shape: Lookup-Only Mode

Use **lookup-only mode** when the user asks to find/list top, latest, or relevant notes but explicitly says not to synthesize or read/analyze the contents. Trigger phrases include:
- "just list titles"
- "return titles with paths"
- "without any synthesis"
- "do not include snippets"
- "JSON only"
- "exact shape"

In lookup-only mode, still perform the normal retrieval, fusion, filtering, and top-N selection rules for the chosen search mode. Then stop at the selected note list:
- Do **not** read the full note bodies in Step 2.
- Do **not** synthesize themes, takeaways, or evidence.
- Output only the fields the user requested. If no schema is specified, use title and vault-relative path.
- If the user requests JSON-only, the final answer must be valid JSON with no Markdown, commentary, rankings, scores, snippets, or prose outside the JSON.
- If the user requests "latest", sort the unioned candidate set by effective time — `file_mtime` for `wiki/` notes, `frontmatter_sort_time` (falling back to `file_mtime`) for raw notes, matching the CLI's `--sort time` rule — before applying the final top-N cap.

### Track A: Index Browsing

#### Step A1: Identify Relevant Sections

The vault has **two generated root indexes**, one per source tree:

- `~/notes/index/raw/root_index.md` — source clippings under `raw/` (evidence)
- `~/notes/index/wiki/root_index.md` — the synthesis knowledgebase under `wiki/` (conclusions; sections carry curated scope descriptions from `Overview of <Folder>` notes)

Browse **both** by default — research questions usually benefit from wiki conclusions *and* raw evidence. When the request is explicitly scoped to one tree (a `--folder` constraint, "in my wiki", an `/absorb`-driven duplicate check against existing wiki notes), read only that tree's index. (The `/wiki` skill's vault check deliberately spans both trees — wiki hits for merge-over-create, raw hits for sources — so it arrives unscoped.)

Read the root index(es) to find sections related to the research topic. **Use the Read tool** (not `cat`) so the full file is loaded without rtk rewriting or any output truncation:

```
Read ~/notes/index/raw/root_index.md
Read ~/notes/index/wiki/root_index.md
```

Each root index is currently well under the Read tool's default 2000-line limit, so a single Read loads it fully. Do not pipe it through `cat`, `head`, or any shell tool — the rtk PreToolUse hook rewrites `cat` to `rtk read`, and any caller that wraps the output (subagent summaries, etc.) may clip it. If a future Read ever truncates (the file has grown past the limit), read it in two chunks with `offset`.

**Token-efficient variant — grep-first when the topic has distinctive keywords.** Loading the full index every time is wasteful when the topic has specific, high-signal terms (e.g. `光通信`/`optical`/`CPO`, not generic words like "investment"). In that case, instead of reading the whole file, first `grep` it to find candidate sections (run over each root index in scope):

```
grep -inE "光通信|光互连|光模块|硅光|optical|photonic|transceiver|CPO|DWDM|coherent" ~/notes/index/raw/root_index.md ~/notes/index/wiki/root_index.md
grep -ilE "光通信|光互连|光模块|硅光|optical|photonic|transceiver|CPO|DWDM|coherent" ~/notes/index/raw/section_indices/*.md ~/notes/index/wiki/section_indices/*.md   # candidate section FILES via note titles/summaries (bilingual)
grep -nE "^## \[" ~/notes/index/raw/root_index.md   # section-header → section_indices/<file>.md map (same layout under index/wiki/)
```

- Build the alternation from the **same query expansion you construct for Track B Step B1** (synonyms, both languages, sub-concepts), OR'd into one case-insensitive `grep -iE` pattern. The more complete the alternation, the lower the miss risk — under-expanding the pattern is the main failure mode, so err toward more terms.
- **Run both greps.** The root-index grep hits section paths (in the Section Tree or `## [...]` headers), Descriptions, and themes; the enclosing section for a hit is the nearest preceding `## [folder](section_indices/<file>.md)` line (use the third grep as the map). The section-files grep (`-l` lists matching files) hits per-note titles and summaries — this is where bilingual recall lives, since generated root Descriptions are mostly English while note titles stay in their original language. Read the union of matched section indices in Step A2.
- **Recall caveat and fallback.** Even both greps can miss a section whose Description, folder name, and note titles all avoid your terms. Two backstops: (1) Track B's full-vault FTS sweep catches on-topic notes regardless of which folder they sit in — it always runs, so a grep miss here is recoverable; (2) when keywords are generic, the topic is broad, or grep returns suspiciously few sections, **fall back to the full `Read` of root_index** for maximum recall. Once a section is selected, Step A2 still **reads its section index in full** (that's where the per-note summaries that catch vocabulary mismatches live).

The root index has two parts:

- A **Section Tree** at the top — a nested bullet list of every section with its assigned-note count, each linking to its section index file. Use it to see the section hierarchy at a glance and pick branches top-down. Note the tree shows *sections*, not the full folder tree — small subfolders are folded into their ancestor's section and don't appear as their own entries.
- **Per-section blocks** (`## [folder path](section_indices/<file>.md)`), sorted by path, each with:
  - `Description` — the section's scope. Curated ones (from the folder's `Overview of <Folder>` note) are authoritative and may state boundaries ("X lives elsewhere"); the rest are generated one-liners. Some tiny or non-routing sections (`raw/inbox`, `raw/daily`) have no description.
  - `Note count` — **sections are disjoint** (every note is listed in exactly one section), but a section is not limited to its folder's direct notes: small folder subtrees (≤20 notes) don't get their own section, so their notes are absorbed into the nearest ancestor section, and splitting only ever goes one folder level deep. A count labeled `(direct notes only)` means the section has child sections and nested notes live there; an unlabeled count silently includes notes from deeper subfolders that have no section of their own.
  - `Section themes` — shared tags, present only when the section's notes have them.

Scan for sections whose folder name, Description, or themes relate to the topic. **When a parent section matches, also take its children from the Section Tree as candidates** — reading a parent's section file does NOT cover its subtree. Include adjacent sections too — for CPU investment, check not only `AI Chips & Foundry` but also sibling sections like `Memory & Storage` and related branches under macro analysis.

#### Step A2: Select Candidates from Section Indices

For each relevant section, read the section index with the **Read tool** (not `cat`):

```
Read ~/notes/index/raw/section_indices/raw-investment-candidates-ai-chips-foundry.md
```

Section indices also fit within the Read tool's default 2000-line limit today. Same reason as the root index: avoid `cat`/`head` so nothing in the rewrite/wrap chain can truncate the file.

Section indices contain per-note metadata:
- Path: exact file path
- Tags: note tags (line omitted when the note has none)
- Summary: one-line summary of the note

A section file lists the notes **assigned** to that section — its folder's direct notes plus, when a subfolder is too small (≤20 notes in its subtree) to earn its own section, all of that subfolder's notes too (check each note's `Path` for its real folder). Sections are disjoint, so no note appears in two section files. When the section *does* have child sections, its `Section Summary` block includes a `Subsections:` line linking them — if the parent looked relevant, its children usually are too; read those as well.

**Scan summaries and titles to select candidates.** Pick notes whose title or summary is relevant to the research topic — even if they wouldn't match any keyword search. This is the index's main advantage: it catches vocabulary mismatches (e.g., a note titled "AMD FA 大涨的部分原因" is about a CPU company's stock but wouldn't match "CPU" searches).

**Adaptive index budget.** How many candidates to select from the index depends on the requested top-N:
- **N ≤ 15:** select up to **2×N** candidates from index summaries
- **15 < N ≤ 50:** select up to **1.5×N** candidates (rounded up)
- **N > 50:** select up to **N** candidates

These are upper bounds — only select notes that are genuinely relevant based on their summary. The budget is generous because deduplication with search results will shrink the pool, and having more index candidates improves recall for notes that search would miss.

### Track B: Keyword Search

#### Step B1: Construct Search Queries

For normal keyword searches, `notes-search` treats multi-word queries as **AND** — every word must appear in the note for it to match. It is not OR, not phrase match. This shapes how to design queries.

**The default is always multiple queries, fused into one ranked list.** This applies even to seemingly simple asks like "latest 10 notes about X" or "top N notes on Y". A single query — no matter how well-chosen — only surfaces notes containing that exact term. Notes using a synonym (光互连 vs 光通信), the other language (optical communications vs 光通信), or a sub-concept (CPO, silicon photonics, EML) will be missed. **Never satisfy a research request with a single query unless prompted to do so.** Plan at least 5–8 queries (10–15 for broad or bilingual investment topics) covering synonyms, both languages, and key sub-terms, then run them all through one `notes-search search-multi` call (Step B2) — it dedupes and rank-fuses them server-side. The top-N cap is applied after fusion and filtering, never within a single query.

**Seed-note keyword generation.** If the user provides a seed note, wiki article, or report on the topic (or one clearly exists in the vault), read `references/keyword-generation-from-seed.md` before building the query list — it covers extracting candidate keywords by priority tier plus the exclusion lists (analyst/publisher names, generic macro terms, cross-cutting tech terms, trading-tactic terms). Its precision test applies even without a seed: for every candidate query term ask *"if a note contains this term, is it almost certainly about the topic?"* — if no, drop it. A single noisy keyword can flood the union with off-topic notes.

**Advanced FTS5 syntax is an exception, not the default.** The FTS5 engine supports full FTS5 query syntax, but use it only when the user's prompt includes explicit search-query constraints that are awkward to express with ordinary multi-query sweeps, such as excluding titles containing a keyword or key phrase. Example: for "CPU investment but exclude quick screen notes", pair each normal query with an FTS5 exclusion such as `NOT (title:"quick screen")`. Always wrap field filters in parentheses, e.g. `(title:memory cycle)` or `(title:"memory cycle")`, so they parse robustly. For syntax details, read `references/fts5-search-syntax.md`; otherwise keep using the multi-query workflow above.

**How to build the query list — follow these steps in order:**

1. **Identify the research topic and its framing.** The user's prompt has two parts: the *subject* (e.g., 内存, 光通信, agent harness) and the *framing* (e.g., 周期/cycle, 产业趋势/industry trends, engineering). Both matter. A request about "内存周期" is about memory *cycles* specifically — not memory in general. Keep the framing in mind throughout.

2. **List topic-name synonyms in both languages.** Write down every way the topic is named — Chinese, English, abbreviations. Include synonyms of both the *subject* and the *framing*. For 内存周期: the subject (内存/存储/memory) and the framing (周期/cycle/supercycle/超级周期) combine into: 内存周期, 存储周期, memory cycle, 存储超级周期, memory supercycle. For 光通信产业趋势: 光通信, 光互连, optical communications, optical networking.

3. **For each compound Chinese term, also create a word-split variant.** CJK text is indexed as unigrams (`内存周期` → `内 存 周 期`), but on the query side a bare compound is wrapped in quotes, so `内存周期` matches those four characters only **contiguously** — a phrase match. `内存` and `周期` often appear in different parts of a note, and the phrase form misses all of those. Searching `内存 周期` (two words, AND, each matched anywhere) catches them — a live check found `内存周期` returning 2 notes vs 50 for `内存 周期`. **Always run both**: the unsplit compound and the meaningful word-split. More examples: `光通信` + `光 通信`, `存储周期` + `存储 周期`, `人工智能` + `人工 智能`. Split at word boundaries, not into single characters.

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

5. **Don't add English singular/plural variants as separate queries.** The engine auto-expands them (`cycle` ↔ `cycles`, `memory` ↔ `memories`), so one form suffices. Spend the query budget on synonyms and sub-concepts instead.

#### Step B2: Run Searches with CLI

**Run the whole query plan through one `search-multi` call** — it executes every query, dedupes by filepath, and computes reciprocal rank fusion (RRF) server-side, returning a single ranked list:

```bash
# Primary invocation: all planned queries in one call (FTS5 only)
notes-search search-multi "内存周期" "内存 周期" "memory cycle" "HBM 周期" "存储 周期" \
  --json --limit 30 --per-query-limit 30

# Sort the fused list by note time instead (for "latest"/"recent" asks)
notes-search search-multi "AI agents" "agent harness" "LLM agent" --json --sort time --limit 30

# Restrict to a folder
notes-search search-multi "fine-tuning" "LoRA" --folder "raw/AI" --json
```

Each fused result carries `rrf_score` (higher is better), `matched_queries` with the note's 1-based rank in every query it matched, the snippet from its best-ranked query, plus `summary`, `file_mtime`, and `frontmatter_sort_time`. The `per_query` field reports each query's `total` vs `returned` counts.

Single-query `search` remains useful for probing (checking a candidate keyword's precision with `--limit 5`) and for QMD semantic search:

```bash
notes-search search "agent harness" --json                                  # single-query probe
notes-search search "how to build autonomous agents" --engine qmd --mode vsearch   # semantic (~1.5s)
notes-search search "agent memory systems" --engine qmd --mode query        # hybrid+rerank (~17s)
```

Run `notes-search search-multi --help` and `notes-search search --help` for the full flag lists.

**When to add QMD queries:** for conceptual or abstract topics where keyword recall is inherently weak (e.g., "how I think about position sizing", "lessons from failed trades"), add 1–2 `--engine qmd --mode vsearch` queries as an extra recall source alongside the FTS5 sweep. Merge QMD hits into the union **by rank, never by score** — QMD scores are higher-is-better and on a different scale from FTS5 (see Step 1). Skip QMD for well-named concrete topics; the multi-query FTS5 sweep covers those.

**Sort and limit guidance:**
- Use `--sort time` only when the user asks about "recent", "latest", or time-sensitive topics. On `search-multi` it orders the fused list by effective note time; on single-query `search` it re-sorts only the top ~500 relevance-ranked matches, so a recent-but-weakly-matching note can fall outside the pool — one more reason the multi-query plan matters.
- Use `--sort relevance` (default) for depth and quality
- **`--per-query-limit`** (candidate depth per query before fusion): the default 30 suits most runs. **`--limit`** (fused list cap): set it to at least 2–3× the requested top-N so the post-fusion filter in Step 1 has slack.
- **Check `per_query` totals in the JSON output.** Each query reports `total` matches vs `returned`. If a highly relevant query shows `total` far above `returned` (e.g., 30 returned of 104), re-run with a larger `--per-query-limit` or split it into narrower variants instead of silently losing candidates.
- For large-scale research, raise both: `--per-query-limit 100 --limit 150` or higher for a broad candidate pool

### Track C: Agent-Engine Retrieval (agent-engine mode only)

**When agent-engine mode triggers, read `references/agent-engine-mode.md` and follow it** — it owns the full invocation guidance (`--limit` semantics, backend variants, worked example). The core invariants:

- Make exactly one call — `notes-search search "<research topic>" --engine agent --json` (add `--limit N` for top-N asks; here it IS the final cap) — and skip Tracks A and B entirely.
- Treat the returned ranked list as the final candidate set: no union, no reranking, no extra FTS5/QMD queries. Every returned note is the Step 2 reading list (see Step 2's no-drop rule).
- Proceed directly to Step 2 → Step 3 → Step 4, and in the synthesis note that retrieval was delegated to the agent engine with index browsing and FTS5/QMD sweeps intentionally skipped.

## Shared Pipeline

After retrieval, all modes converge on these steps. Agent-engine mode skips Step 1 (its list is already ranked and final).

### Step 1: Union, Deduplicate, and Rerank

This step applies only to **default mode** and **search-only mode**.

You now have candidates from one or two sources:
- **Default mode:** index browsing (Track A) and keyword search (Track B)
- **Search-only mode:** keyword search (Track B) only

Candidates are **unioned**, not intersected — a note appearing in *any* enabled source is a candidate.

1. **Take the fused list from `search-multi` as the search-side candidates.** The CLI already deduped by filepath and computed RRF (`rrf_score`, higher is better; per-query ranks in `matched_queries`) — do not recompute it, and do NOT filter to notes that matched multiple queries (single-query matches are legitimate candidates; multi-query presence is already rewarded inside `rrf_score`). Never compare raw `bm25_score` values across queries or engines: single-query FTS5 scores are boosted composites (folder −6.0/−3.0, title, and investment-recency boosts baked in; lower is better) whose scale depends on each query's term count and rarity, and QMD scores flip direction (higher is better). If supplemental QMD queries were run, merge their hits into the candidate pool by rank, never by score.
2. **Union with index candidates** — in default mode, add the Track A selections to the fused list (union, not intersection — a note from *any* enabled source is a candidate). For each note track:
   - Which source(s) it came from: index-only, search-only, or both. In search-only mode, every candidate is search-only.
   - Its summary, if available, from the search result `summary` field and/or from the section index when index browsing was enabled
3. **Filter the shortlist — the mandatory counterweight to RRF.** Generic meta-notes match many queries by construction, so RRF over-ranks them (a live memory-cycle fusion put "Watchlist Competitive Landscape" at #1). On the top ~2–3×N of the fused pool, remove or demote two categories, extending deeper into the fused list if filtering leaves fewer than N:
   - **Generic meta-notes** whose primary subject is not any specific topic: watchlists, portfolio summaries, PEG/valuation screens, glossaries, and other broad reference notes that mention many topics.
   - **Cross-sector notes** whose primary subject is a DIFFERENT or BROADER sector but that mention the research topic as one of several areas. For example, a note about the entire semiconductor supply chain that mentions optical communications should rank below notes specifically about optical communications. The research topic should be the note's PRIMARY subject, not a secondary mention.

   Base this primary-subject judgment on the search result `summary` field (or the section index one-liner) when available — snippets show keyword context and routinely overstate relevance for passing mentions. Fall back to title + snippet only when no summary exists.
4. **Adjust the ranking with the judgment signals the engine can't compute:**
   - **Appeared in both sources** — strong relevance signal. A note selected from the index AND matched by search queries is almost certainly on-topic.
   - **Summary relevance:** Search results may include a DB-backed `summary` field, and section indices provide one-line summaries for index-sourced notes. Use any available summary to judge whether the research topic is the note's PRIMARY subject versus a passing mention or cross-sector aside. If both search and index summaries exist, treat them as complementary signals. A missing summary is neutral — never demote a note solely because the field is absent.
   - **Title relevance:** use it for the primary-subject judgment (the engine's title boost only checks term presence, not whether the title is *about* the topic), and as the main signal for index-only notes that have no `rrf_score`.
   - Recency — for time-sorted asks ("latest", "recent"), use `search-multi --sort time` and slot index candidates in by effective time (wiki notes → `file_mtime`; raw notes → `frontmatter_sort_time`, falling back to `file_mtime`), NOT within a single query's results
5. **Apply top-N cap AFTER union** — if the user asked for "latest 10" or "top N", apply the cap to the unioned/deduped/reranked list. Never apply `--limit N` to a single query and call that the answer.
6. **Verify sub-concept coverage.** After selecting the top N, check that each core sub-concept from your query plan has at least one representative in the list. For example, if you ran queries for CPO, silicon photonics, 光模块, and 光互连, verify that the top 10 includes notes covering each of these angles — not just notes that happened to match the broadest query. If a sub-concept query returned a strong result (top 3 of that query) but no note from that sub-concept made the final list, replace the weakest entry in the top N with the best result from the underrepresented sub-concept. This prevents the broadest queries from monopolizing the top N and ensures the final list covers the topic's full breadth. **In default mode, also check that index-only notes got fair consideration** — if the index surfaced relevant notes that no search query matched, at least one should appear in the top N if its summary is clearly on-topic.
7. **Stop for lookup-only mode** — if the user asked only for titles/paths/JSON and no synthesis, output the selected list now using the requested shape.
8. **Select notes to read** — for synthesis mode, pick the top candidates (may be dozens or hundreds for large research)

### Step 2: Read Relevant Notes (Batched)

For small sets, read all notes directly. For large sets, batch by file size to stay within context limits.

**Read what was selected — don't drop candidates by filename prior.** When the candidate set was chosen by Step 1 (default/search-only) or by the agent engine (Track C), every note on the list earned its slot. Do not skip notes mid-Step-2 based on filename, folder, or guessed redundancy ("looks like a clipping", "the analytical notes probably already cover this"). If the total is large, batch by `wc -c` and read across multiple batches — that is what batching is for. The only acceptable skip reason is a concrete observation made *after* reading: byte-identical duplicate, empty file, etc. This rule is especially load-bearing in **agent-engine mode**, where dropping notes by prior amounts to reranking the agent's output — which Track C forbids.

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

### Step 3: Synthesize and Answer

After gathering information (directly or via batch summaries):
1. If batched: merge batch summaries first, noting which batches covered which sub-topics
2. Identify key themes and insights across notes; note any contradictions or nuances
3. Lead with the main insight or answer
4. Support with specific evidence from notes — cite note titles when making claims
5. Report coverage breadth (e.g., "Based on 45 notes across 3 batches from your vault...")
6. Highlight any gaps or areas with limited coverage
7. If search-only mode was used, mention that index browsing was intentionally skipped. If agent-engine mode was used, mention that retrieval was delegated to the `--engine agent` search and that index browsing plus FTS5/QMD sweeps were intentionally skipped.
8. Unless console-only mode is active (see **Output Destinations**), proceed to Step 4 to persist the wiki

### Step 4: Persist as Wiki (Default)

Run this step for every synthesis-mode research request unless console-only mode is active or the request was lookup-only (see **Output Destinations** — in those cases the workflow ends at Step 3). Console output happens first — the user always sees the synthesis in the response; the wiki is an *additional* artifact.

Delegate to the `/wiki` skill via the Skill tool rather than writing the wiki file directly. `/wiki` owns folder selection, title uniqueness, frontmatter, the `[[#Heading]]` TOC format, and the References section convention — reimplementing any of that here would drift.

**Keep the invocation prompt deliberately slim.** The synthesis was just printed in this same turn, so it is already the most recent assistant content in the conversation; `/wiki`'s Step 1 ("Review the current conversation for relevant answers, analysis, and references") will pull from it via recency. Inlining the synthesis again duplicates content and dilutes `/wiki`'s own SKILL.md instructions in its attention budget — which empirically produces worse articles than calling `/wiki` fresh in a follow-up turn. The slim handoff approximates that follow-up-turn behavior while keeping the workflow single-shot.

Invoke `/wiki` with a prompt containing only:

1. **Topic pointer.** One line stating the research topic and instructing `/wiki` to base the article on the synthesis just printed above in this conversation. Do **not** re-inline the synthesis.

2. **Source notes list.** Every note read in Step 2, with its vault path and (where available) one-line description of why it's relevant. This is the one item `/wiki` cannot reliably reconstruct from recency — Step 2 note paths are scattered across earlier tool results. Format each entry so `/wiki` can drop it into the `## References` section with minimal transformation:
   ```
   - [[<note title>]] — <why it's relevant to this research>
   ```

3. **Coverage caveat (only if search-only mode was used).** Pass a single-sentence flag so `/wiki` includes the standard caveat ("index browsing was intentionally skipped, so notes that use unusual vocabulary may be undercovered") in the wiki body or overview. Omit entirely when default mode was used.

Do **not** pass a title hint or folder suggestion — `/wiki` derives the title from the body content per its uniqueness rules, and picks the folder via its own routing rules. Leave both decisions entirely to `/wiki`.

After `/wiki` returns, append its reported file path to the console output so the user knows where the artifact landed.

## Example Usage

### Top-N research: "Find the top 10 posts about CPU stock investment"

**Track A (index):** N=10, budget: 2×10 = 20 index candidates.
1. Read root index → find `raw/investment/candidates/AI Chips & Foundry` (74 notes), plus sub-sections for AMD, INTC, ARM, QCOM
2. Read section indices → scan all 74 summaries, select ~20 whose title/summary relates to CPU investment (e.g., "AMD FA 大涨的部分原因" wouldn't match "CPU" searches but IS about a CPU company)

**Track B (search):** Run in parallel with Track A.
3. One fused call with 10–13 queries: `notes-search search-multi "CPU 投资" "CPU stock" "服务器 CPU" "server CPU" "CPU demand" "CPU 需求" "Intel investment" "AMD investment" "ARM CPU" "CPU 芯片" --json --limit 30`

**Merge:**
4. Union ~20 index candidates with the fused list (already deduped, RRF-ranked)
5. Filter the shortlist (drop generic watchlist/glossary notes RRF over-ranked); then adjust: both-sources notes rank highest, then by `rrf_score` + summary relevance
6. Verify sub-concept coverage (AMD, Intel, ARM, QCOM each represented)
7. Take top 10

### Recent-focused: "What are my latest 10 notes on AI agents?"

Even though the user asked for just 10 notes, **do not** run a single query and cap at 10 — that misses notes using synonym terms.

1. **Track A:** read root index → `raw/AI/Agent` sections → select ~20 candidates (2×N budget), noting timestamps.
2. **Track B (parallel):** `notes-search search-multi "AI agents" "agent" "autonomous agents" "agent harness" "LLM agent" --json --sort time --limit 30` — fuses all queries, then orders by effective note time.
3. Union with index candidates, slot them in by effective time (wiki notes → `file_mtime`; raw notes → `frontmatter_sort_time`, fallback `file_mtime`), take the top 10.

The same pattern applies for bilingual topics — add Chinese synonym queries alongside English ones before unioning.

### Large research: "Research my top 100 notes on investment"

Same as top-N, scaled: index budget = N = 100; run `notes-search search-multi "investment" <topic-specific queries...> --json --per-query-limit 100 --limit 150`; union with index candidates → filter → top 100. `wc -c` shows ~400KB total → split into ~5 batches of ~80KB, process each, merge summaries, synthesize, then Step 4 (wiki, the default).

### Search-only: "Find the top 10 notes about CPU stock investment, skip index"

Do not read `root_index.md` or section indices. Run a broader-than-usual sweep — one `search-multi` call with the top-N example's queries plus extra variants like `"QCOM CPU"`, `"AI CPU"` — with `--json --limit 30`. Filter the fused shortlist for generic/cross-sector notes, verify sub-concept coverage, read, synthesize. In the final answer include: "Search-only mode used; index browsing was intentionally skipped, so notes that use unusual vocabulary may be undercovered."

### Agent-engine: "Find the top 10 notes about CPU stock investment, use the agent engine"

Read `references/agent-engine-mode.md` and follow its worked example: one `--engine agent --json --limit 10` call, then read every returned note in Step 2 and synthesize.

### Output destination examples

- **"Research the memory cycle thesis"** — wiki output is the default: run the full pipeline, print the console synthesis, then Step 4 delegates to `/wiki` with a slim handoff (topic pointer + source notes list, no inlined synthesis, no title/folder hint) and appends the returned file path to the console output.
- **"Research the memory cycle thesis, no wiki"** — same pipeline, but skip Step 4 entirely; the workflow ends at the console answer. Lookup-only requests ("just list the titles", "JSON only") are also always console-only.
