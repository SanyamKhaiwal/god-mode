#!/usr/bin/env bash
# God Mode Stop hook: block once if files changed after HANDOFF.md was last updated.
# Silent (exit 0) when there is no active plan, the plan is done, or not a git repo.

input=$(cat 2>/dev/null) || input=""
printf '%s' "$input" | grep -q -E '"stop_hook_active"[[:space:]]*:[[:space:]]*true' && exit 0

dir="${CLAUDE_PROJECT_DIR:-$PWD}"
plan="$dir/.godmode/PLAN.md"
handoff="$dir/.godmode/HANDOFF.md"

# Requirements ledger (every route): unticked items in REQUEST.md while code changed after the ledger was last
# touched -> block once and ask for each item to be verified and ticked, or reported as not done.
request="$dir/.godmode/REQUEST.md"
if [ -f "$request" ] && git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  open=$(grep -E '^[[:space:]]*- \[ \]' "$request" | tr -d '\r' | head -n 5)
  if [ -n "$open" ]; then
    changed=$( { git -C "$dir" -c core.quotePath=false ls-files -m -o --exclude-standard; git -C "$dir" -c core.quotePath=false diff --name-only --cached; } 2>/dev/null \
      | grep -v -e '^\.godmode/' -e '^$' | sort -u)
    first=""
    while IFS= read -r f; do
      [ -n "$f" ] || continue
      if [ "$dir/$f" -nt "$request" ]; then first="$f"; break; fi
    done <<< "$changed"
    if [ -n "$first" ]; then
      list=$(printf '%s' "$open" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' ' ')
      printf '{"decision":"block","reason":"God Mode: .godmode/REQUEST.md still has unticked requirements and code changed after it (e.g. %s). Unticked: %s Check each against the code now: tick the ones that are done and true, and say plainly which are not done. Then stop."}\n' "$first" "$list"
      exit 0
    fi
  fi
fi

[ -f "$plan" ] || exit 0
status=$(grep -m1 -i '^Status:' "$plan" | sed 's/^[Ss]tatus:[[:space:]]*//' | tr -d '\r' | tr '[:upper:]' '[:lower:]')
case "$status" in
  planning) exit 0 ;;   # nothing to hand off yet
  done*)
    # Marked done but still in .godmode/ root: the archive step (references/full-route.md section 4, steps 2-4) was skipped.
    echo '{"decision":"block","reason":"God Mode: PLAN.md says done but the task is not archived. Finish references/full-route.md section 4 now: if Route is Full and the reviewer has not run on this diff, run it first; merge non-none Learnings into the project record or CLAUDE.md; then move PLAN.md, HANDOFF.md and test-log.md into .godmode/archive/<YYYY-MM-DD>-<task-slug>/. Then stop."}'
    exit 0 ;;
esac
git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

if [ ! -f "$handoff" ]; then
  echo '{"decision":"block","reason":"God Mode: .godmode/HANDOFF.md is missing while PLAN.md is in progress. Create it now: Status, Current step, Next action, Test log, Decisions, Dead ends, Files touched. Then stop."}'
  exit 0
fi

# Plan must use the template's step headings, or the finish check below can't see the steps.
if ! grep -q -i '^###.*\[status:' "$plan" 2>/dev/null; then
  echo '{"decision":"block","reason":"God Mode: .godmode/PLAN.md has no step headings in the template format, so progress cannot be tracked. Rewrite each step as `### S<n>: <title> [T1|T2|T3] [status: todo|done]` followed by `- Files:`, `- Change:`, `- Acceptance:`, `- Executor:` lines (see assets/PLAN.template.md), keeping the current statuses. Then stop."}'
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
  exit 0
fi

# Every step done but the task not finished: section 6 (verification, review, record, archive) was skipped.
total=$(grep -c -i '^###.*\[status:' "$plan" 2>/dev/null)
donec=$(grep -c -i '^###.*\[status:[[:space:]]*done[[:space:]]*\]' "$plan" 2>/dev/null)
if [ "${total:-0}" -gt 0 ] && [ "$total" -eq "$donec" ]; then
  echo '{"decision":"block","reason":"God Mode: every step in .godmode/PLAN.md is done, but the task is not finished. Run references/full-route.md section 4 now: FINAL verification through godmode-run.sh, the reviewer if the route is Full or a step touched a risk area, merge Learnings and Decisions into the project record or CLAUDE.md, rewrite HANDOFF.md to its final state, set Status: done in both files, and archive them. Then stop."}'
fi
exit 0
