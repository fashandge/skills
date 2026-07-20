# Feedback Assistant draft — kernel wired-memory leak in data.kalloc.1024[vfs.namei]

Suggested area: **Kernel** (or System Performance). Attach a sysdiagnose captured while wired memory is high.

---

**Title:**
Kernel wired-memory leak in zone data.kalloc.1024[vfs.namei] — ~305 MiB/hour, 16.2 GiB after 2 days, reclaimable only by reboot

**Description:**

## Summary

The kernel zone `data.kalloc.1024[vfs.namei]` (pathname-lookup buffers) grows
monotonically and is never released. On a 24 GB MacBook Pro it reached 16.2 GiB
— 82% of all wired memory — after only 54 hours of uptime, driving memory
pressure to critical (9% free) and making the system unusable until reboot.
The leak reproduces every boot cycle on this machine and scales with
path-resolution (open/stat/access) volume.

## Environment

- Hardware: MacBook Pro (Mac16,8), Apple M4 Pro, 24 GB RAM
- macOS: 26.5.1 (25F80)
- Kernel: Darwin 25.5.0, xnu-12377.121.6~2, RELEASE_ARM64_T6041
- Third-party kernel code: none — `kextstat` shows only com.apple.* extensions,
  `systemextensionsctl list` reports 0 system extensions

## Steps to reproduce

1. Boot the machine.
2. Run a normal development workload that performs a sustained volume of path
   resolutions — e.g. file watchers (uvicorn --reload / watchfiles), node module
   resolution, and repository-wide scans (ripgrep/glob from build tools).
3. Sample wired memory over time: `sudo zprint | sort -n` (or watch
   `top -l 1 -n 0` PhysMem wired figure).

## Expected results

Pathname-lookup allocations are transient; the zone should stay small
(well under 1 GiB) and total wired memory should remain roughly flat over days
of uptime.

## Actual results

The zone grows linearly at ~305 MiB/hour and is never reclaimed while the
system runs:

- After 54 h 23 m uptime: `data.kalloc.1024[vfs.namei]` = 16,588 MiB
  (16,986,179 KB), out of 19.77 GiB total wired — 81.9% of all wired memory.
- Rate implies roughly 1 KiB leaked per path resolution (~89 resolutions/sec
  sustained average during the window).
- `top -l 1 -n 0`: `PhysMem: 23G used (19G wired, 2397M compressor), 154M unused.`
- `memory_pressure`: 9% free (critical); swap 1.6 GB used and climbing.
- zprint ranking at sample time (all other zones normal):

```
 16588.1 MB  data.kalloc.1024[vfs.namei]
   511.8 MB  com.apple.iokit.IOGPUFamily
   413.9 MB  VM_KERN_MEMORY_PTE
   123.5 MB  com.apple.iokit.IOGPUFamily.API
   102.9 MB  com.apple.iokit.IOSurface
   (remaining zones < 100 MB each)
```

- Quitting all user applications does not release the memory; per-process RSS
  accounting is normal. Only a reboot reclaims it.
- Reproduced across multiple boot cycles on this machine (same zone, same
  magnitude after ~2 days uptime each time).

## Impact

On a 24 GB machine the leak consumes two-thirds of physical RAM within ~2.5
days, causing sustained memory pressure, swap thrashing, and severe system
slowdown. The only workaround is rebooting every few days.

## Notes

- Happy to attach a sysdiagnose taken while the zone is large, and a time
  series of per-zone samples (CSV) showing the growth rate.
