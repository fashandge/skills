# Launch a Codex desktop-app task

Use this transport only when the orchestrator is itself in the Codex app, the
app task controls are available, and the user explicitly asks for a new or
background Codex task. Do not create a task merely because the user asks how
the mode works. The created task is user-owned and appears in the app.

1. Prepare the same durable, self-contained kickoff described in `../SKILL.md`.
2. Call `list_projects`, then select the exact saved project that owns the
   target repository on the intended host. Do not substitute a projectless
   task or a similarly named project.
3. Choose the task environment deliberately:
   - Use `local` when the worker must share the current checkout, including a
     newly written kickoff or authorized uncommitted state. Do not keep editing
     that checkout concurrently with the worker.
   - Use `worktree` for isolation only when the kickoff and required inputs are
     reachable from the worktree's base. Specify `startingState` only when the
     user explicitly requests a particular branch/ref or asks to include the
     current working tree. Never launch a worktree that cannot read its
     authoritative kickoff.
4. Call `create_thread` with that `projectId`, environment, and this initial
   prompt:

   ```text
   Implement per <kickoff-path> — read it fully first and treat it as authoritative.
   ```

   Omit model and reasoning overrides unless the user explicitly requests
   them. Retain the returned `threadId` and `hostId`; a queued worktree may
   initially return only `clientThreadId` and is not yet waitable.
5. After successful creation, report the created task using the app's
   `created-thread` directive. Do not use `fork_thread`: inherited conversation
   history defeats the clean, self-contained kickoff boundary. Do not use
   `handoff_thread`: it moves an existing task rather than creating a worker.

For launch-only mode, return as soon as creation succeeds. Do not read or wait
on the new task.

For a managed run, use `wait_threads` with one target, its latest cursor, and
bounded waits. Use `read_thread` only when the compact status lacks needed
detail, and use `send_message_to_thread` for steering or answers already
authorized by the user's instructions. Surface any request for new authority,
credentials, approval, or a material user choice instead of deciding it for
the worker. Do not narrate unchanged snapshots. Verify artifacts, diffs, and
tests directly before accepting the result.

This app-native transport does not create a local-v1 run directory, lease, or
journal. Codex task status/history is authoritative for orchestration, while
the kickoff remains authoritative for implementation scope.

If the app task controls are unavailable, fall back to manual creation and give
the user this one-line prompt:

```text
Implement per docs/plans/<kickoff>.md — read it fully first.
```

State clearly that the manual fallback provides no automated monitoring or
steering.
