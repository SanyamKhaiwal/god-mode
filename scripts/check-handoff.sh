#!/usr/bin/env bash
# God Mode Stop hook: block once if files changed after HANDOFF.md was last updated.
# Silent (exit 0) when there is no active plan, the plan is done, or not a git repo.

input=$(cat 2>/dev/null) || input=""
printf '%s' "$input" | grep -q -E '"stop_hook_active"[[:space:]]*:[[:space:]]*true' && exit 0

dir="${CLAUDE_PROJECT_DIR:-$PWD}"
plan="$dir/.godmode/PLAN.md"
handoff="$dir/.godmode/HANDOFF.md"

[ -f "$plan" ] || exit 0
status=$(grep -m1 -i '^Status:' "$plan" | sed 's/^[Ss]tatus:[[:space:]]*//' | tr -d '\r' | tr '[:upper:]' '[:lower:]')
case "$status" in done|planning) exit 0 ;; esac   # nothing to hand off yet, or finished
git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

if [ ! -f "$handoff" ]; then
  echo '{"decision":"block","reason":"God Mode: .godmode/HANDOFF.md is missing while PLAN.md is in progress. Create it now: Status, Current step, Next action, Test log, Decisions, Dead ends, Files touched. Then stop."}'
  exit 0
fi

files=$( { git -C "$dir" -c core.quotePath=false ls-files -m -o --exclude-standard; git -C "$dir" -c core.quotePath=false diff --name-only --cached; } 2>/dev/null \
  | grep -v -e '^\.godmode/' -e '^$' | sort -u)

n=0; first=""
while IFS= read -r f; do
  [ -n "$f" ] || continue
  if [ "$dir/$f" -nt "$handoff" ]; then
    n=$((n+1)); [ -z "$first" ] && first="$f"
  fi
done <<< "$files"

if [ "$n" -gt 0 ]; then
  esc=$(printf '%s' "$first" | sed 's/\\/\\\\/g; s/"/\\"/g')
  printf '{"decision":"block","reason":"God Mode: %s file(s) changed after .godmode/HANDOFF.md was last updated (e.g. %s). Update HANDOFF.md now: Status, Current step, Next action, and append to Test log / Decisions / Dead ends / Files touched. Then stop."}\n' "$n" "$esc"
fi
exit 0
