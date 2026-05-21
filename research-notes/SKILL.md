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

**The default is always multiple queries, then union + dedupe.** This applies even to seemingly simple asks like "latest 10 notes about X" or "top N notes on Y". A single query — no matter how well-chosen — only surfaces notes containing that exact term. Notes using a synonym (光互连 vs 光通信), the other language (optical communications vs 光通信), or a sub-concept (CPO, silicon photonics, EML) will be missed. **Never satisfy a research request with a single `notes-search` call.** Run at least 3–5 separate queries covering synonyms, both languages, and key sub-terms, then union and dedupe results before applying any `--limit` or top-N cap.

**Core principles:**

1. **Run multiple narrow queries, not one long one.** A query like `光通信 CPO silicon photonics` only matches notes containing *all three* terms, missing notes that use 光互连 instead of 光通信, or InP-focused notes that never mention silicon photonics. Use 1–2 carefully chosen terms per query and iterate.

2. **Search both Chinese and English keywords for the same topic, in separate queries.** The vault contains notes in both languages. For an industry like optical communications, run `光通信` and `optical communications` as separate queries — each surfaces a different population of notes.

3. **Mixed Chinese + English in one query is fine — even useful — when the English term is a technical term-of-art that Chinese authors leave untranslated.** Chinese investment/tech notes routinely keep English acronyms inline (CPO, InP, HBM, EML, ZR+, hyperscaler capex, silicon photonics) because translation loses precision. Queries like `光通信 CPO`, `存储 HBM`, `硅光 InP` usefully narrow to Chinese-language notes engaging with the English vocabulary.

4. **Avoid pairing a Chinese term with its direct English translation** in the same query (e.g. `光通信 optical communications`, `硅光 silicon photonics`, `光互连 optical interconnect`). Authors pick one or the other for the same concept, so the AND constraint will return near-empty.

**Generating keywords from a seed note/wiki:**

If the user provides a seed note, wiki article, or report on the topic (or if one exists in the vault), read it first to extract candidate keywords before searching. Score every candidate against a single test: **"if a note contains this term, is it almost certainly about the topic?"** If no, drop it — high recall on the wrong topic is worse than low recall on the right one.

Pick keywords in this priority order. Local search is cheap, so **err on the side of more queries — ~15–20 strong terms is fine, even more if the topic is broad**. The real cost isn't query count, it's letting *weak* terms in: a single noisy keyword can flood the union with off-topic notes. Quantity is free; precision is not.

1. **Topic name + direct synonyms (both languages)** — the canonical labels for the topic itself (光通信 / 光互连 / 光互联 / optical communications / optical networking). Always include both Chinese and English.
2. **Core technical concepts unique to the topic** — terms-of-art whose meaning is the topic (CPO, LPO/NPO, silicon photonics, 硅光, 光模块, InP, EML, CW laser, FAU, Photonics-SOI). A note using these is almost certainly on-topic.
3. **Sub-segments / adjacent technologies that drive the topic** — narrower than the topic but still topic-defining (1.6T, ZR+, DCI for optical; HBM, NAND for storage). Include only if they're rarely used outside the topic.
4. **For investment topics: tickers and primary public companies in the topic** — the small set of stocks the topic *is about* (LITE, COHR, CIEN, GLW, AAOI, TSEM, AXTI, FN for optical). A note about LITE is a note about optical comms.
5. **Chinese-market peers and component vendors**, if the vault has Chinese-language coverage (中际旭创, 新易盛, Soitec/SLOIY).

**What to exclude — these inflate the union with off-topic notes:**

- **Research-shop / analyst / publisher names** (Bernstein, SemiAnalysis, Goldman Sachs, LightCounting, fpeking, lionhill). They surface notes that *cite* the source on any topic, not notes about your topic. The seed note often lists them in a "References" section — that's not a green light to query them.
- **Generic macro / financial terms** (hyperscaler capex, AI infrastructure, capex, valuation, P/E). These match thousands of unrelated notes.
- **Cross-cutting tech terms that span many topics** (AI, GPU, datacenter, NVIDIA, NVLink moat — unless the topic *is* NVIDIA). NVDA and AVGO are platform companies that show up in every AI-infra note; querying them pulls in everything.
- **Trading-tactic terms** (均线, EMA, breakout, support, resistance, PEG screen) — these match chart-commentary notes that happen to mention a topic ticker but aren't about the topic.
- **Generic verbs and structure words** from the seed (报告, 投资, 分析, 风险, report, analysis, investment).

When in doubt, run a candidate query with `--limit 5` and skim the top results: if 2+ of them clearly aren't about the topic, drop the keyword from the plan.

Build a query list from the kept terms, then run them as separate AND queries. Start with the broadest single-term queries first (priorities 1–2), then narrow with 2-term combinations only if a single-term query returns too much.

**Example query plan for "光通信" (optical communications):**

```bash
# Broad single-term sweeps (run separately, dedupe results)
notes-search search "光通信"
notes-search search "光互连"
notes-search search "optical communications"
notes-search search "silicon photonics"
notes-search search "硅光"
notes-search search "CPO"

# Narrowing with 2-term AND (only if single-term returns too much)
notes-search search "光通信 CPO"      # mixed lang, fine
notes-search search "硅光 InP"         # mixed lang, fine
notes-search search "CPO CW laser"    # English-only
notes-search search "光模块 1.6T"      # Chinese-only

# Ticker-scoped
notes-search search "LITE"
notes-search search "TSEM PH18"
```

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
- Use `--sort time` when the user asks about "recent", "latest", or time-sensitive topics
- Use `--sort relevance` (default) for depth and quality
- When the user says "top N notes", set `--limit N`
- For large-scale research, use `--limit 100` or higher to get a broad candidate pool

### Step 4: Union and Deduplicate

You will have results from multiple `notes-search` calls (Step 3) plus index sections (Steps 1–2). These are **unioned**, not intersected — a note appearing in *any* query's results is a candidate.

1. **Union all candidates** — concatenate filepaths from every query's results and from index sections into one list. Do NOT filter to notes that appeared in multiple queries; that defeats the purpose of running synonym/sub-term sweeps.
2. **Dedupe by filepath** — collapse exact-path duplicates. Track which queries each note matched (useful for relevance signal).
3. **Prioritize** — rank candidates by:
   - Number of queries the note matched (notes hit by multiple queries are often more central)
   - Best `bm25_score` across queries (lower is better in this CLI)
   - Recency — for time-sorted asks ("latest", "recent"), sort by `frontmatter_sort_time` or `file_mtime` across the unioned set, NOT within a single query's results
   - Note type (prefer `personal synthesis` and `research paper` for depth)
4. **Apply top-N cap AFTER union** — if the user asked for "latest 10" or "top N", apply the cap to the unioned/deduped/sorted list. Never apply `--limit N` to a single query and call that the answer.
5. **Select notes to read** — pick the top candidates (may be dozens or hundreds for large research)

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
