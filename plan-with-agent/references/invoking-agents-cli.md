# Invoking a counterpart agent (agents-cli)

Shared mechanics for calling a second agent via `agents-cli`. Consumed by the
`plan-with-agent`, `review-with-agent`, and `skill-review-with-agent` skills —
edit here, not in the SKILL.mds, so they can't drift. Full flag list: `agents-cli -h`.

Every call is fresh-context and one-shot (no session resume): the prompt must
be fully self-contained — the brief, absolute paths, constraints, and
prior-round history every time.

Pass the prompt through a quoted stdin heredoc (avoids quoting, ARG_MAX, and
persistent prompt files); the answer arrives on stdout — capture it to a file,
then read the file. Run long calls in the background and read the output file
when the process exits; don't kill quiet runs.

**Long calls from a cmux-hosted Claude Code session: add `--detach`.** An
agent-process reaper in that environment can SIGKILL a background agents-cli
call ~6 minutes after the session goes idle (plain shells survive; agent
process trees don't). For calls expected to exceed ~6 minutes — any high/xhigh
review or draft — add `--detach <output-base>`: the CLI returns immediately
with a JSON line of file paths, the run continues in its own session, the
final answer lands in `<output-base>.out`, and `<output-base>.exitcode`
appears last (poll for it to detect completion; a plain background sleep-loop
task works as a completion timer since shells survive the reaper). Short calls
don't need `--detach`. When using it, the stdout-redirect in the templates
above is unnecessary — results are file-based.

## Generic one-shot counterpart calls

**Codex:**

```bash
agents-cli -a codex -m "$MODEL" --codex-reasoning "$EFFORT" \
  --codex-working-dir <repo-root> --timeout 3600 \
  > <round-output-file> <<'PROMPT_EOF'
<self-contained prompt>
PROMPT_EOF
```

**Claude:**

```bash
agents-cli -a claude -m "$MODEL" --claude-effort "$EFFORT" --no-mcp \
  --timeout 3600 > <round-output-file> <<'PROMPT_EOF'
<self-contained prompt>
PROMPT_EOF
```

Use these generic calls for plan review and whenever a code candidate cannot
be represented by a native review scope.

## Native code-review calls (`review-with-agent` only)

These flags dispatch the reviewer through its built-in code-review workflow.
The heredoc contains only the self-contained context packet; do not put the
slash command in the prompt yourself.

**Codex:**

```bash
agents-cli -a codex -m "$MODEL" --codex-reasoning "$EFFORT" \
  --codex-working-dir <repo-root> --codex-review \
  --timeout 3600 > <round-output-file> <<'PROMPT_EOF'
<self-contained context packet>
PROMPT_EOF
```

This calls headless `codex exec review -`, using the context packet as native
custom review instructions for the current working-tree changes. Use the
generic call for other local scopes. Do not add `--uncommitted`, `--base`, or
`--commit`: Codex currently rejects a preset target combined with custom
instructions. Do not put `/review` in the prompt either; `/review` is handled
by the interactive TUI, not by one-shot `codex exec`.

**Claude — current working diff:**

```bash
agents-cli -a claude -m "$MODEL" --claude-effort "$EFFORT" --no-mcp \
  --claude-review-command code-review --timeout 3600 \
  > <round-output-file> <<'PROMPT_EOF'
<self-contained context packet>
PROMPT_EOF
```

For a GitHub pull request, use `--claude-review-command review` and optionally
`--claude-review-target <PR-number-or-URL>`. These select Claude Code's
unnamespaced `/code-review` and `/review` commands. Never substitute
`/code-review:code-review`, `/codex:review`, or `/ultrareview` unless the user
explicitly asks for that separate plugin or remote-review workflow.

- Always pass `--timeout 3600`: the default is 1200s, which high/xhigh passes
  over a substantial artifact regularly exceed.
- Claude only: always pass `--no-mcp` (unattended `claude -p` runs can hang on
  plugin MCP teardown, and these calls need no MCP tools), and note there is no
  working-dir flag — run the command from the repo root so paths in the prompt
  resolve.
- Mutable-call retry safety: when the consuming workflow permits the reviewer
  to write any artifact, snapshot every writable artifact before the call. If
  the result is unusable, restore every artifact to its exact pre-call state
  (including nonexistence) before a retry or fallback. Never run another agent
  atop a partial mutation.
- Transient or malformed call: if a call times out, exits nonzero for a
  transient provider reason, or returns empty/unusable output, retry it once.
  For a generic call, a missing required output field from the consuming prompt
  (such as `VERDICT:` or `VALIDATION:`), or a verdict inconsistent with the
  consuming skill's severity rubric, is also malformed. A coherent native code
  review is usable without those exact fields; the consuming skill normalizes
  its severities and verdict. A call that produced no usable output doesn't
  count against the consuming skill's call cap.
- Persistent failure: do not repeat an invalid model, missing binary,
  authentication failure, or twice-malformed result with the same
  configuration. If the user did not name an exact model, select the next
  eligible model from the roster in [model-selection.md](model-selection.md);
  if they did, report the failure and ask before substituting.
