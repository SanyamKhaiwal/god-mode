#!/usr/bin/env bash
# Run a command and print a trimmed version of its output, keeping what matters.
# Usage: filter-output.sh <command> [args...]
#   e.g. filter-output.sh pytest -q
#        filter-output.sh bash -c "make 2>&1 | tee build.log"
# Short output is printed in full. Long output keeps error/failure lines plus the tail.
# The command's exit code is preserved.
# Tunables (env): GM_FULL_MAX (default 80), GM_MATCH_MAX (default 60), GM_TAIL (default 40)

if [ $# -eq 0 ]; then
  echo "usage: filter-output.sh <command> [args...]" >&2
  exit 2
fi

FULL_MAX="${GM_FULL_MAX:-80}"
MATCH_MAX="${GM_MATCH_MAX:-60}"
TAIL="${GM_TAIL:-40}"

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

"$@" > "$tmp" 2>&1
code=$?
total=$(wc -l < "$tmp" | tr -d ' ')

if [ "$total" -le "$FULL_MAX" ]; then
  cat "$tmp"
else
  echo "[filter-output] $total lines, exit $code. Showing error/failure lines, then the last $TAIL lines."
  echo "----- matches -----"
  grep -n -i -E 'error|fail|failed|exception|traceback|assert|panic|fatal|undefined reference|cannot|not found|warning' "$tmp" \
    | awk '!seen[substr($0, index($0, ":")+1)]++' \
    | head -n "$MATCH_MAX"
  # Where each failure happened: the last Python frame before an exception line, and the first Java "at" frame.
  locs=$(awk '
    /^[[:space:]]*File ".*", line [0-9]+/ { f = NR ": " $0; next }
    /^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception)(:|$)/ { if (f != "") print f; f = "" }
    /^[[:space:]]+at [A-Za-z0-9_.$<>]+\(.*:[0-9]+\)/ { if (!java_seen) { print NR ": " $0; java_seen = 1 } next }
    /Exception|Error/ { java_seen = 0 }
  ' "$tmp" | awk '!seen[substr($0, index($0, ":")+1)]++' | head -n 30)
  if [ -n "$locs" ]; then
    echo "----- failure locations -----"
    printf '%s\n' "$locs"
  fi
  echo "----- tail -----"
  tail -n "$TAIL" "$tmp"
fi

echo "[exit code: $code]"
exit "$code"
