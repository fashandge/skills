---
name: research-notes
description: Use when the user asks to research a topic, find information, list matching notes, or answer questions using their local Obsidian notes vault, including lookup-only requests for top/latest/relevant note titles and paths or JSON-only result lists, or when the user wants research findings written up as a wiki article in their vault
---

# research-notes

Research topics and answer questions using the local Obsidian notes vault at `~/notes` (symlink to `/Users/jianfuchen/Library/Mobile Documents/iCloud~md~obsidian/Documents/notes`).

## Modes

Three independent axes shape a run. Decide all three up front from the user's prompt.

### Retrieval mode: default (index + search) vs search-only

- **Default mode** runs two retrieval tracks concurrently and unions them: **Track A index browsing** (complete coverage of relevant folders, one-line summaries, catches notes whose vocabulary matches no query) and **Track B keyword search** (catches on-topic notes scattered across other folders, with per-query rankings). Neither alone is sufficient — the index misses notes in unexpected folders; search misses synonyms not in any query.
- **Search-only mode** skips Track A. Use it only when the prompt says so: "skip index", "search only", "just use notes-search", "don't browse the index", "use the search engine only". Compensate with a broader query sweep than usual (extra synonyms, title variants, bilingual terms, ticker/company variants when relevant, sub-concepts), and say in the final answer that index browsing was intentionally skipped.

### Output shape: synthesis vs lookup-only

- **Synthesis** (default): read the selected notes and answer.
- **Lookup-only**: the user asks to find/list top, latest, or relevant notes but explicitly says not to synthesize or read the contents — "just list titles", "return titles with paths", "without any synthesis", "do not include snippets", "JSON only", "exact shape". Run the normal retrieval, fusion, filtering, and top-N selection, then stop at the selected list: do not read note bodies, do not synthesize. Output only the fields requested (default: title and vault-relative path). If JSON-only was requested, the final answer must be valid JSON with no Markdown or prose outside it. For "latest", sort the unioned candidates by effective time before the top-N cap (see Step 1).

### Output destination: wiki (default) vs console-only

- **Wiki** (default for synthesis): print the synthesis in the response, then persist it as a wiki article via the `/wiki` skill (Step 4). A bare "research X" produces both; "save as a wiki" / "write it up" merely reinforce the default.
- **Console-only**: skip the wiki when the prompt says "no wiki" / "don't write a wiki" / "skip the wiki" / "console only" / "just answer" / "don't save it" / "quick lookup" / "just checking" / "don't persist". Lookup-only runs are always console-only (there is no synthesis to persist), as are trivial factual checks where a persisted article would be vault clutter. If it is genuinely ambiguous whether the finding has lasting value, write the wiki.

## Track A: Index Browsing

### Step A1: Identify Relevant Sections

The vault has two generated root indexes, one per source tree:

- `~/notes/index/raw/root_index.md` — source clippings under `raw/` (evidence)
- `~/notes/index/wiki/root_index.md` — the synthesis knowledgebase under `wiki/` (conclusions; sections carry curated scope descriptions from `Overview of <Folder>` notes)

Browse **both** by default. Read only one tree's index when the request is explicitly scoped to it (a `--folder` constraint, "in my wiki", an `/absorb`-driven check against existing wiki notes).

**Always load index files with the Read tool, never `cat`/`head`.** The rtk PreToolUse hook rewrites `cat` to `rtk read`, and any wrapper that summarizes output may clip the file. Root and section indices currently fit within Read's default 2000-line limit; if a Read ever truncates, read the rest with `offset`.

Each root index has a **Section Tree** (nested bullets, every section with its note count, linking to its section file) followed by **per-section blocks** (`## [folder path](section_indices/<file>.md)`) with a `Description` (curated ones are authoritative and may state boundaries; the rest are generated one-liners; a few tiny sections have none), a `Note count`, and optional `Section themes` (shared tags). Sections are disjoint, but medium-grain: a folder subtree of ≤20 notes gets no section of its own and its notes are listed in the nearest ancestor section, so a section can include notes from deeper subfolders. A count labeled `(direct notes only)` means the section has child sections holding the nested notes.

**Two ways to find relevant sections:**

1. **Full Read** of the root index(es). Scan for sections whose folder name, Description, or themes relate to the topic. **When a parent section matches, also take its children from the Section Tree** — reading a parent's section file does NOT cover its subtree. Include adjacent sections too (for CPU investment: not only `AI Chips & Foundry` but siblings like `Memory & Storage` and related macro-analysis branches).
2. **Grep-first** when the topic has distinctive, high-signal keywords (e.g. `光通信`/`optical`/`CPO`, not generic words like "investment"). Build one case-insensitive alternation from the **same query expansion you construct in Step B1** (synonyms, both languages, sub-concepts) and run it over both the root index and the section files:

   ```bash
   grep -inE "光通信|光互连|光模块|硅光|optical|photonic|transceiver|CPO|DWDM|coherent" ~/notes/index/raw/root_index.md ~/notes/index/wiki/root_index.md
   grep -ilE "光通信|光互连|光模块|硅光|optical|photonic|transceiver|CPO|DWDM|coherent" ~/notes/index/raw/section_indices/*.md ~/notes/index/wiki/section_indices/*.md
   grep -nE "^## \[" ~/notes/index/raw/root_index.md   # section-header → section file map (same layout under index/wiki/)
   ```

   Run both greps: the root-index grep hits section paths and Descriptions (mostly English); the section-files grep hits per-note titles and summaries, which is where bilingual recall lives. Under-expanding the pattern is the main failure mode, so err toward more terms. When keywords are generic, the topic is broad, or grep returns suspiciously few sections, fall back to the full Read. A grep miss is also recoverable because Track B's full-vault sweep always runs.

### Step A2: Select Candidates from Section Indices

Read each relevant section index in full (Read tool, e.g. `~/notes/index/raw/section_indices/raw-investment-candidates-ai-chips-foundry.md`). Each lists its assigned notes with `Path`, `Tags` (omitted when none), and a one-line `Summary`. When a section has child sections, its `Section Summary` block carries a `Subsections:` line — if the parent looked relevant, read those too.

**Scan titles and summaries to select candidates** — notes that are on-topic even if they would match no keyword search (e.g. "AMD FA 大涨的部分原因" is about a CPU company's stock but never says "CPU"). That is the index's main advantage.

**Adaptive index budget**, an upper bound scaled to the requested top-N: up to 2×N for N ≤ 15; 1.5×N (rounded up) for 15 < N ≤ 50; N for N > 50. Only select notes genuinely relevant by summary; the budget is generous because deduplication with search results shrinks the pool.

## Track B: Keyword Search

### Step B1: Construct Search Queries

`notes-search` treats a multi-word query as **AND** — every word must appear in the note. Not OR, not phrase match.

**The default is always multiple queries fused into one ranked list**, even for "latest 10 notes about X". A single query only surfaces notes containing that exact term; synonyms (光互连 vs 光通信), the other language, and sub-concepts (CPO, silicon photonics) are all missed. Never satisfy a research request with a single query unless the user asks for one. Plan 5–8 queries for focused technical topics, 10–15 for broad or bilingual investment topics, and run them all through one `search-multi` call (Step B2). The top-N cap is applied after fusion and filtering, never within a single query.

**Seed-note keyword generation.** If the user provides a seed note, wiki article, or report on the topic (or one clearly exists in the vault), read `references/keyword-generation-from-seed.md` first — it covers extracting candidate keywords by priority tier plus the exclusion lists. Its precision test applies even without a seed: for every candidate term ask *"if a note contains this term, is it almost certainly about the topic?"* If no, drop it — one noisy keyword floods the union with off-topic notes.

**Advanced FTS5 syntax is an exception.** Use it only when the prompt has explicit constraints awkward to express with ordinary queries, such as excluding a title phrase: pair each normal query with `NOT (title:"quick screen")`. Always parenthesize field filters, e.g. `(title:"memory cycle")`. See `references/fts5-search-syntax.md`.

**Build the query list in this order:**

1. **Identify the subject and the framing.** "内存周期" has subject 内存 and framing 周期 — it is about memory *cycles*, not memory in general. Both parts matter throughout.
2. **List topic-name synonyms in both languages**, for subject and framing alike, in **separate** queries — `光通信` and `optical communications` surface different note populations. For 内存周期: 内存周期, 存储周期, memory cycle, 存储超级周期, memory supercycle. Do not pair a Chinese term with its direct English translation in one query (`光通信 optical communications`); authors pick one, so AND returns near-empty. Mixed queries are fine when the English term is a term-of-art Chinese authors leave untranslated (`光通信 CPO`, `存储 HBM`, `硅光 InP`).
3. **For each compound Chinese term, also add a word-split variant.** CJK text is indexed as unigrams, but a bare compound on the query side becomes a contiguous phrase match: `内存周期` returns only notes with those four characters adjacent, while `内存 周期` (two words, AND, each matched anywhere) catches notes where they appear apart — a live check found 3 vs 70 matches. Always run both: `光通信` + `光 通信`, `存储周期` + `存储 周期`, `人工智能` + `人工 智能`. Split at word boundaries, not into single characters.
4. **Identify 3–5 core sub-concepts** — the topic's major segments or technical pillars. Memory: DRAM, HBM, NAND. Optical: CPO, silicon photonics, 光模块, 硅光. Agent harness: harness engineering, agent loop, coding agent.
5. **Qualify sub-concept queries by how specific the framing is.** Specific framing (周期/cycle, 估值/valuation, 缺货/shortage) narrows what the user wants, so pair each sub-concept with it: `HBM 周期`, `HBM cycle`, `NAND cycle`, `DRAM 周期`. Bare `HBM` would flood results with product and supply-chain notes unrelated to cycles. General framing (产业趋势/industry trends, 产业链, landscape) is broad enough that any note primarily about the sub-concept is relevant, so use it bare: `CPO`, `silicon photonics`, `光模块`. Rule of thumb: pair when the framing term would filter out irrelevant notes; go bare when the sub-concept alone implies the topic.
6. **No ticker queries unless the topic is that company or stock.** "内存周期" is the cycle thesis, not MU or SK Hynix; ticker queries pull in earnings notes and price targets that mention the ticker but are not about the thesis.
7. **Compile**: 2–4 topic-synonym queries (each with its word-split variant) plus 3–5 qualified sub-concept queries in both languages where applicable. Keep each query to 1–2 terms — `光通信 CPO silicon photonics` matches only notes containing all three. Do not spend queries on English singular/plural variants; the engine auto-expands them (`cycle` ↔ `cycles`).

### Step B2: Run Searches with CLI

Run the whole plan through **one `search-multi` call** — it executes every query, dedupes by filepath, and computes reciprocal rank fusion (RRF) server-side:

```bash
# All planned queries in one call (FTS5 only)
notes-search search-multi "内存周期" "内存 周期" "memory cycle" "HBM 周期" "存储 周期" \
  --json --limit 30 --per-query-limit 30

# Order the fused list by note time (for "latest"/"recent" asks)
notes-search search-multi "AI agents" "agent harness" "LLM agent" --json --sort time --limit 30

# Restrict to a folder
notes-search search-multi "fine-tuning" "LoRA" --folder "raw/AI" --json
```

Each fused result carries `rrf_score` (higher is better), `matched_queries` with the note's 1-based rank in every query it matched, the snippet from its best-ranked query, plus `summary` (when a DB-backed one exists), `file_mtime`, and `frontmatter_sort_time`. The `per_query` field reports each query's `total` vs `returned`. Run `notes-search search-multi --help` and `notes-search search --help` for full flag lists.

Single-query `search` remains useful for probing a candidate keyword's precision (`--limit 5`) and for QMD semantic search:

```bash
notes-search search "how to build autonomous agents" --engine qmd --mode vsearch   # semantic (~1.5s)
notes-search search "agent memory systems" --engine qmd --mode query        # hybrid+rerank (~17s)
```

**When to add QMD queries:** for conceptual or abstract topics where keyword recall is inherently weak ("how I think about position sizing", "lessons from failed trades"), add 1–2 `--engine qmd --mode vsearch` queries as an extra recall source. Merge QMD hits into the candidate pool **by rank, never by score** (Step 1). Skip QMD for well-named concrete topics.

**Sort and limit guidance:**
- `--sort time` only for "recent"/"latest"/time-sensitive asks. On `search-multi` it orders the fused list by effective note time; on single-query `search` it re-sorts only the top 500 relevance-ranked matches, so a recent-but-weakly-matching note can fall outside the pool — one more reason the multi-query plan matters.
- `--per-query-limit` (candidate depth per query before fusion): the default 30 suits most runs. `--limit` (fused list cap): at least 2–3× the requested top-N so the Step 1 filter has slack. For large-scale research raise both (`--per-query-limit 100 --limit 150` or higher).
- **Check `per_query` totals.** If a highly relevant query shows `total` far above `returned` (e.g. 30 of 104), re-run with a larger `--per-query-limit` or split it into narrower variants instead of silently losing candidates.

## Shared Pipeline

### Step 1: Union, Deduplicate, and Rerank

Candidates are **unioned**, never intersected — a note from any enabled track is a candidate.

1. **Take the fused `search-multi` list as the search-side candidates.** The CLI already deduped and computed RRF; do not recompute it, and do NOT filter to notes that matched multiple queries — single-query matches are legitimate, and multi-query presence is already rewarded inside `rrf_score`. Never compare raw `bm25_score` values across queries or engines: single-query FTS5 scores are boosted composites whose scale depends on each query's terms, and QMD scores run in the opposite direction. Merge any QMD hits by rank.
2. **Union with Track A selections** (default mode). For each note track which source(s) it came from — index-only, search-only, or both — and its summary from the search `summary` field and/or the section index.
3. **Filter the shortlist — the mandatory counterweight to RRF.** Generic meta-notes match many queries by construction, so RRF over-ranks them (a live memory-cycle fusion put "Watchlist Competitive Landscape" at #1). On the top ~2–3×N of the fused pool, remove or demote, extending deeper if fewer than N remain:
   - **Generic meta-notes** whose primary subject is no specific topic: watchlists, portfolio summaries, PEG/valuation screens, glossaries, broad reference notes.
   - **Cross-sector notes** whose primary subject is a different or broader sector and that mention the research topic only as one of several areas (a whole-semiconductor-supply-chain note that mentions optical ranks below notes specifically about optical).

   Judge "primary subject" from the `summary` field or the section-index one-liner when available — snippets show keyword context and routinely overstate relevance for passing mentions. Fall back to title + snippet only when no summary exists. A missing summary is neutral; never demote a note solely because the field is absent.
4. **Adjust with the signals the engine can't compute:**
   - **Appeared in both tracks** — strong relevance signal; almost certainly on-topic.
   - **Title relevance** — whether the title is *about* the topic (the engine's title boost only checks term presence). This is also the main signal for index-only notes, which have no `rrf_score`.
   - **Recency** — for "latest"/"recent" asks, use `search-multi --sort time` and slot index candidates in by effective time: `file_mtime` for `wiki/` notes, `frontmatter_sort_time` (falling back to `file_mtime`) for raw notes, matching the CLI's `--sort time` rule.
5. **Apply the top-N cap after union**, to the unioned, deduped, reranked list — never `--limit N` on a single query.
6. **Verify sub-concept coverage.** Check that each core sub-concept from the query plan has at least one representative in the top N. If a sub-concept query returned a strong result (its top 3) but nothing from it made the list, replace the weakest entry with that result. This stops the broadest queries from monopolizing the top N. In default mode, also check that index-only notes got fair consideration: if the index surfaced a clearly on-topic note that no query matched, at least one such note should appear.
7. **Lookup-only: stop here** and output the selected list in the requested shape.
8. **Synthesis: select notes to read** — the top candidates, which may be dozens or hundreds for large research.

### Step 2: Read Relevant Notes (Batched)

**Read what was selected.** Every note selected in Step 1 earned its slot; do not skip notes by filename, folder, or guessed redundancy ("looks like a clipping", "the analytical notes probably cover this"). The only acceptable skip is a concrete observation made after reading (byte-identical duplicate, empty file).

1. **Estimate sizes**: `wc -c` over the selected paths.
2. **Plan batches** by cumulative size: under 80KB read all at once; 80–240KB split into 2–3 batches; 240KB+ split into 4+. Keep each batch under ~80KB (~20K tokens), highest-priority notes in batch 1.
3. **Process each batch**: read all notes, extract key findings, quotes, and insights relevant to the query, and write a batch summary with note-title citations.
4. **Merge batch summaries** into a unified view before synthesis.

### Step 3: Synthesize and Answer

1. If batched, merge batch summaries first, noting which batches covered which sub-topics.
2. Identify key themes and insights across notes; note contradictions and nuances.
3. Lead with the main insight or answer.
4. Support with specific evidence, citing note titles.
5. Report coverage breadth ("Based on 45 notes across 3 batches from your vault...") and highlight gaps or thinly covered areas.
6. If search-only mode was used, say that index browsing was intentionally skipped, so notes with unusual vocabulary may be undercovered.
7. Unless console-only, proceed to Step 4.

### Step 4: Persist as Wiki (Default)

Console output happens first; the wiki is an additional artifact. Delegate to the `/wiki` skill via the Skill tool rather than writing the file directly — `/wiki` owns folder selection, title uniqueness, frontmatter, the TOC format, and the References convention.

**Keep the invocation prompt deliberately slim.** The synthesis was just printed in this turn, so `/wiki`'s "review the current conversation" step pulls it via recency. Re-inlining it duplicates content and dilutes `/wiki`'s own instructions in its attention budget, which empirically produces worse articles. Pass only:

1. **Topic pointer** — one line naming the research topic and telling `/wiki` to base the article on the synthesis printed above. Do not re-inline the synthesis.
2. **Source notes list** — every note read in Step 2, formatted for direct use in `## References`:
   ```
   - [[<note title>]] — <why it's relevant to this research>
   ```
   This is the one thing `/wiki` cannot reconstruct from recency, since the paths are scattered across earlier tool results.
3. **Coverage caveat** — only if search-only mode was used, one sentence so `/wiki` carries the caveat into the article. Omit otherwise.

Do not pass a title hint or folder suggestion; `/wiki` derives both. After it returns, append its reported file path to the console output.

## Examples

### Top-N: "Find the top 10 posts about CPU stock investment"

- **Track A**: budget 2×10 = 20. Root index → `raw/investment/candidates/AI Chips & Foundry` plus its AMD/INTC/ARM/QCOM children; read those section indices and pick ~20 by title/summary (including notes like "AMD FA 大涨的部分原因" that never say "CPU").
- **Track B** (in parallel): `notes-search search-multi "CPU 投资" "CPU stock" "服务器 CPU" "server CPU" "CPU demand" "CPU 需求" "Intel investment" "AMD investment" "ARM CPU" "CPU 芯片" --json --limit 30`
- **Merge**: union; drop generic watchlist/glossary notes RRF over-ranked; both-track notes first, then by `rrf_score` + summary relevance; verify AMD/Intel/ARM/QCOM each represented; take 10.

### Latest-N: "What are my latest 10 notes on AI agents?"

Still a multi-query plan: Track A over the `raw/AI/Agent` sections (~20 candidates, noting timestamps) in parallel with `notes-search search-multi "AI agents" "agent" "autonomous agents" "agent harness" "LLM agent" --json --sort time --limit 30`. Union, slot index candidates in by effective time, take 10.

### Large research: "Research my top 100 notes on investment"

Index budget 100; `search-multi` with `--per-query-limit 100 --limit 150`; union → filter → top 100. `wc -c` shows ~400KB → ~5 batches of ~80KB; merge summaries; synthesize; Step 4 wiki.

### Search-only: "...top 10 notes about CPU stock investment, skip index"

No index reads. One `search-multi` call with the top-N queries plus extra variants (`"QCOM CPU"`, `"AI CPU"`). Filter, verify coverage, read, synthesize, and state that index browsing was intentionally skipped.
