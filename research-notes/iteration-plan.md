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
