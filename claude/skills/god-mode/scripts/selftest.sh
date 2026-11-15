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
  printf 'Status: in progress\n### S1: x [T1] [status: todo]\n' > "$d/.godmode/PLAN.md"
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

# Escalation ladder: 1st fail -> systematic debugging, 2nd -> solver (Opus), 3rd -> ask user; a PASS resets
LD="$T/ladder"; mkdir -p "$LD"
o1=$(CLAUDE_PROJECT_DIR="$LD" bash "$S/godmode-run.sh" S2 bash -c 'exit 1')
o2=$(CLAUDE_PROJECT_DIR="$LD" bash "$S/godmode-run.sh" S2 bash -c 'exit 1')
o3=$(CLAUDE_PROJECT_DIR="$LD" bash "$S/godmode-run.sh" S2 bash -c 'exit 1')
has "$o1" "1st failure of S2" && has "$o1" "systematic-debugging/QUICK.md" && r=1 || r=0; check "A ladder: 1st failure -> systematic debugging" $r
has "$o2" "2nd failure of S2" && has "$o2" "solver" && r=1 || r=0; check "A ladder: 2nd failure -> Opus solver" $r
has "$o3" "Stop and ask the user" && r=1 || r=0; check "A ladder: 3rd failure -> ask the user" $r
CLAUDE_PROJECT_DIR="$LD" bash "$S/godmode-run.sh" S2 true >/dev/null
o4=$(CLAUDE_PROJECT_DIR="$LD" bash "$S/godmode-run.sh" S2 bash -c 'exit 1')
o5=$(CLAUDE_PROJECT_DIR="$LD" bash "$S/godmode-run.sh" S3 bash -c 'exit 1')
o6=$(CLAUDE_PROJECT_DIR="$LD" bash "$S/godmode-run.sh" BASELINE bash -c 'exit 1')
has "$o4" "1st failure of S2" && has "$o5" "1st failure of S3" && ! has "$o6" "LADDER" && r=1 || r=0; check "A ladder: PASS resets, per step, BASELINE exempt" $r
[ -f "$S/../superpowers/systematic-debugging/QUICK.md" ] && [ $(ls "$S"/../superpowers/*/QUICK.md | wc -l) -eq 9 ] && r=1 || r=0; check "A ladder guides are bundled" $r

# Filter keeps the location of each failure (last Python frame before the exception)
FO="$T/fo"; mkdir -p "$FO"; { for i in $(seq 1 100); do echo "noise $i"; done
  printf 'Traceback (most recent call last):\n  File "a.py", line 3, in <module>\n    f()\n  File "core.py", line 451, in f\n    x = y[9]\nIndexError: list index out of range\n'; } > "$FO/out.txt"
out=$(bash "$S/filter-output.sh" cat "$FO/out.txt")
has "$out" "failure locations" && has "$out" 'File "core.py", line 451' && r=1 || r=0; check "D filter keeps last traceback frame" $r

# ---- B: check-handoff ----
B="$T/B"; mkdir -p "$B"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$B" bash "$S/check-handoff.sh"); rc=$?
[ $rc -eq 0 ] && [ -z "$out" ] && r=1 || r=0; check "B silent with no PLAN" $r

d=$(mkrepo b_done); printf 'Status: DONE\n' > "$d/.godmode/PLAN.md"
echo h > "$d/.godmode/HANDOFF.md"; sleep 1; echo x >> "$d/a.txt"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh"); rc=$?
[ $rc -eq 0 ] && has "$out" '"decision":"block"' && has "$out" "not archived" && r=1 || r=0; check "B blocks done-but-unarchived" $r
mkdir -p "$d/.godmode/archive/x"; mv "$d/.godmode/PLAN.md" "$d/.godmode/HANDOFF.md" "$d/.godmode/archive/x/"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh")
[ -z "$out" ] && r=1 || r=0; check "B silent once archived" $r

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

# Requirements ledger (Direct route: REQUEST.md only, no PLAN.md): unticked items + code edited after the ledger -> block once
mkledger() { local d; d=$(mkrepo "$1"); rm -f "$d/.godmode/PLAN.md"; printf '# Request\nx\n- [ ] 1. a\n- [x] 2. b\n' > "$d/.godmode/REQUEST.md"; echo "$d"; }
d=$(mkledger l_open); sleep 1; echo x >> "$d/a.txt"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh")
has "$out" '"decision":"block"' && has "$out" "REQUEST.md" && has "$out" "1." && r=1 || r=0; check "L blocks unticked ledger after code edit" $r
out=$(echo '{"stop_hook_active": true}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh")
[ -z "$out" ] && r=1 || r=0; check "L ledger block only once (stop_hook_active)" $r
d=$(mkledger l_noedit)
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh")
[ -z "$out" ] && r=1 || r=0; check "L silent when no code changed" $r
d=$(mkledger l_ticked); sleep 1; echo x >> "$d/a.txt"; sleep 1; printf -- '- [x] 1. a\n- [x] 2. b\n' > "$d/.godmode/REQUEST.md"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh")
[ -z "$out" ] && r=1 || r=0; check "L silent when every item ticked" $r
d=$(mkledger l_upd); sleep 1; echo x >> "$d/a.txt"; sleep 1; touch "$d/.godmode/REQUEST.md"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh")
[ -z "$out" ] && r=1 || r=0; check "L silent when ledger updated after the edit" $r

# Unfinished finish: every step done, plan not done, HANDOFF current -> block once with section 6 reminder
d=$(mkrepo b_fin); printf 'Status: in progress\n### S1: a [T1] [status: done]\n### S2: b [T2] [status: Done]\n' > "$d/.godmode/PLAN.md"
echo x >> "$d/a.txt"; sleep 1; echo h > "$d/.godmode/HANDOFF.md"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh")
has "$out" '"decision":"block"' && has "$out" "full-route.md section 4" && r=1 || r=0; check "B blocks when all steps done but task unfinished" $r
out=$(echo '{"stop_hook_active": true}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh")
[ -z "$out" ] && r=1 || r=0; check "B finish-block only once (stop_hook_active)" $r
printf 'Status: in progress\n### S1: a [T1] [status: done]\n### S2: b [T2] [status: todo]\n' > "$d/.godmode/PLAN.md"; sleep 1; touch "$d/.godmode/HANDOFF.md"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh")
[ -z "$out" ] && r=1 || r=0; check "B silent while steps remain" $r

# Free-form plan (no template step headings) -> block with template reminder
d=$(mkrepo b_free); printf 'Status: in progress\n## S1 stuff - Status: done\n' > "$d/.godmode/PLAN.md"; sleep 1; echo h > "$d/.godmode/HANDOFF.md"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/check-handoff.sh")
has "$out" '"decision":"block"' && has "$out" "template format" && r=1 || r=0; check "B blocks free-form plan" $r

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

# Session log tail: printed only while a task is open (unticked ledger item or unfinished plan)
d="$T/c5"; mkdir -p "$d/.godmode"; printf -- '- [ ] 1. open item\n' > "$d/.godmode/REQUEST.md"
printf '# Session log\n## 10:00 USER\nLOG-MARKER-PROMPT\n' > "$d/.godmode/SESSION.md"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/session-start.sh")
has "$out" "LOG-MARKER-PROMPT" && has "$out" "SESSION.md" && r=1 || r=0; check "C session log tail printed with open ledger" $r
printf -- '- [x] 1. open item\n' > "$d/.godmode/REQUEST.md"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/session-start.sh")
! has "$out" "LOG-MARKER-PROMPT" && r=1 || r=0; check "C session log silent when nothing is open" $r
d="$T/c6"; mkdir -p "$d/.godmode"; printf 'Status: in progress\n' > "$d/.godmode/PLAN.md"; printf '## 10:00 USER\nPLAN-LOG-MARKER\n' > "$d/.godmode/SESSION.md"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/session-start.sh")
has "$out" "PLAN-LOG-MARKER" && r=1 || r=0; check "C session log tail printed with unfinished plan" $r

# Graph side effect: no .godmode/ created in a project without an active PLAN
d="$T/c4"; mkdir -p "$d"; printf 'import os\n' > "$d/x.py"
echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/session-start.sh" >/dev/null
[ ! -e "$d/.godmode" ] && r=1 || r=0; check "C no .godmode created without PLAN" $r
d="$T/c5"; mkdir -p "$d/.godmode"; printf 'Status: in progress\n' > "$d/.godmode/PLAN.md"; printf 'import os\n' > "$d/x.py"
echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/session-start.sh" >/dev/null
[ ! -f "$d/.godmode/project-map.json" ] && r=1 || r=0; check "C never builds the graph (on demand only)" $r

# Requirements ledger: printed while unchecked items remain, silent when all ticked
d="$T/c6"; mkdir -p "$d/.godmode"; printf '# Request\r\nAdd X\r\n- [x] 1. flag --x\r\n- [ ] 2. warning on stderr\r\n' > "$d/.godmode/REQUEST.md"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/session-start.sh")
has "$out" "unfinished requirements" && has "$out" "2. warning on stderr" && r=1 || r=0; check "C open REQUEST.md printed" $r
case "$out" in *$'\r'*) r=0;; *) r=1;; esac; check "C REQUEST.md CR stripped" $r
printf '# Request\n- [x] 1. a\n- [x] 2. b\n' > "$d/.godmode/REQUEST.md"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$d" bash "$S/session-start.sh")
! has "$out" "unfinished requirements" && r=1 || r=0; check "C silent when all requirements ticked" $r

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

# E2: JS/TS support with internal edge a -> b
j="$T/graph_js"; mkdir -p "$j/src"
printf "import { b } from './b';\nimport React from 'react';\nexport const a = b;\n" > "$j/src/a.js"
printf "export const b = 1;\n" > "$j/src/b.ts"
python "$S/build-graph.py" "$j" "$j/.godmode/project-map.json" --quiet
r=$(python - "$j/.godmode/project-map.json" <<'PY'
import json, sys
g = json.load(open(sys.argv[1]))
ok = g['meta']['total_files'] >= 2 and any(e['from'] == 'src/a.js' and e['to'] == 'src/b.ts' for e in g['edges'])
print(1 if ok else 0)
PY
)
check "E JS project indexes files and resolves internal edge a->b" "$r"

# E3: Python stdlib not in hubs, sibling is an internal edge
p="$T/graph_py"; mkdir -p "$p"
printf "import os\nimport sys\nimport helper\nprint(os.name, helper)\n" > "$p/main.py"
printf "import os\nX = 1\n" > "$p/helper.py"
python "$S/build-graph.py" "$p" "$p/.godmode/project-map.json" --quiet
r=$(python - "$p/.godmode/project-map.json" <<'PY'
import json, sys
g = json.load(open(sys.argv[1]))
hubs = [h[0] for h in g['hub_nodes']]
ok = 'os' not in hubs and 'sys' not in hubs and all(h in g['nodes'] for h in hubs) \
    and any(e['from'] == 'main.py' and e['to'] == 'helper.py' for e in g['edges']) \
    and 'os' in g['meta']['external_modules']
print(1 if ok else 0)
PY
)
check "E Python hubs exclude stdlib; sibling is internal edge" "$r"

# E4: graph-brief.txt written and <= 60 lines
if [ -f "$p/.godmode/graph-brief.txt" ] && [ "$(wc -l < "$p/.godmode/graph-brief.txt")" -le 60 ] && [ -f "$d/.godmode/graph-brief.txt" ]; then r=1; else r=0; fi
check "E graph-brief.txt written (<=60 lines)" $r

# E5: graph-query (symbols, importers, outline, refs, missing map)
q="$T/graph_q"; mkdir -p "$q/pkg"
printf 'import os\n\nclass Widget:\n    def spin(self):\n        pass\n\ndef make():\n    return Widget()\n' > "$q/pkg/core.py"
printf 'from pkg.core import Widget, make\n\nMAX_N = 3\nw = Widget()\n' > "$q/app.py"
python "$S/build-graph.py" "$q" "$q/.godmode/project-map.json" --quiet
Q="python $S/graph-query.py --map $q/.godmode/project-map.json"
out=$($Q where Widget)
has "$out" "pkg/core.py:3  class  Widget" && r=1 || r=0; check "E query where finds class with line" $r
out=$($Q where Widget.spin)
has "$out" "pkg/core.py:4  method  Widget.spin" && r=1 || r=0; check "E query where finds method with line" $r
out=$($Q importers pkg/core.py)
has "$out" "app.py" && r=1 || r=0; check "E query importers lists importing file" $r
out=$($Q outline core.py)
has "$out" "Widget.spin" && has "$out" "make" && has "$out" "class" && r=1 || r=0; check "E query outline lists symbols" $r
out=$($Q refs Widget)
has "$out" "app.py" && r=1 || r=0; check "E query refs finds from-import user" $r
(cd "$T" && python "$S/graph-query.py" --map "$T/nope/map.json" where X >/dev/null 2>&1); rc=$?
[ $rc -eq 2 ] && r=1 || r=0; check "E query explicit missing map exits 2" $r
LZ="$T/lazy"; mkdir -p "$LZ"; printf 'class Gadget:\n    pass\n' > "$LZ/g.py"
out=$(cd "$LZ" && python "$S/graph-query.py" where Gadget 2>&1)
has "$out" "g.py:1" && [ -f "$LZ/.godmode/project-map.json" ] && r=1 || r=0; check "E query lazily builds the default map" $r

# C++ export/API macros (tinyxml2, Unreal): class LIB_API Name
CX="$T/cxx"; mkdir -p "$CX"; printf '#pragma once\nclass MYGAME_API AMyActor : public AActor {\n};\nstruct FOO_API FHit final {\n};\nclass Plain {\n};\n' > "$CX/a.h"
python "$S/build-graph.py" "$CX" "$CX/m.json" --quiet
out=$(python "$S/graph-query.py" --map "$CX/m.json" where AMyActor; python "$S/graph-query.py" --map "$CX/m.json" where FHit; python "$S/graph-query.py" --map "$CX/m.json" where Plain)
has "$out" "a.h:2  class  AMyActor" && has "$out" "a.h:4  struct  FHit" && has "$out" "a.h:6  class  Plain" && r=1 || r=0; check "E C++ classes with export macros indexed" $r

[ $fails -eq 0 ] || exit 1
exit 0
