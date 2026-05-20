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

### Step 3: Search with CLI

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

### Step 4: Combine and Deduplicate

The index and search may return overlapping notes. Before reading:

1. **Collect all candidates** - gather note paths from both index sections and search results
2. **Dedupe by filepath** - remove duplicates (same note may appear in index and search)
3. **Prioritize** - rank candidates by:
   - Search score (if available)
   - Summary relevance to the query
   - Note type (prefer `personal synthesis` and `research paper` for depth)
   - Recency (if relevant to the question)
4. **Apply top-N cap** - if the user specified a number, limit to that many notes
5. **Select notes to read** - pick the top candidates for reading (may be dozens or hundreds for large research)

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

### Recent-focused: "What are my latest notes on AI agents?"

1. Run `notes-search search "AI agents" --sort time --limit 30 --json`
2. Read section indices for context
3. Combine, dedupe, read top notes (batching if needed)
4. Synthesize with emphasis on recent developments

## Output Format

When presenting research findings:
- Lead with the main insight or answer
- Support with specific evidence from notes (cite note titles)
- Note the breadth of coverage (e.g., "Based on 20 notes from your vault...")
- Highlight any gaps or areas with limited coverage
