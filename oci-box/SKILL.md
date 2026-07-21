---
name: oci-box
description: Use the always-available OCI Ampere (ARM64 Linux) box for remote compute — running heavy builds/tests/batches off the Mac, long-running jobs, or anything needing a Linux/ARM64 environment. Use whenever the user says "run it on the box", "offload to OCI", "use the remote box", "box status/ssh", asks about the pipeline box, or wants to run something on a beefy free ARM machine without tying up the Mac. Wraps the `box` command (on PATH via ~/mycmd), which starts the box if stopped, waits for SSH, and runs the command with the ml conda env and secrets loaded.
allowed-tools: Bash
---

# oci-box

The OCI box is a free Ampere A1.Flex instance (ARM64 Linux, 16 ocpu / 96 GB)
shared across all projects. The `box` command on the Mac (on PATH via
`~/mycmd`) is the single entry point — it wraps
`~/projects/investment/src/scripts/oci_box_ctl.sh`.

## Canonical usage

```bash
box status                 # lifecycle + shape; never wakes the box
box 'pytest -q'            # start if stopped, wait for SSH, run remotely
box                        # ...or open an interactive shell instead
BOX_RUN_DIR=~/projects/foo box 'make build'   # run in another project
```

Remote commands run in the **ml conda env** with `~/.config/secrets.env`
loaded, cwd defaulting to `~/projects/investment` — always set `BOX_RUN_DIR`
for any other project. Full subcommand list: `box help`.

## Gotchas (the things `box help` can't tell you)

- **Bare `box` / `box <cmd>` / `box up` wake the box** from stopped (~1-2 min
  cold start; `status`/`stop`/`resize` don't). That's normal — don't
  `box status` first to "check", just run the command.
- **Never `shutdown`/`poweroff` on the box itself** — an OS-level halt leaves
  the instance billing. The box self-stops via an idle watchdog; to stop
  manually use `box stop` (SOFTSTOP via the OCI API).
- **It's ARM64** — x86-only binaries, docker images, and wheels won't work
  without rebuilding. There is an ml conda env on the box (created by the
  bootstrap script); it is not synced with the Mac's — install what you need.
- **Never `box resize`** — the box already runs at its intended shape
  (16 ocpu / 96 GB), and resizing reboots a running instance.
- **Secrets/auth live on both sides**: the Mac needs
  `~/.config/secrets.env` (OCI_INSTANCE_OCID, OCI_IP, OCI_PRIVATE_KEY_FILE)
  plus OCI CLI config for start/stop/status/resize. If `box` fails with a
  missing-var error, that's the file to check.
- The investment repo's nightly pipeline runs on the box around 00:05
  Tue–Sat (see `docs/data-pipeline.md` → "Automation" there for the exact
  schedule); a concurrent manual run is fine but expect load.

## Setup / rebuild

If the box is ever lost or reprovisioned, `bootstrap_oci_box.sh` in the
investment repo (`src/scripts/`) recreates the environment. Project-specific
plumbing (nightly pipeline, watchdog, DB pull) lives there too — this skill
covers only the generic cross-project usage.
