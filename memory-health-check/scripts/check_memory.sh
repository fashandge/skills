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

[[ -x $MP ]]     || MP=$(command -v memory_pressure 2>/dev/null || echo memory_pressure)
[[ -x $VMSTAT ]] || VMSTAT=$(command -v vm_stat 2>/dev/null || echo vm_stat)
[[ -x $SYSCTL ]] || SYSCTL=$(command -v sysctl 2>/dev/null || echo sysctl)

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

(( ${#reasons[@]} == 0 )) && reasons+=("free headroom, light swap, modest compression")

# --- report ------------------------------------------------------------------
print -r -- "=== macOS memory health ==="
print -r -- "Physical RAM:          ${phys_gb} GB"
print -r -- "memory_pressure free:  ${free_pct:-?}%"
print -r -- "Compressor occupied:   ${occ_gb} GB  (${occ_pct}% of RAM)"
print -r -- "Compressor stored:     ${stored_gb} GB original  →  ${comp_ratio}:1 compression"
print -r -- "Swap used:             ${swap_used_gb} GB  (of ${swap_total:-?} MB total)"
print -r -- ""
print -r -- "VERDICT: ${verdict}"
for r in "${reasons[@]}"; do print -r -- "  - $r"; done
exit 0
