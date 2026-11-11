#!/usr/bin/env bash
# Run a command through filter-output.sh and log PASS/FAIL to .godmode/test-log.md.
# Usage: godmode-run.sh <step-id> <command> [args...]
# Output is shown as usual; the exit code is the command's own. Logging never fails loudly.

if [ $# -lt 2 ]; then
  echo "usage: godmode-run.sh <step-id> <command> [args...]" >&2
  exit 2
fi

step="$1"; shift
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

"$(dirname "$0")/filter-output.sh" "$@" > "$tmp" 2>&1
code=$?
cat "$tmp"

{
  dir="${CLAUDE_PROJECT_DIR:-$PWD}/.godmode"
  log="$dir/test-log.md"
  mkdir -p "$dir"
  [ -f "$log" ] || printf '# Test log (written by godmode-run.sh)\n\n' > "$log"

  if [ "$code" -eq 0 ]; then res="PASS (exit 0)"; else res="FAIL (exit $code)"; fi
  # Prefer a test-framework count line (Catch2/pytest style) over a generic pass/fail line.
  clean=$(tr -d '\r' < "$tmp" | grep -v -e '^\[exit code:' -e '^\[filter-output\]')
  summary=$(printf '%s\n' "$clean" | grep -i -E 'test cases|assertions' | tail -n 1)
  [ -n "$summary" ] || summary=$(printf '%s\n' "$clean" | grep -i -E 'tests passed|passed|failed' | tail -n 1)
  summary=$(printf '%s' "$summary" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
  entry="- $(date '+%Y-%m-%d %H:%M') | $step | $res | \`$*\`"
  [ -n "$summary" ] && entry="$entry — $summary"
  printf '%s\n' "$entry" >> "$log"
  if [ "$code" -ne 0 ]; then
    tr -d '\r' < "$tmp" | grep -v '^\[exit code:' | tail -n 15 | sed 's/^/    /' >> "$log"
  fi
} 2>/dev/null || true

exit "$code"
