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
