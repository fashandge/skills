# Worker-side `emit` payloads

Workers report through `handoffctl emit` (the outbox journal). Data schemas are
enforced exactly — missing or unknown fields exit 2 with the field diff — and
are printed by `handoffctl emit --help` and embedded in every generated kickoff
contract. Treat those as the source of truth for field shapes; this file exists
for the worked examples.

## Publish a result

Write body and data to private files (never interpolate content into a shell
program), then:

```bash
<helper> emit --run-dir "$HANDOFF_RUN_DIR" --type result \
  --body-file /tmp/result-body.md --data-file /tmp/result-data.json
```

`result-data.json`:

```json
{
  "commitments": [],
  "dirty": false,
  "head": "fc47787e9e448a75aae0ba70738f1d99f774a0f1",
  "inbox_cursor": 0,
  "stage": "complete",
  "verification": [
    {
      "command": "pytest tests/ -q",
      "exit_code": 0,
      "summary": "42 passed"
    }
  ]
}
```

The body file carries the human-readable result: the answer or deliverable,
evidence, current `HEAD`, and dirty state. A successful emit moves the run to
`awaiting_review` and (for cmux-launched workers) sends the best-effort
`Handoff result ready` notification.

## Conclude after acceptance

After consuming the accepted `review` and the orchestrator `stop`, emit two
checkpoints — `succeeded` first, then `stopped`:

```bash
<helper> emit --run-dir "$HANDOFF_RUN_DIR" --type checkpoint \
  --body-file /tmp/ckpt-body.md --data-file /tmp/ckpt-succeeded.json
```

`ckpt-succeeded.json` — valid only from `awaiting_review` with a consumed
matching accepted review in the prefix; `inbox_cursor` covers at least the
review:

```json
{"state": "succeeded", "stage": "complete", "current_activity": "Result accepted; reporting succeeded", "inbox_cursor": 3, "commitments": []}
```

`ckpt-stopped.json` — requires `desired_state: stop` and the `stop` message
inside the consumed prefix:

```json
{"state": "stopped", "stage": "complete", "current_activity": "Consumed orchestrator stop; run concluded", "inbox_cursor": 4, "commitments": []}
```

## Validator notes

- `verification` items are exactly `{command, exit_code, summary}`; `exit_code`
  is an integer, or `null` when the check could not start.
- `commitments` is a list of distinct non-empty strings, each at most 2,048
  bytes.
- `inbox_cursor` cannot decrease, cannot exceed the inbox tail, and cannot
  advance across an unanswered blocking question.
- Terminal checkpoint preconditions live in the state machine: `succeeded`
  needs the accepted review, `stopped` needs the consumed orchestrator stop.
