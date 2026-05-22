# research-notes SKILL.md Iteration Plan

## Round 1

### Current plan

**Overview:** Run all 3 test cases against the current SKILL.md to establish a baseline, identify gaps, then iterate.

**Details:**
1. Spawn 3 agents in parallel, one per test case, each invoking `/research-notes` with the test prompt
2. Collect results (queries fired + final title lists)
3. Evaluate against benchmarks
4. Identify SKILL.md improvements needed
5. Make changes and re-test

### Progresses
- Starting baseline evaluation with 3 parallel agents
- Round 1 was a prior session attempt; continuing as Round 2

## Round 2

### Current plan

**Overview:** Establish fresh baseline by running all 3 test cases against current SKILL.md, then identify specific gaps in query strategy guidance and iterate.

**Details:**
1. Run all 3 test cases in parallel via subagents
2. Evaluate each against benchmark (queries fired, title list, "what good looks like" criteria)
3. Identify patterns of failure (missing queries, wrong sort, noise in results, missing bilingual coverage)
4. Update SKILL.md with targeted improvements
5. Re-test and iterate

### Progresses
- Launched 3 test case agents in parallel, waiting for results
- All 3 agents completed. Results:

#### Baseline evaluation results

| Test Case | Verdict | Expected Titles Found | Key Issues |
|-----------|---------|----------------------|------------|
| agent harness | PARTIAL PASS | 9/10 | Minor: "Approaches to AI Agent Self-Improvement" is noise; missing 腾讯汤道生 |
| 内存周期 | FAIL | 3/10 | "Watchlist Competitive Landscape" at #1; missing NAND/HBM/存储涨价 queries; generic notes dominate |
| 光通信产业趋势 | FAIL | 4/10 | "Watchlist" at #3, "Glossary" at #2; missing CPO/silicon photonics standalone queries |

#### Root cause analysis

1. **Ranking by query-count as primary signal over-ranks generic notes.** "Watchlist Competitive Landscape" matches 5-7 queries across all topics because it's a broad meta-note. Current SKILL.md puts "Number of queries matched" first in ranking criteria.
2. **Insufficient standalone sub-concept queries.** SKILL.md says "at least 3-5 queries" but benchmarks need 8+. Core sub-concepts (NAND, HBM, CPO) each need their own standalone query.
3. **No noise filtering for generic/meta notes.** Watchlists, PEG screens, glossaries should be deprioritized.
4. **Keyword-from-seed reference not applied to bare topic queries.** The reference file's principles (broad single-term sweeps, ticker queries) should apply universally.

#### Planned SKILL.md changes

1. Increase minimum query count from 3-5 to 5-8 (10-15 for broad topics)
2. Add explicit guidance: each core sub-concept gets a standalone query
3. Fix ranking: title-relevance to topic > query-count; add noise filtering
4. Broaden keyword-from-seed reference to apply to all queries, not just seed-based

### Round 2 evaluation results

| Test Case | Verdict | Expected Found | Baseline | Improvement | Notes |
|-----------|---------|---------------|----------|-------------|-------|
| agent harness | PARTIAL PASS | 8/10 | 9/10 (bg) | No noise (was: tangential note) | Missing: 腾讯汤道生, OpenAI-Cursor-Anthropic |
| 内存周期 | PARTIAL PASS | 7/10 | 3/10 | +4 titles, no Watchlist noise | Missing: PE PB估值, SanDisk NAND, MU SNDK扩产 |
| 光通信产业趋势 | PASS | 9/10 | 4/10 | +5 titles, no noise | Missing only: CMOS Process |

**Key improvements:**
- Noise filtering works: Watchlist, PEG Screen, Glossary all eliminated from top 10
- Standalone sub-concept queries work: CPO元年, HBM/NAND notes now appearing
- Bilingual coverage improved across all 3 tests

**Remaining gaps:**
1. 内存周期 still missing 3 expected notes — likely ranking issue, not query coverage
2. agent harness missing 2 expected notes — ranking pushes Meta-Harness and I Improved 15 LLMs above them
3. 光通信 missing CMOS Process — may be a ranking issue

### Suggested next steps

1. Investigate whether the 3 missing 内存周期 notes are in the candidate pool (query issue) or ranked too low (ranking issue)
2. Consider adding guidance about preferring notes that discuss the topic thesis/dynamics over notes about individual companies
3. Consider whether "title relevance" ranking guidance is too aggressive — it may push notes with topic keywords in title above notes that are more thesis-central but have less keyword-dense titles

## Round 3

### Current plan

**Overview:** Add thesis-specificity ranking and better per-query limits.

**Details:**
1. Clarify per-query --limit should be 2-3x requested top-N
2. Add thesis dynamics ranking (cycle, pricing, expansion keywords)
3. Re-test all 3

### Evaluation results

| Test Case | R2 | R3 | Trend |
|-----------|----|----|-------|
| agent harness | 8/10 | 8/10 | same |
| 内存周期 | 7/10 | 6/10 | WORSE |
| 光通信 | 9/10 | 8/10 | WORSE |

**Root cause:** Thesis-specificity ranking was too prescriptive and cycle-focused. Hurt 光通信 (industry trends ≠ cycle dynamics) and didn't help 内存周期. "Demote generic reference notes" was too aggressive — demoted valuable analyst reports (Bernstein深度研报) and pushed tangential personal opinion notes up.

### Suggested next steps (implemented as Round 4)

1. Roll back thesis-specificity ranking, revert to simpler title-relevance guidance
2. Add "review the boundary" step — scan positions N+1 to N+5 and swap in notes with strong title relevance or BM25 that were pushed down by low query-count
3. Keep noise filtering (watchlists, PEG screens) and sub-concept queries — those work well

## Round 4

### Current plan

**Overview:** Roll back thesis-specificity ranking regression, add boundary review for notes near the cutoff.

### Evaluation results

| Test Case | R2 | R3 | R4 |
|-----------|----|----|-----|
| agent harness | 8/10 | 8/10 | 8/10 |
| 内存周期 | 7/10 | 6/10 | 7/10 |
| 光通信 | 9/10 | 8/10 | 8/10 |

**Diagnostic findings:**
- 腾讯汤道生 is position #10, OpenAI-Cursor-Anthropic #11 in "harness" query — right at the boundary
- CMOS Process is #1 in "silicon photonics" query (BM25=-32.6) but not making top 10 because it only matches 1 query
- SanDisk NAND周期 is #4 in "NAND" query but not making top 10
- Root cause: query-count still dominates ranking despite guidance saying otherwise. Notes matching 3+ queries consistently outrank single-query matches even when the single-query match has a much better BM25 score.

**Key insight:** The issue isn't boundary review (which agents aren't consistently doing) — it's sub-concept coverage. If a sub-concept query (e.g., "silicon photonics") returns strong results but none make the top N, the topic isn't fully covered.

### Suggested next steps (implemented as Round 5)

1. Replace boundary review with "verify sub-concept coverage" step
2. Make it explicit: each sub-concept query should have at least one representative in the final top N
3. Re-test all 3
