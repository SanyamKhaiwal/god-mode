#!/usr/bin/env bash
# God Mode SessionStart hook.
# 1. Project state: if CLAUDE.md names a "Project record:" file, print its injected block
#    (between godmode:inject markers) and the tail of the "Results log:" file.
# 2. If the project has an unfinished .godmode task, print PLAN.md and HANDOFF.md
#    so they enter the new session's context (after startup, /clear, or compaction).

cat > /dev/null 2>&1 || true   # discard hook input JSON on stdin

ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
DIR="$ROOT/.godmode"
PLAN="$DIR/PLAN.md"
HANDOFF="$DIR/HANDOFF.md"
MAX_LINES=400

# First backtick-quoted path on the first CLAUDE.md line containing the label.
claude_path() {
  [ -f "$ROOT/CLAUDE.md" ] || return 0
  grep -m1 -F "$1" "$ROOT/CLAUDE.md" | tr -d '\r' | sed -n 's/^[^`]*`\([^`]*\)`.*/\1/p'
}

project_state() {
  local rec res
  rec=$(claude_path "Project record:")
  if [ -n "$rec" ] && [ -f "$ROOT/$rec" ]; then
    echo "=== PROJECT STATE (from $rec) ==="
    tr -d '\r' < "$ROOT/$rec" | awk '/<!-- godmode:inject:end -->/{f=0} f{print} /<!-- godmode:inject:start -->/{f=1}' | head -n 150
    echo
  fi
  res=$(claude_path "Results log:")
  if [ -n "$res" ] && [ -f "$ROOT/$res" ]; then
    echo "--- last results ($res) ---"
    tr -d '\r' < "$ROOT/$res" | tail -n 12
    echo
  fi
}

active_task() {
  [ -f "$PLAN" ] || return 0
  local status
  status=$(grep -m1 -i '^Status:' "$PLAN" | sed 's/^[Ss]tatus:[[:space:]]*//' | tr -d '\r' | tr '[:upper:]' '[:lower:]')
  [ "$status" = "done" ] && return 0

  echo "=== GOD MODE: unfinished task found in .godmode/ (status: ${status:-unknown}) ==="
  echo "Resume from HANDOFF.md 'Next action' unless the user starts something new."
  echo
  echo "----- .godmode/PLAN.md -----"
  head -n "$MAX_LINES" "$PLAN"
  if [ -f "$HANDOFF" ]; then
    echo
    echo "----- .godmode/HANDOFF.md -----"
    head -n "$MAX_LINES" "$HANDOFF"
  fi
}

update_graph() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [ -f "$script_dir/build-graph.py" ]; then
    python "$script_dir/build-graph.py" "$ROOT" "$DIR/project-map.json" --quiet 2>/dev/null || true
  fi
}

project_state 2>/dev/null
active_task 2>/dev/null
update_graph 2>/dev/null
exit 0
