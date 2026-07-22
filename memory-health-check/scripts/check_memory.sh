#!/bin/zsh
# macOS memory health probe.
# Gathers raw figures from memory_pressure, vm_stat, and sysctl vm.swapusage,
# derives the human-meaningful metrics (compressor load, compression ratio,
# swap usage), and prints a single block the caller can interpret.
#
# Designed to ALWAYS exit 0 with its answer in stdout, even if one source is
# missing — a probe that means "here are the numbers" must not read as a failed
# step. Uses absolute paths because launchd/cron and stripped PATHs may not have
# the tools on PATH.

set -u

MP=/usr/bin/memory_pressure
VMSTAT=/usr/bin/vm_stat
SYSCTL=/usr/sbin/sysctl
TOP=/usr/bin/top

[[ -x $MP ]]     || MP=$(command -v memory_pressure 2>/dev/null || echo memory_pressure)
[[ -x $VMSTAT ]] || VMSTAT=$(command -v vm_stat 2>/dev/null || echo vm_stat)
[[ -x $SYSCTL ]] || SYSCTL=$(command -v sysctl 2>/dev/null || echo sysctl)
[[ -x $TOP ]]    || TOP=$(command -v top 2>/dev/null || echo top)

# How many top consumers to list (override: TOPN=20 check_memory.sh).
TOPN=${TOPN:-12}

mp_out=$("$MP" 2>/dev/null)
vm_out=$("$VMSTAT" 2>/dev/null)
swap_out=$("$SYSCTL" vm.swapusage 2>/dev/null)
memsize=$("$SYSCTL" -n hw.memsize 2>/dev/null)

# --- page size ---------------------------------------------------------------
# vm_stat reports its page size in the header, e.g. "(page size of 16384 bytes)".
pagesize=$(print -r -- "$vm_out" | sed -n 's/.*page size of \([0-9]*\) bytes.*/\1/p' | head -1)
[[ -z "$pagesize" ]] && pagesize=16384

# --- helper: pull a vm_stat counter (pages) ----------------------------------
vm_pages() {
  print -r -- "$vm_out" | sed -n "s/^$1: *\([0-9]*\)\..*/\1/p" | head -1
}

occupied_pages=$(vm_pages "Pages occupied by compressor")
stored_pages=$(vm_pages "Pages stored in compressor")
free_pages=$(vm_pages "Pages free")
active_pages=$(vm_pages "Pages active")
inactive_pages=$(vm_pages "Pages inactive")
wired_pages=$(vm_pages "Pages wired down")
spec_pages=$(vm_pages "Pages speculative")

# --- memory_pressure free percentage -----------------------------------------
free_pct=$(print -r -- "$mp_out" | sed -n 's/.*free percentage: *\([0-9]*\)%.*/\1/p' | head -1)

# --- swap (sysctl vm.swapusage) ----------------------------------------------
swap_total=$(print -r -- "$swap_out" | sed -n 's/.*total = *\([0-9.]*\)M.*/\1/p' | head -1)
swap_used=$(print -r -- "$swap_out"  | sed -n 's/.*used = *\([0-9.]*\)M.*/\1/p'  | head -1)

# --- derive ------------------------------------------------------------------
# awk does the float math; guard against empty inputs by defaulting to 0.
read -r phys_gb occ_gb stored_gb comp_ratio occ_pct <<EOF
$(awk -v ps="$pagesize" -v mem="${memsize:-0}" -v occ="${occupied_pages:-0}" \
       -v stored="${stored_pages:-0}" 'BEGIN{
  gb = 1073741824;
  phys = mem/gb;
  occg = occ*ps/gb;
  storedg = stored*ps/gb;
  ratio = (occ>0)? stored/occ : 0;
  occpct = (mem>0)? occg/phys*100 : 0;
  printf "%.2f %.2f %.2f %.2f %.0f", phys, occg, storedg, ratio, occpct;
}')
EOF

swap_used_gb=$(awk -v u="${swap_used:-0}" 'BEGIN{printf "%.2f", u/1024}')

# --- wired memory (kernel-locked; a leak here starves userland) ---------------
# From top's PhysMem line: "23G used (2768M wired, 6209M compressor), ...".
# Wired memory can't be compressed, paged out, or reclaimed, and it is not freed
# when processes exit — only a reboot releases it. So a large wired share of RAM
# is a kernel-leak signal the userland metrics (free %, swap, compressor) miss
# entirely, and per-process rankings look innocent while it happens.
phys_line=$("$TOP" -l 1 -n 0 2>/dev/null | /usr/bin/grep -i PhysMem)
wired_raw=$(print -r -- "$phys_line" | sed -n 's/.*(\([0-9.]*[MG]\) wired.*/\1/p' | head -1)
read -r wired_gb wired_pct <<EOF
$(awk -v raw="${wired_raw:-}" -v mem="${memsize:-0}" 'BEGIN{
  gb=1073741824; n=raw+0; u=raw; gsub(/[0-9.]/,"",u);
  b=(u=="G")? n*gb : (u=="M")? n*1048576 : 0;
  printf "%.2f %.0f", b/gb, (mem>0 && b>0)? b/mem*100 : 0;
}')
EOF

# --- verdict -----------------------------------------------------------------
# Thresholds reflect what the macOS memory subsystem treats as comfortable.
# free_pct is the memory_pressure tool's own headline (higher = more headroom).
# occ_pct (compressor share of physical RAM) is the structural-strain signal:
# heavy compression means real demand routinely exceeds installed RAM. Swap
# climbing toward its total, or multi-GB, is where the user feels slowdowns.
verdict="HEALTHY"
reasons=()

fp=${free_pct:-100}
if (( fp < 15 )); then
  verdict="CRITICAL"; reasons+=("memory_pressure free is only ${fp}% (<15% = severe pressure)")
elif (( fp < 30 )); then
  verdict="BORDERLINE"; reasons+=("memory_pressure free is ${fp}% (30%+ is comfortable)")
fi

if (( ${swap_used_gb%.*} >= 4 )); then
  verdict="CRITICAL"; reasons+=("swap used is ${swap_used_gb} GB (>=4 GB = thrashing risk)")
elif awk -v u="$swap_used_gb" 'BEGIN{exit !(u>=2)}'; then
  [[ $verdict == HEALTHY ]] && verdict="BORDERLINE"
  reasons+=("swap used is ${swap_used_gb} GB (light swap is <2 GB)")
fi

if (( ${occ_pct:-0} >= 50 )); then
  [[ $verdict == HEALTHY ]] && verdict="BORDERLINE"
  reasons+=("compressor holds ${occ_pct}% of physical RAM (heavy compression = at your ceiling)")
elif (( ${occ_pct:-0} >= 35 )); then
  reasons+=("compressor holds ${occ_pct}% of physical RAM (notable, watch it)")
fi

# Wired share of RAM. Normal is ~3-4 GB (roughly 10-17% on a 24 GB Mac); a large
# share means the kernel itself is holding the RAM and no app-closing will help.
wp=${wired_pct:-0}
if [[ -n "$wired_raw" ]]; then
  if (( wp >= 45 )); then
    verdict="CRITICAL"; reasons+=("wired (kernel) memory is ${wired_gb} GB = ${wp}% of RAM — likely a kernel leak; only a reboot frees it")
  elif (( wp >= 30 )); then
    [[ $verdict == HEALTHY ]] && verdict="BORDERLINE"
    reasons+=("wired (kernel) memory is ${wired_gb} GB = ${wp}% of RAM — elevated; run the sudo wired-zone sampler to attribute it")
  fi
fi

(( ${#reasons[@]} == 0 )) && reasons+=("free headroom, light swap, modest compression, normal wired")

# --- report ------------------------------------------------------------------
print -r -- "=== macOS memory health ==="
print -r -- "Physical RAM:          ${phys_gb} GB"
print -r -- "memory_pressure free:  ${free_pct:-?}%"
print -r -- "Compressor occupied:   ${occ_gb} GB  (${occ_pct}% of RAM)"
print -r -- "Compressor stored:     ${stored_gb} GB original  →  ${comp_ratio}:1 compression"
print -r -- "Swap used:             ${swap_used_gb} GB  (of ${swap_total:-?} MB total)"
if [[ -n "$wired_raw" ]]; then
  print -r -- "Wired (kernel) memory: ${wired_gb} GB  (${wired_pct}% of RAM)"
fi
print -r -- ""
print -r -- "VERDICT: ${verdict}"
for r in "${reasons[@]}"; do print -r -- "  - $r"; done

# --- kernel wired-zone leak watch (from the persistent sampler's CSV) ---------
# Per-zone wired sizes need sudo to read live (zprint reports 0K otherwise), but
# the sample_wired_zones.sh sampler / local.wired-zone-sampler daemon logs them
# to a CSV we can read without sudo — so a slow-building leak shows up in the
# default run. The log may be absent if the daemon was never installed or was
# stopped; that's fine, we just say so.
WZLOG="${WZLOG:-$HOME/.local/state/wired-zone-samples.csv}"
print -r -- ""
print -r -- "=== Kernel wired-zone leak watch ==="
if [[ -s "$WZLOG" ]]; then
  # Trend is computed over the most recent ~6h window, NOT first-vs-last across
  # the whole log: a reboot clears wired memory, so spanning one makes the naive
  # delta a meaningless large negative. The recent window also answers the real
  # question — "is it leaking right now?".
  awk -F, -v now="$(/bin/date +%s)" '
    NR>1 && $1+0>0 { e[n]=$1; z[n]=$4; w[n]=$5; zone=$3; n++ }
    END{
      if(n==0){print "  (log present but has no samples yet)"; exit}
      gsub(/"/,"",zone);
      li=n-1;                                   # rows are appended in epoch order
      printf "  watched zone: %s\n", zone;
      printf "  latest:       %.2f GB in zone  (%.1f%% of %.2f GB wired)\n",
             z[li]/1048576, (w[li]>0? z[li]/w[li]*100:0), w[li]/1048576;
      age=now-e[li];
      if(age > 3600)
        printf "  (last sample %.1f h ago — sampler daemon may be stopped)\n", age/3600;
      cut=e[li]-21600; fi=-1;                    # first row within last 6h
      for(i=0;i<n;i++){ if(e[i]>=cut){ fi=i; break } }
      if(fi<0 || fi==li){print "  (not enough recent samples for a trend)"; exit}
      dt=e[li]-e[fi]; dz=z[li]-z[fi]; cnt=li-fi+1;
      if(dt<=0){print "  (timestamps not increasing — cannot compute a rate)"; exit}
      perday=dz/1048576/(dt/86400);
      printf "  trend (last %.1f h): %+.2f GB = %+.1f MB/hour (%d samples)\n",
             dt/3600, dz/1048576, dz/1024/(dt/3600), cnt;
      if(perday > 0.5)
        printf "  >> growing ~%.1f GB/day — likely a kernel leak; a reboot reclaims it\n", perday;
      else
        print  "  >> flat/negligible growth — no active leak";
    }' "$WZLOG"
else
  print -r -- "  (no sampler log at $WZLOG)"
  print -r -- "  The live wired figure above is the check; for per-zone attribution run:"
  print -r -- "    sudo ~/skills/memory-health-check/scripts/sample_wired_zones.sh --top"
fi

# --- top memory consumers ----------------------------------------------------
# top's MEM column is the right per-process ranking here; `ps -o rss` has been
# seen to report near-zero RSS in some sandboxed/stripped environments, so we
# use top -l 1 (single non-interactive sample). Print from the PID header down.
top_out=$("$TOP" -l 1 -o mem -n "$TOPN" -stats pid,command,mem 2>/dev/null)
print -r -- ""
print -r -- "=== Top ${TOPN} memory consumers ==="
if [[ -n "$top_out" ]]; then
  print -r -- "$top_out" | awk '/^PID/{p=1} p'
else
  print -r -- "(top unavailable — non-macOS or tool missing)"
fi
exit 0
