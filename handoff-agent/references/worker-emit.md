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

After consuming the accepted `review`, emit one `paused` checkpoint and idle
awaiting further instructions. There is no accompanying lifecycle message and
no exit checkpoint. A doorbell arrives with the next instruction; resume by
consuming a `steer`/`answer`/`supersede`/`input-changed`/`base-changed` newer
than the accepted review and checkpointing back to `working`:

```bash
<helper> emit --run-dir "$HANDOFF_RUN_DIR" --type checkpoint \
  --body-file /tmp/ckpt-body.md --data-file /tmp/ckpt-paused.json
```

`ckpt-paused.json` — valid from `awaiting_review` with a consumed matching
accepted review:

```json
{"state": "paused", "stage": "complete", "current_activity": "Result accepted; paused awaiting instructions", "inbox_cursor": 2, "commitments": []}
```

`conclude --stop` and `stop` write the orchestrator-owned registry
`finished_at` marker. They do not send worker lifecycle messages, and the
worker does not emit `succeeded`/`stopped` or exit; cleanup reaps the resident
session when requested.

## Validator notes

- `verification` items are exactly `{command, exit_code, summary}`; `exit_code`
  is an integer, or `null` when the check could not start.
- `commitments` is a list of distinct non-empty strings, each at most 2,048
  bytes.
- `inbox_cursor` cannot decrease, cannot exceed the inbox tail, and cannot
  advance across an unanswered blocking question.
- New runs can checkpoint only `working` or `paused`. Historical
  `succeeded`/`stopped` records remain readable for old frozen contracts but
  are rejected when a current run tries to emit them.
- `paused` needs the consumed matching accepted review. Resuming from
  `paused` to `working` needs a work message newer than that review.
