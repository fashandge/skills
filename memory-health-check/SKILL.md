---
name: memory-health-check
description: Check whether a macOS machine's memory (RAM) is healthy by running memory_pressure, vm_stat, and sysctl vm.swapusage plus a wired (kernel) memory and wired-zone leak check, then interpreting the results into a healthy / borderline / critical verdict. Use whenever the user asks "is my memory healthy", "am I low on RAM", "why is my Mac slow / beachballing", "check memory pressure", "how much memory am I using", "is my swap too high", "is the kernel leaking wired memory", or shares an Activity Monitor memory screenshot and wants it assessed. Reads the live system, not just the screenshot, so it gives a precise answer rather than eyeballing a graph.
allowed-tools: Bash(zsh:*), Bash(memory_pressure:*), Bash(vm_stat:*), Bash(sysctl:*), Bash(top:*), Bash(/usr/bin/memory_pressure:*), Bash(/usr/bin/vm_stat:*), Bash(/usr/sbin/sysctl:*), Bash(/usr/bin/top:*)
---

# memory-health-check

Assess whether a Mac is comfortable on RAM or running against its ceiling. Activity
Monitor's "Memory Pressure" graph and the headline numbers are a decent glance, but the
authoritative answer comes from the live kernel counters — so this skill reads them directly
and turns them into a plain verdict.

## How to run it

Run the bundled probe. It gathers all three userland counter sources, does the page-size math,
**also reads the wired (kernel) figure and the wired-zone leak trend**, prints a verdict block,
and then lists the top memory-consuming processes:

```bash
~/skills/memory-health-check/scripts/check_memory.sh
```

The wired check is part of the default run — don't treat it as optional. A machine can pass every
userland signal (free %, swap, compressor) while the kernel quietly eats its RAM, and only the
wired figure catches that, so always read out both what it says about *right now* and about the
*kernel wired-zone trend*. The two sudo-free wired signals it prints are the live wired share of
RAM (from `top`'s PhysMem line) and, when the sampler CSV exists, the recent growth trend of the
watched zone; per-zone live attribution still needs the sudo sampler below.

The script always exits 0 with its answer in stdout (a probe meaning "here are the numbers"
must not read as a failed step). It uses absolute tool paths so it works under stripped PATHs
(launchd/cron) too. If the user is on a non-macOS machine the tools won't exist and the script
will report mostly blanks — say so rather than inventing numbers.

The top-consumers list defaults to 12 processes; override with `TOPN`:

```bash
TOPN=20 ~/skills/memory-health-check/scripts/check_memory.sh
```

If you prefer to read the raw sources yourself (e.g. to show the user the underlying output):

```bash
memory_pressure | tail -1                        # headline "free percentage"
vm_stat                                          # page-level counters (16 KB pages on Apple Silicon)
/usr/sbin/sysctl vm.swapusage                    # swap total / used / free
top -l 1 -o mem -n 12 -stats pid,command,mem     # top processes by memory
```

Use `top` for per-process memory, **not** `ps -o rss` — the latter has been seen to report
near-zero RSS under sandboxed/stripped environments, giving a bogus ranking. `top -l 1` takes a
single non-interactive sample and works fine headless.

## What each metric means

Don't just read the numbers back — the whole value of this skill is translating them. The three
signals answer three different questions:

- **`memory_pressure` free percentage** — the headline. macOS computes this from free +
  reclaimable (inactive/purgeable/file-backed) pages. It's the closest analog to the colored
  pressure graph: **higher = more headroom**. This is the "are we in trouble *right now*"
  signal. Apple's own guidance is to watch memory pressure, not "Memory Used".
- **Compressor occupied (% of physical RAM)** — the structural-strain signal. macOS compresses
  inactive memory to avoid swapping to disk. A large compressor share (and a stored:occupied
  ratio well above 1:1) means real demand **routinely exceeds installed RAM** and the OS is
  paying a constant CPU tax to cope. This can be high even when pressure is green — it tells you
  whether you're *at your ceiling*, not whether you're failing.
- **Swap used** — the fallback. Light swap (a few hundred MB to ~1 GB) is normal and harmless.
  Swap climbing into multiple GB, or approaching the swap file's total, means the machine is
  paging to disk — that's where the user actually *feels* beachballs and app reloads.

`vm_stat` reports counts in **pages**; multiply by the page size in its header (16384 bytes on
Apple Silicon, 4096 on Intel) to get bytes. The script does this for you.

## When wired memory is the problem

The three userland signals cover userland demand. They do **not** explain a machine whose RAM is
eaten by the kernel — that's what the script's wired figure and leak-watch block are for. The
default run flags this for you: `check_memory.sh` escalates the verdict to Borderline at ≥30% of
RAM wired and Critical at ≥45% (normal is roughly 3–4 GB, ~10–17% on a 24 GB Mac; double digits GB
is pathological), and its "Kernel wired-zone leak watch" section reports whether the watched zone
is growing. When either shows elevated or growing wired memory, this section is the deep dive.

The raw one-liner behind the script's wired figure, if you want to show it:

```bash
top -l 1 -n 0 | grep PhysMem     # "23G used (19G wired, 1.9G compressor), 100M unused"
```

Wired memory is kernel-locked: it cannot be compressed, paged out, or reclaimed, and it is not
released when processes exit — only a reboot frees it. So a wired leak starves userland no matter
how few apps are open, and per-process rankings will look innocent. Rule out third-party drivers
first (`systemextensionsctl list`, `kmutil showloaded --collection-type auxiliary`); if both come
back empty, it is Apple's own kernel.

To attribute it to a specific zone, use the companion sampler — `zprint` reports every size as
`0K` to unprivileged callers, so this one genuinely needs `sudo`:

```bash
sudo ~/skills/memory-health-check/scripts/sample_wired_zones.sh --top       # rank wired allocations now
sudo ~/skills/memory-health-check/scripts/sample_wired_zones.sh -n 48 -i 900 # 12 h @ 15 min, logs MB/hour
```

It appends a CSV row per sample (zone size, total wired, swap, process counts) to
`~/.local/state/wired-zone-samples.csv` and prints the growth rate across the whole log, which is
what turns "my Mac is slow" into a filable bug report and lets you A/B which workload drives the
leak. `-z ZONE` watches a different label; the default is `data.kalloc.1024[vfs.namei]`.

`check_memory.sh` reads this same CSV (no sudo — it only reads, never runs `zprint`) for its
leak-watch block, but computes its trend over the **most recent ~6 h window**, not first-vs-last
across the whole log: a reboot clears wired memory, so a whole-log delta that spans one shows a
meaningless large negative. If the CSV is absent — the sampler daemon was never installed, or you
stopped it — the leak-watch block simply says the log is missing and points at the sudo sampler;
if the newest row is over an hour old, it notes the daemon may be stopped. Override the path it
reads with `WZLOG=/path/to.csv`.

Persistent sampling on this machine: root LaunchDaemon `local.wired-zone-sampler` (plist source
`launchd/local.wired-zone-sampler.plist` in this skill, installed at
`/Library/LaunchDaemons/`) takes one sample every 15 min plus one at boot, so the CSV keeps
growing across reboots without any sudo runs. Manage: `sudo launchctl bootout
system/local.wired-zone-sampler` to stop, `sudo launchctl bootstrap system
/Library/LaunchDaemons/local.wired-zone-sampler.plist` to start; stdout/stderr at
`/var/log/wired-zone-sampler.{out,err}.log`.

Observed on this machine (macOS 26.5.1, build 25F80, 2 days uptime): **16.2 GB** stuck in
`data.kalloc.1024[vfs.namei]` — the kernel's pathname-lookup buffers, ~1 KB leaked per path
resolution, so it scales with `open`/`stat`/`access` volume (node module resolution, file
watchers, repo scans). Kernel *zones* are normally well under 1 GB in total; when the sampler
shows one zone holding tens of percent of all wired memory, that is the leak, and rebooting is the
only way to reclaim it.

## Verdict rubric

The script applies these thresholds; apply the same judgment if reading raw:

| Signal | Healthy | Borderline | Critical |
|---|---|---|---|
| `memory_pressure` free | ≥ 30% | 15–30% | < 15% |
| Swap used | < 2 GB | 2–4 GB | ≥ 4 GB (or near swap total) |
| Compressor share of RAM | < 35% | 35–50% (watch) | — (see note) |
| Wired share of RAM | < 30% | 30–45% | ≥ 45% (likely kernel leak) |

The worst signal sets the verdict. Compressor share alone doesn't push to Critical — it's a
"you're at your ceiling" flag, not an acute failure — but combined with low free % or rising
swap it confirms the squeeze. A flat, low Activity Monitor pressure graph corroborates a
Healthy free %; a graph trending up or turning yellow/red corroborates Borderline/Critical.

## How to report back

Lead with the verdict, then explain it in terms the user can act on. Separate **"right now"**
(driven by free % and swap), **"structurally"** (driven by compressor load), and **"the kernel"**
(driven by the wired figure and leak-watch) — a machine can be fine this moment yet maxed out for
its workload, or fine on every userland signal yet quietly leaking wired memory, and conflating
these misleads. Always report the wired result, not just the userland verdict; a "healthy" that
silently skipped the wired check is the exact gap this skill closes. Be honest when it's only
borderline; don't round a squeezed machine up to "healthy". Close with what to watch for (pressure
turning yellow/red, swap past ~2–3 GB, wired trending up) and, when relevant, that the practical
fix is closing memory-heavy apps or adding RAM — or, for a wired leak, a reboot — rather than any
setting.

If the user shared an Activity Monitor screenshot, reconcile it with the live reading: the
screenshot's "Compressed" figure should roughly match the script's compressor-occupied GB, and
its pressure graph color should track the free %.

When the verdict is Borderline or Critical, use the top-consumers list to make the advice
concrete: name the actual heavy processes and group related ones (e.g. several Chrome helpers,
or a stack of AI/dev tools) so the total is visible, then point at the biggest realistic wins
rather than a generic "close some apps". A single large process is one lever; a swarm of
mid-size ones that sum to gigabytes is another. Don't suggest killing system processes like
`WindowServer` or `kernel_task`.
