#!/bin/bash
# worker_pane.sh — open/close the passive live-view pane for a delegated worker run
# (delegate-first skill). The pane only ever runs `tail -F` (or a caller-supplied
# view command); the worker itself stays a harness-tracked background job.
#
# Safety invariants (the reason this script exists — see SKILL.md "Run visibly"):
#   * every cmux send/send-key/close-surface call passes an explicit --surface;
#     bare `cmux send ...` targets $CMUX_SURFACE_ID = the surface hosting the
#     CALLING agent session, i.e. it types into / closes the orchestrator itself
#   * close refuses to target the calling session's own surface, in both its
#     UUID and short-ref (surface:N) forms
set -u

usage() {
  cat <<'EOF'
worker_pane.sh — visible live-view pane for a delegated worker (cmux or tmux)

USAGE
  worker_pane.sh open  --stream FILE [--cmd COMMAND] [--title NAME]
  worker_pane.sh close --surface surface:N | --window NAME
  worker_pane.sh --help

SUBCOMMANDS
  open   Create an unfocused terminal pane running COMMAND (default:
         tail -F 'FILE'). Prints one JSON object on stdout and exits 0:
           {"backend":"cmux","surface":"surface:N","close":"worker_pane.sh close --surface surface:N"}
           {"backend":"tmux","window":"NAME","close":"worker_pane.sh close --window NAME"}
           {"backend":"none","reason":"..."}   <- no cmux/tmux; run headless, NOT an error
  close  Close the pane opened by `open`, identified by the exact value the
         open JSON reported. Refuses the calling session's own surface.

OPTIONS
  --stream FILE   File the pane tails (required unless --cmd is given)
  --cmd COMMAND   Full view command to run in the pane instead of tail -F;
                  use for remote streams, e.g. --cmd "ssh box tail -F /path/stream"
  --title NAME    tmux window name (default worker-<pid>); ignored under cmux

EXIT CODES
  0 success (including backend "none")   1 usage error   2 backend command failed

EXAMPLE
  scripts/worker_pane.sh open --stream /tmp/worker-last.stream
  # ... after review ...
  scripts/worker_pane.sh close --surface surface:86
EOF
}

fail_usage() { echo "ERROR: $1" >&2; echo "Run with --help for the full schema." >&2; exit 1; }
json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

# Own-surface refs of the calling session (cmux only; empty when not under cmux).
own_surface_uuid="${CMUX_SURFACE_ID:-}"
own_surface_ref=""
if [ -n "$own_surface_uuid" ] && command -v cmux >/dev/null 2>&1; then
  own_surface_ref=$(cmux identify 2>/dev/null | sed -n 's/.*"surface_ref"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
fi

cmd="${1:-}"; shift 2>/dev/null || true
case "$cmd" in
  -h|--help|help|"") usage; [ "$cmd" = "" ] && exit 1 || exit 0 ;;
esac

STREAM="" VIEWCMD="" TITLE="" SURFACE="" WINDOW=""
while [ $# -gt 0 ]; do
  case "$1" in
    --stream)  STREAM="${2:-}"; shift 2 ;;
    --cmd)     VIEWCMD="${2:-}"; shift 2 ;;
    --title)   TITLE="${2:-}"; shift 2 ;;
    --surface) SURFACE="${2:-}"; shift 2 ;;
    --window)  WINDOW="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) fail_usage "unknown flag '$1' for '$cmd' (valid: --stream --cmd --title --surface --window)" ;;
  esac
done

case "$cmd" in
open)
  [ -n "$STREAM$VIEWCMD" ] || fail_usage "open needs --stream FILE (or --cmd COMMAND)"
  [ -n "$VIEWCMD" ] || VIEWCMD="tail -F '$STREAM'"

  if [ -n "${CMUX_WORKSPACE_ID:-}" ] && command -v cmux >/dev/null 2>&1 && cmux ping >/dev/null 2>&1; then
    out=$(cmux new-surface --type terminal --workspace "$CMUX_WORKSPACE_ID" --focus false 2>&1)
    sid=$(printf '%s' "$out" | grep -o 'surface:[0-9]*' | head -1)
    if [ -z "$sid" ]; then
      echo "ERROR: could not parse surface ref from new-surface output: $out" >&2; exit 2
    fi
    # Paranoia: never type into the calling session's own surface.
    if [ "$sid" = "$own_surface_ref" ]; then
      echo "ERROR: new-surface returned the calling session's own surface ($sid); refusing to send" >&2; exit 2
    fi
    # Trailing \n is cmux-send's Enter escape (see `cmux send --help`).
    if ! cmux send --surface "$sid" "$VIEWCMD"'\n' >/dev/null 2>&1; then
      echo "ERROR: cmux send --surface $sid failed" >&2; exit 2
    fi
    printf '{"backend":"cmux","surface":"%s","close":"worker_pane.sh close --surface %s"}\n' "$sid" "$sid"
    exit 0
  fi

  if [ -n "${TMUX:-}" ] && command -v tmux >/dev/null 2>&1; then
    win="${TITLE:-worker-$$}"
    if ! tmux new-window -d -n "$win" "$VIEWCMD" 2>/dev/null; then
      echo "ERROR: tmux new-window failed" >&2; exit 2
    fi
    printf '{"backend":"tmux","window":"%s","close":"worker_pane.sh close --window %s"}\n' \
      "$(json_escape "$win")" "$(json_escape "$win")"
    exit 0
  fi

  printf '{"backend":"none","reason":"no cmux workspace and no tmux session; run the worker headless"}\n'
  exit 0
  ;;

close)
  if [ -n "$SURFACE" ]; then
    case "$SURFACE" in
      surface:[0-9]*) : ;;
      *) fail_usage "--surface must be a short ref like surface:86 (the value 'open' reported), got '$SURFACE'" ;;
    esac
    if [ "$SURFACE" = "$own_surface_ref" ] || [ "$SURFACE" = "$own_surface_uuid" ]; then
      echo "ERROR: $SURFACE is the calling session's own surface; closing it would kill this agent session. Only close the surface that 'open' reported." >&2
      exit 1
    fi
    if ! cmux close-surface --surface "$SURFACE" >/dev/null 2>&1; then
      echo "ERROR: cmux close-surface --surface $SURFACE failed (already closed?)" >&2; exit 2
    fi
    printf '{"closed":"%s"}\n' "$SURFACE"
    exit 0
  fi
  if [ -n "$WINDOW" ]; then
    if ! tmux kill-window -t "=$WINDOW" 2>/dev/null; then
      echo "ERROR: tmux kill-window -t =$WINDOW failed (already closed?)" >&2; exit 2
    fi
    printf '{"closed":"%s"}\n' "$(json_escape "$WINDOW")"
    exit 0
  fi
  fail_usage "close needs --surface surface:N (cmux) or --window NAME (tmux)"
  ;;

*)
  fail_usage "unknown subcommand '$cmd' (valid: open, close)"
  ;;
esac
