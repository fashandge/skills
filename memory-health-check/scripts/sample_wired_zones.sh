#!/bin/zsh
# Track kernel wired-memory growth over time — specifically leaks in a named
# allocation zone.
#
# Motivation: `check_memory.sh` can tell you the machine is out of RAM, but when
# the culprit is *wired* memory it cannot say why, because per-zone sizes are
# only visible to root. This sampler closes that gap: it appends one CSV row per
# sample and reports the growth rate, so you can measure MB/hour and A/B which
# workload drives it.
#
# Default watch target is data.kalloc.1024[vfs.namei] — the kernel's pathname
# lookup buffers. A leak there grows ~1 KB per path resolution that never gets
# returned, so it scales with open/stat/access volume (node module resolution,
# file watchers, repo scans) and is only released by a reboot.
#
# Requires root: `zprint` reports all sizes as 0K to unprivileged callers.
#
# Usage:
#   sudo ~/skills/memory-health-check/scripts/sample_wired_zones.sh              # one sample
#   sudo ~/skills/memory-health-check/scripts/sample_wired_zones.sh -n 48 -i 900 # 12h @ 15min
#   sudo ~/skills/memory-health-check/scripts/sample_wired_zones.sh --top        # rank all zones
#
# Options:
#   -n COUNT     number of samples (default 1; 0 = run until interrupted)
#   -i SECONDS   interval between samples (default 300)
#   -z ZONE      zone label to watch (default data.kalloc.1024[vfs.namei])
#   -l PATH      CSV log path (default ~/.local/state/wired-zone-samples.csv)
#   --top        also print the 15 largest wired entries for this sample
#
# Always exits 0 with its answer in stdout — a probe that means "here are the
# numbers" must not read as a failed step.

set -u

ZPRINT=/usr/bin/zprint
SYSCTL=/usr/sbin/sysctl
[[ -x $ZPRINT ]] || ZPRINT=$(command -v zprint 2>/dev/null || echo zprint)
[[ -x $SYSCTL ]] || SYSCTL=$(command -v sysctl 2>/dev/null || echo sysctl)

COUNT=1
INTERVAL=300
ZONE='data.kalloc.1024[vfs.namei]'
SHOW_TOP=0

# The log belongs to the human, not to root — resolve their home even when the
# script is invoked via sudo, and hand ownership back at the end.
REAL_USER=${SUDO_USER:-$USER}
REAL_HOME=$(/usr/bin/dscl . -read "/Users/$REAL_USER" NFSHomeDirectory 2>/dev/null | awk '{print $2}')
[[ -d ${REAL_HOME:-} ]] || REAL_HOME=$HOME
LOG="$REAL_HOME/.local/state/wired-zone-samples.csv"

while (( $# > 0 )); do
  case "$1" in
    -n) COUNT=${2:-1}; shift 2 ;;
    -i) INTERVAL=${2:-300}; shift 2 ;;
    -z) ZONE=${2:-$ZONE}; shift 2 ;;
    -l) LOG=${2:-$LOG}; shift 2 ;;
    --top) SHOW_TOP=1; shift ;;
    -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
    *) print -r -- "unknown option: $1 (try --help)"; exit 0 ;;
  esac
done

if [[ $(/usr/bin/id -u) -ne 0 ]]; then
  print -r -- "This sampler needs root — zprint reports every size as 0K otherwise."
  print -r -- "Re-run as:  sudo $0 $*"
  exit 0
fi

/bin/mkdir -p "${LOG:h}" 2>/dev/null

# --- one sample --------------------------------------------------------------
# zprint's trailing "wired memory" table lists non-zone and per-zone wired
# allocations, one per line, size last and suffixed K. Both the watched zone and
# the VM_KERN_COUNT_WIRED grand total come from there.
sample() {
  local out zone_k wired_k epoch stamp nproc nnode nclaude swap_mb
  out=$("$ZPRINT" 2>/dev/null)

  zone_k=$(print -r -- "$out" | /usr/bin/grep -F "$ZONE" | awk '{v=$NF; sub(/K$/,"",v); print v+0; exit}')
  wired_k=$(print -r -- "$out" | awk '/^VM_KERN_COUNT_WIRED[ \t]/{v=$NF; sub(/K$/,"",v); print v+0; exit}')
  [[ -n ${zone_k:-} ]]  || zone_k=0
  [[ -n ${wired_k:-} ]] || wired_k=0

  epoch=$(/bin/date +%s)
  stamp=$(/bin/date '+%Y-%m-%d %H:%M:%S')

  # Workload context, so a row explains itself when you compare two periods.
  nproc=$(/bin/ps ax | /usr/bin/wc -l | /usr/bin/tr -d ' ')
  nnode=$(/bin/ps ax -o comm= | /usr/bin/grep -c 'node$')
  nclaude=$(/bin/ps ax -o comm= | /usr/bin/grep -ci claude)
  swap_mb=$("$SYSCTL" -n vm.swapusage 2>/dev/null | sed -n 's/.*used = *\([0-9.]*\)M.*/\1/p')
  [[ -n ${swap_mb:-} ]] || swap_mb=0

  [[ -s $LOG ]] || print -r -- "epoch,timestamp,zone,zone_kb,wired_total_kb,swap_used_mb,procs,node_procs,claude_procs" >> "$LOG"
  print -r -- "$epoch,$stamp,\"$ZONE\",$zone_k,$wired_k,$swap_mb,$nproc,$nnode,$nclaude" >> "$LOG"

  awk -v z="$zone_k" -v w="$wired_k" -v s="$stamp" -v zone="$ZONE" 'BEGIN{
    printf "%s  %-32s %8.2f GB   wired total %6.2f GB   (%4.1f%% of wired)\n",
           s, zone, z/1048576, w/1048576, (w>0 ? z/w*100 : 0);
  }'

  if (( SHOW_TOP )); then
    print -r -- "  --- 15 largest wired entries ---"
    # Rank actual allocations only: drop the header rules, the VM_KERN_COUNT_*
    # and "zones"/"total" rollups (which double-count everything below them),
    # and any line whose trailing field is the fragmentation counter that wraps
    # to a nonsense 2^64-ish value.
    print -r -- "$out" | awk '
      /^wired memory/{w=1; next}
      w && /^-/{next}
      w && /^(VM_KERN_COUNT_|zones|total)/{next}
      w && NF>1 {
        v=$NF; if (v !~ /K$/) next; sub(/K$/,"",v); v+=0;
        if (v > 1048576*64) next;
        printf "%10.1f MB  %s\n", v/1024, $1;
      }' | sort -rn | head -15 | sed 's/^/  /'
  fi
}

# --- growth rate over the whole log ------------------------------------------
report_rate() {
  [[ -s $LOG ]] || return 0
  awk -F, 'NR>1 && $1+0>0 {
      if (!first) { first=$1; firstz=$4 }
      last=$1; lastz=$4; n++
    }
    END{
      if (n < 2) { print "  (one sample so far — run again later for a rate)"; exit }
      dt = last-first; dz = lastz-firstz;
      if (dt <= 0) exit;
      printf "  growth: %+.2f GB over %.1f h  =  %+.1f MB/hour  (%d samples)\n",
             dz/1048576, dt/3600, dz/1024/(dt/3600), n;
      if (dz > 0) printf "  at this rate it adds %.1f GB/day\n", dz/1048576/(dt/86400);
    }' "$LOG"
}

# --- run ---------------------------------------------------------------------
print -r -- "watching: $ZONE"
print -r -- "log:      $LOG"
print -r -- ""

i=0
while :; do
  sample
  (( i++ ))
  (( COUNT > 0 && i >= COUNT )) && break
  sleep "$INTERVAL"
done

print -r -- ""
report_rate

# Leave the log usable without sudo.
[[ -e $LOG ]] && /usr/sbin/chown "$REAL_USER" "$LOG" 2>/dev/null
exit 0
