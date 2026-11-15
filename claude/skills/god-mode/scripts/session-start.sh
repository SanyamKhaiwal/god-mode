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

open_request() {
  # Requirements ledger (SKILL.md section 0.5): print it while any item is still unchecked.
  local req="$DIR/REQUEST.md"
  [ -f "$req" ] || return 0
  grep -q -E '^[[:space:]]*- \[ \]' "$req" || return 0
  echo "=== GOD MODE: unfinished requirements in .godmode/REQUEST.md ==="
  echo "Before writing code: check every item below against the current code, then finish the unchecked ones."
  echo
  head -n "$MAX_LINES" "$req" | tr -d '\r'
}

session_log() {
  # Tail of .godmode/SESSION.md (written by hubs/session-log-hook.py: prompts verbatim + what was done each turn).
  # Only while a task is open: an unticked ledger item or an unfinished plan.
  local log="$DIR/SESSION.md" hook="$HOME/.claude/hubs/session-log-hook.py" open=0 status
  [ -f "$log" ] && [ -f "$hook" ] || return 0
  [ -f "$DIR/REQUEST.md" ] && grep -q -E '^[[:space:]]*- \[ \]' "$DIR/REQUEST.md" && open=1
  if [ -f "$PLAN" ]; then
    status=$(grep -m1 -i '^Status:' "$PLAN" | sed 's/^[Ss]tatus:[[:space:]]*//' | tr -d '\r' | tr '[:upper:]' '[:lower:]')
    [ "$status" = "done" ] || open=1
  fi
  [ "$open" = 1 ] || return 0
  echo
  CLAUDE_PROJECT_DIR="$ROOT" python -I "$hook" tail 60 | tr -d '\r'
}

# The dependency graph is optional and built on demand only (SKILL.md section 3a); never here.
project_state 2>/dev/null
active_task 2>/dev/null
open_request 2>/dev/null
session_log 2>/dev/null
exit 0
