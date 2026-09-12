# Remote workers in the same Herdr window

Herdr 0.9.0 saved machines show Local and SSH machines in one window. Each
profile connects to **one remote session**, with its own workspaces, panes,
processes, and IDs. This is a viewing/connection feature; spawn_worker still
launches through SSH on the remote host. Do not open a second client or nest
`herdr --remote` in a local worker tab for ordinary same-window spawning.

## Prepare once per host before a batch

1. **Wake OCI before SSH.** For `oci-box`, read the oci-box skill and run
   `box up` on the Mac. It starts a stopped instance and waits for SSH;
   it is also safe when already running. Do not substitute `box start`
   (which does not wait for SSH), open an interactive `box` shell, or
   precede it with `box status`. Let startup complete before any remote
   inspection or spawn; background the command if a cold start is slow.
   The spawn launcher and Herdr reconnects cannot power on an OCI instance.
   When already running on OCI itself, no Mac-side wake step is needed.
2. **Connect the right session to the existing local window.** Inside local
   Herdr, read the herdr skill and run `herdr machine list --json`. Match
   `target` and `session`, not just the display label. Reuse an enabled
   profile; enable a disabled match with `herdr machine enable <profile-id>`.
   If there is no match for the default session, run:

   ```bash
   herdr machine add oci-box --label oci-box
   ```

   Substitute the SSH alias for other hosts. Adding prepares the remote
   installation and starts its server; the profile appears in open local
   clients without changing the user's selection. Do not add it on every
   spawn: `machine add` can create duplicate profiles. Outside local Herdr,
   keep the existing SSH-only spawn behavior; do not control a focused local
   Herdr window from another terminal backend.
3. **Check remote readiness, separately from power and profile state.** Run
   `ssh oci-box herdr status server` and require a running, compatible server,
   then check that the remote checkout, agents package, and chosen agent are
   available. A saved/enabled profile alone does not establish connectivity.
   Allow a reconnect after boot, then recheck before spawning. If it still
   fails, diagnose the reported SSH/server error rather than repeatedly
   spawning. Herdr's **Attention** state requires the setup action it reports;
   background reconnects cannot resolve authentication or upgrade approval.
   Installation or replacement may need an interactive terminal, and replacing
   a server stops its panes. Do not automatically approve that replacement,
   stop the server, or create duplicate profiles as a reconnect workaround.

The current `spawn_worker.sh --remote-host` has **no remote-session selector**;
its SSH receiver uses the remote default Herdr environment. Pair it with a
`default` profile and verify that SSH resolves that server. A named-session
profile alone will not show workers launched into default. If the user
explicitly wants a named session, resolve launcher support first instead of
inventing `--remote-session` for spawn_worker or silently using default.
`--remote-workspace` selects a workspace label **inside** that session.

## Spawn and address the result

Keep the normal `--remote-host`, absolute `--remote-cwd`, and
`--remote-workspace <project-label>` launch path; use `--help` for syntax.
The remote checkout is independent of the Mac's checkout. Same-window access
does not copy code, skills, tools, credentials, or task artifacts between them.
Remote splits beside a local pane are unsupported by the launcher.

Keep `(host, session, handle)` together in session context for any wave gate,
attended wait, read, or follow-up. Use `ssh <host> herdr agent ...` for current
default-session workers. UI machine selection never changes an existing
pane's CLI socket; a local `herdr agent list` does not list remote workers.
If recovering context, list agents separately on each known host/session.
Distinguish a connection failure from a confirmed missing agent before
launching a replacement into the same checkout. Report the machine, session,
workspace, and returned pane handle so the user can locate the worker.

Verified against the installed launcher and Herdr 0.9.0. Herdr's maintained
[Connecting machines documentation](https://herdr.dev/docs/connecting-machines/)
owns connection behavior; installed `herdr machine` and
`spawn_worker.sh --help` own current command syntax.
