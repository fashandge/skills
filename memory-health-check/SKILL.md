---
name: memory-health-check
description: Check whether a macOS machine's memory (RAM) is healthy by running memory_pressure, vm_stat, and sysctl vm.swapusage, then interpreting the results into a healthy / borderline / critical verdict. Use whenever the user asks "is my memory healthy", "am I low on RAM", "why is my Mac slow / beachballing", "check memory pressure", "how much memory am I using", "is my swap too high", or shares an Activity Monitor memory screenshot and wants it assessed. Reads the live system, not just the screenshot, so it gives a precise answer rather than eyeballing a graph.
allowed-tools: Bash(zsh:*), Bash(memory_pressure:*), Bash(vm_stat:*), Bash(sysctl:*), Bash(/usr/bin/memory_pressure:*), Bash(/usr/bin/vm_stat:*), Bash(/usr/sbin/sysctl:*)
---

# memory-health-check

Assess whether a Mac is comfortable on RAM or running against its ceiling. Activity
Monitor's "Memory Pressure" graph and the headline numbers are a decent glance, but the
authoritative answer comes from the live kernel counters — so this skill reads them directly
and turns them into a plain verdict.

## How to run it

Run the bundled probe. It gathers all three sources, does the page-size math, and prints a
verdict block:

```bash
~/skills/memory-health-check/scripts/check_memory.sh
```

The script always exits 0 with its answer in stdout (a probe meaning "here are the numbers"
must not read as a failed step). It uses absolute tool paths so it works under stripped PATHs
(launchd/cron) too. If the user is on a non-macOS machine the tools won't exist and the script
will report mostly blanks — say so rather than inventing numbers.

If you prefer to read the raw sources yourself (e.g. to show the user the underlying output):

```bash
memory_pressure | tail -1            # headline "free percentage"
vm_stat                              # page-level counters (16 KB pages on Apple Silicon)
/usr/sbin/sysctl vm.swapusage        # swap total / used / free
```

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

## Verdict rubric

The script applies these thresholds; apply the same judgment if reading raw:

| Signal | Healthy | Borderline | Critical |
|---|---|---|---|
| `memory_pressure` free | ≥ 30% | 15–30% | < 15% |
| Swap used | < 2 GB | 2–4 GB | ≥ 4 GB (or near swap total) |
| Compressor share of RAM | < 35% | 35–50% (watch) | — (see note) |

The worst signal sets the verdict. Compressor share alone doesn't push to Critical — it's a
"you're at your ceiling" flag, not an acute failure — but combined with low free % or rising
swap it confirms the squeeze. A flat, low Activity Monitor pressure graph corroborates a
Healthy free %; a graph trending up or turning yellow/red corroborates Borderline/Critical.

## How to report back

Lead with the verdict, then explain it in terms the user can act on. Separate **"right now"**
(driven by free % and swap) from **"structurally"** (driven by compressor load) — a machine can
be fine this moment yet clearly maxed out for its workload, and conflating the two misleads. Be
honest when it's only borderline; don't round a squeezed machine up to "healthy". Close with
what to watch for (pressure turning yellow/red, swap past ~2–3 GB) and, when relevant, that the
practical fix is closing memory-heavy apps or adding RAM rather than any setting.

If the user shared an Activity Monitor screenshot, reconcile it with the live reading: the
screenshot's "Compressed" figure should roughly match the script's compressor-occupied GB, and
its pressure graph color should track the free %.
