#!/usr/bin/env bash
# Self-test for godmode-run.sh, check-handoff.sh and session-start.sh (temp dirs only).
S="$(cd "$(dirname "$0")" && pwd)"
fails=0
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT

ok()  { echo "PASS $1"; }
bad() { echo "FAIL $1"; fails=$((fails+1)); }
check() { if [ "$2" = 1 ]; then ok "$1"; else bad "$1"; fi; }
has() { case "$1" in *"$2"*) return 0;; esac; return 1; }

mkrepo() { # mkrepo <name>: temp git repo with an in-progress PLAN.md
  local d="$T/$1"; mkdir -p "$d/.godmode"
  git -C "$d" init -q 2>/dev/null
  git -C "$d" config core.autocrlf false; git -C "$d" config user.email t@t; git -C "$d" config user.name t
  printf 'Status: in progress\n' > "$d/.godmode/PLAN.md"
  echo a > "$d/a.txt"; git -C "$d" add a.txt; git -C "$d" commit -qm init
  echo "$d"
}

# ---- A: godmode-run ----
A="$T/A"; mkdir -p "$A"
out=$(CLAUDE_PROJECT_DIR="$A" bash "$S/godmode-run.sh" s1 bash -c 'echo "All tests passed (3 assertions in 2 test cases)"'); rc=$?
log=$(cat "$A/.godmode/test-log.md" 2>/dev/null)
[ $rc -eq 0 ] && has "$log" "| s1 | PASS (exit 0) |" && has "$log" "— All tests passed (3 assertions in 2 test cases)" && r=1 || r=0
check "A pass logged with summary" $r
has "$log" "# Test log (written by godmode-run.sh)" && r=1 || r=0; check "A header created" $r
out=$(CLAUDE_PROJECT_DIR="$A" bash "$S/godmode-run.sh" s2 bash -c 'echo boom; exit 3'); rc=$?
log=$(cat "$A/.godmode/test-log.md")
[ $rc -eq 3 ] && has "$log" "FAIL (exit 3)" && has "$log" "    boom" && r=1 || r=0
check "A fail logged, exit 3, tail indented" $r
has "$log" "[exit code" && r=0 || r=1; check "A exit-code line omitted from tail" $r
out=$(CLAUDE_PROJECT_DIR="$A" bash "$S/godmode-run.sh" s3 bash -c 'echo "a \`b\` \"c\" \$(x)"'); rc=$?
log=$(cat "$A/.godmode/test-log.md")
[ $rc -eq 0 ] && has "$log" "| s3 | PASS" && r=1 || r=0; check "A backticks/quotes safe" $r

# ---- B: check-handoff ----
B="$T/B"; mkdir -p "$B"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$B" bash "$S/check-handoff.sh"); rc=$?
[ $rc -eq 0 ] && [ -z "$out" ] && r=1 || r=0; check "B silent with no PLAN" $r

d=$(mkrepo b_done); printf 'Status: DONE\n' > "$d/.godmode/PLAN.md"
echo h > "$d/.godmode/HANDOFF.md"; sleep 1; echo x >> "$d/a.txt"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh"); rc=$?
[ $rc -eq 0 ] && [ -z "$out" ] && r=1 || r=0; check "B silent when done" $r

d=$(mkrepo b_blk); echo h > "$d/.godmode/HANDOFF.md"; sleep 1; echo x >> "$d/a.txt"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh"); rc=$?
nl=$(printf '%s\n' "$out" | wc -l | tr -d ' ')
[ $rc -eq 0 ] && [ "$nl" = 1 ] && has "$out" '"decision":"block"' && has "$out" "e.g. a.txt" && r=1 || r=0
check "B blocks when file newer than HANDOFF" $r
out=$(echo '{"stop_hook_active" :  true}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh")
[ -z "$out" ] && r=1 || r=0; check "B silent when stop_hook_active" $r

d=$(mkrepo b_new); echo x >> "$d/a.txt"; sleep 1; echo h > "$d/.godmode/HANDOFF.md"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh")
[ -z "$out" ] && r=1 || r=0; check "B silent when HANDOFF newer" $r

d=$(mkrepo b_miss); echo x >> "$d/a.txt"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh")
has "$out" '"decision":"block"' && r=1 || r=0; check "B blocks when HANDOFF missing" $r

d="$T/b_nogit"; mkdir -p "$d/.godmode"; printf 'Status: in progress\n' > "$d/.godmode/PLAN.md"
out=$(echo '{}' | GIT_CEILING_DIRECTORIES="$T" CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh"); rc=$?
[ $rc -eq 0 ] && [ -z "$out" ] && r=1 || r=0; check "B silent when not a git repo" $r

# ---- C: session-start ----
d="$T/c1"; mkdir -p "$d/Docs" "$d/.godmode"
printf 'x\r\nProject record: `Docs/rec.md`\r\nResults log: `Docs/res.md`\r\n' > "$d/CLAUDE.md"
printf 'before\r\n<!-- godmode:inject:start -->\r\nINJECTED-LINE\r\n<!-- godmode:inject:end -->\r\nafter\r\n' > "$d/Docs/rec.md"
for i in $(seq 1 20); do echo "res$i"; done > "$d/Docs/res.md"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/session-start.sh")
has "$out" "=== PROJECT STATE (from Docs/rec.md) ===" && has "$out" "INJECTED-LINE" && ! has "$out" "before" && ! has "$out" "after" && r=1 || r=0
check "C injected block printed" $r
has "$out" "--- last results (Docs/res.md) ---" && has "$out" "res20" && has "$out" "res9" && ! has "$out" "res8" && r=1 || r=0
check "C results tail printed" $r
case "$out" in *$'\r'*) r=0;; *) r=1;; esac; check "C CR stripped" $r
! has "$out" "=== GOD MODE" && r=1 || r=0; check "C no GOD MODE without PLAN" $r

d="$T/c2"; mkdir -p "$d"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/session-start.sh"); rc=$?
[ $rc -eq 0 ] && [ -z "$out" ] && r=1 || r=0; check "C nothing without CLAUDE.md" $r

d="$T/c3"; mkdir -p "$d/.godmode"; printf 'Status: in progress\n' > "$d/.godmode/PLAN.md"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/session-start.sh")
has "$out" "=== GOD MODE" && r=1 || r=0; check "C active task printed" $r
printf 'Status: done\n' > "$d/.godmode/PLAN.md"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/session-start.sh")
! has "$out" "=== GOD MODE" && r=1 || r=0; check "C no GOD MODE when done" $r

# ---- D: edge cases found in review ----
d=$(mkrepo "d space"); echo h > "$d/.godmode/HANDOFF.md"; sleep 1; echo x >> "$d/a.txt"
w=$(cygpath -w "$d" 2>/dev/null || echo "$d")
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$w" bash "$S/check-handoff.sh")
has "$out" '"decision":"block"' && r=1 || r=0; check "D blocks with Windows-form path containing a space" $r
printf 'Status: planning\r\n' > "$d/.godmode/PLAN.md"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$w" bash "$S/check-handoff.sh")
[ -z "$out" ] && r=1 || r=0; check "D silent while Status is planning (CRLF)" $r
d=$(mkrepo d_utf); echo h > "$d/.godmode/HANDOFF.md"; sleep 1; echo x > "$d/é.txt"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh")
has "$out" '"decision":"block"' && r=1 || r=0; check "D blocks on a changed non-ASCII file name" $r
d=$(mkrepo d_ign); printf 'ignored.txt\n' > "$d/.gitignore"; git -C "$d" add .gitignore; git -C "$d" commit -qm ign
echo h > "$d/.godmode/HANDOFF.md"; sleep 1; echo x > "$d/ignored.txt"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh")
[ -z "$out" ] && r=1 || r=0; check "D silent for a gitignored file" $r
out=$(bash "$S/godmode-run.sh" only-step 2>&1); rc=$?
[ $rc -eq 2 ] && r=1 || r=0; check "D godmode-run usage error exits 2" $r
out=$(CLAUDE_PROJECT_DIR="$A" bash "$S/godmode-run.sh" s4 bash -c 'echo "0 failed"; echo "All tests passed (9 assertions in 4 test cases)"; echo "100% tests passed, 0 tests failed out of 1"')
has "$(cat "$A/.godmode/test-log.md")" "— All tests passed (9 assertions in 4 test cases)" && r=1 || r=0
check "D summary prefers the test-case count line" $r

# ---- E: AST graph builder & summary ----
d="$T/graph_test"; mkdir -p "$d/src" "$d/java" "$d/cpp"
printf 'class PyModel:\n    def save(self):\n        pass\n' > "$d/src/model.py"
printf 'package com.test;\npublic class JavaService extends BaseService {\n    public void run() {}\n}\n' > "$d/java/JavaService.java"
printf '#include "model.h"\nclass CppGateway : public BaseGateway {\npublic:\n    void execute();\n};\n' > "$d/cpp/gateway.h"

python "$S/build-graph.py" "$d" "$d/.godmode/project-map.json" --quiet; rc=$?
[ $rc -eq 0 ] && [ -f "$d/.godmode/project-map.json" ] && r=1 || r=0
check "E build-graph creates project-map.json" $r

out=$(python "$S/graph-summary.py" "$d/.godmode/project-map.json")
has "$out" "Project Architecture Map" && has "$out" "PyModel" && r=1 || r=0
check "E graph-summary outputs architecture brief" $r

[ $fails -eq 0 ] || exit 1
exit 0
