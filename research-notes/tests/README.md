# research-notes test cases

Lightweight regression cases for the `research-notes` skill. Each `*.md` file records one real run so future iterations can be compared against past behavior.

## File format

Each case is a single Markdown file with these sections:

- **Prompt** — exact `/research-notes` argument string from the user
- **Model** — model that produced the run (e.g. `claude-opus-4-7[1m]`)
- **Date** — YYYY-MM-DD the run was captured
- **Queries fired** — every `notes-search` invocation actually run, in order
- **Final answer** — the ranked list / synthesis returned to the user
- **What good looks like** — short prose describing the qualities a good answer should have for this prompt (coverage, ranking, language mix, etc.). Use this when grading future runs.

## How to run all test cases

Use the Agent tool to run all test cases in parallel, then collect and evaluate results.

### Step 1: Discover test cases

```bash
ls ~/skills/research-notes/tests/*.md | grep -v README
```

### Step 2: Read all test case files

Read every test case file to extract the **Prompt**, **Final answer**, and **What good looks like** sections.

### Step 3: Launch one subagent per test case (in parallel)

For each test case, spawn an Agent with `subagent_type: "general-purpose"` that:

1. Receives the test prompt verbatim (the text inside the `Prompt` code block).
2. Executes the `/research-notes` skill with that prompt as the argument.
3. Returns the full skill output (the ranked title list or synthesis) back to you.

**Important:** The subagent prompt must be self-contained. Include:
- The exact test prompt to pass to `/research-notes`
- An instruction to invoke the `research-notes` skill with that prompt
- An instruction to return **both** the complete output (all titles and any synthesis) **and** every `notes-search` command that was executed during the run (with arguments), so the evaluator can compare query strategies

Example subagent prompt:

```
Run the research-notes skill with this exact prompt and return two things:

1. Every `notes-search` CLI command you executed (with full arguments), in the order they were run
2. The complete skill output (ranked title list or synthesis) verbatim

Prompt:
find the top 10 notes about agent harness, just list the titles, without doing any synthesis yet
```

Launch all subagents in a single message so they run concurrently.

### Step 4: Evaluate each result

After all subagents return, evaluate each result against its test case:

1. **Read the test case file** to get the expected `Queries fired`, `Final answer`, and `What good looks like` criteria.
2. **Compare queries fired** against the expected `Queries fired` section:
   - List queries that were expected but missing (these explain recall gaps).
   - List unexpected queries that were added (note whether they helped or added noise).
   - Note any differences in `--limit`, `--sort`, `--engine`, or `--mode` flags.
   - If the actual title list is missing expected notes, check whether the missing notes would have been found by the missing queries — this is the primary diagnostic for quality regressions.
3. **Grade each criterion** from `What good looks like` as PASS or FAIL with a one-line reason.
4. **Compare the title list** against the expected `Final answer`:
   - How many of the expected titles appear in the actual output?
   - Are there unexpected titles that shouldn't be there (noise)?
   - Is the ranking order reasonable?
5. **Assign an overall verdict**: PASS, PARTIAL PASS, or FAIL.

Do NOT require exact string equality — the vault changes over time, and minor ranking shifts are expected. Judge against the `What good looks like` criteria, which describe the *qualities* of a good answer.

### Step 5: Report

Present results in a summary table:

```
| Test Case | Verdict | Expected Titles Found | Criteria Passed | Query Coverage | Notes |
|-----------|---------|----------------------|-----------------|----------------|-------|
| ...       | ...     | 8/10                 | 5/6             | 6/8 queries    | ...   |
```

Then list per-test detail in three sections:

1. **Query diff** — expected vs actual queries, with missing/added queries called out. For any missing expected titles, note which missing query would have found them.
2. **Criteria grades** — each `What good looks like` criterion with PASS/FAIL and a one-line reason.
3. **Title diff** — expected titles found/missing, unexpected titles added, ranking assessment.

## How to update a test case

When iterating on `SKILL.md`:

1. Re-run the test cases using the procedure above.
2. Judge against `What good looks like`, not strict string equality.
3. If the new behavior is strictly better, update the recorded case (new `Final answer`, model, and date).
