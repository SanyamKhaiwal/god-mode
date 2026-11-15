#!/usr/bin/env bash
# Hard benchmark v2. Usage: bash run.sh <task> <arm>   task = ml | refactor | cache ; arm = opus | sonnet | router
set -uo pipefail
TASK="$1"; ARM="$2"
OUT="/d/Coding projects/Skills Testing and Claude setup/test-runs/hard2"
DIR="/d/Coding projects/hard2-runs/$TASK-$ARM"
rm -rf "$DIR"; mkdir -p "$(dirname "$DIR")"
case "$TASK" in
  ml)       git clone -q "/d/Coding projects/hard2-ml" "$DIR" ;;
  refactor) git clone -q "/d/Coding projects/godmode-big-test" "$DIR" && git -C "$DIR" checkout -q 4ad5748 ;;
  cache)    git clone -q "/d/Coding projects/hard2-cache" "$DIR" ;;
  ladder)   git clone -q "/d/Coding projects/hard-base3" "$DIR" && git -C "$DIR" checkout -q e3572a1 ;;
  plugin)   git clone -q "/d/Coding projects/godmode-big-test" "$DIR" && git -C "$DIR" checkout -q 4ad5748 ;;
esac
git -C "$DIR" config user.email t@t; git -C "$DIR" config user.name t
LADDER='After a recent change, 18 tests in scripts/tests fail: search ranking looks wrong and some normalization tests fail too. Find the real cause or causes and fix them properly, with regression tests. Do not weaken the tests, the score thresholds, the stop-word list or the synonym table.'
PLUGIN='Design and implement a plugin mechanism for search domains. A new domain is added by dropping a folder plugins/<name>/ (at the repository root, next to data/) that contains data.csv and plugin.json with the keys search_cols and output_cols, without editing any existing code. `search.py --domain <name>` must work for plugin domains (text and --json). An invalid plugin.json must fail with a clear error and no traceback. Built-in domains must behave exactly as before. Choose the design (discovery, validation, registration, precedence against built-in names) yourself, and add tests.'

ML='This repo trains a tiny decoder-only transformer written from scratch in numpy (model.py, with hand-written backpropagation). The gradient check (`python gradcheck.py`) fails for several parameters, and a reviewer suspects there may be other correctness problems in the model beyond the gradients. Find and fix every bug so that model.py is a correct causal transformer with exact gradients. Do not change the architecture, the task or the training setup; keep the fixes minimal, and explain each bug you fixed.'
REFACTOR='scripts/core.py (about 1,050 lines) has grown too large. Split it into a package of focused modules (for example: normalization/tokenization, BM25 ranking, CSV loading and caching, domain search, stack search), each under 400 lines, and keep scripts/core.py as a thin backward-compatible facade of at most 150 lines, so every existing import keeps working: public names and the private names used by the tests and other scripts, including the module-level caches. Behaviour and CLI output must stay byte-for-byte identical, the existing tests must not be modified, and the test suite must stay at its baseline.'
CACHE='Implement SingleFlightCache in sfcache.py exactly as specified in README.md (stdlib only), with thorough tests, including concurrency tests.'

case "$ARM" in
  opus)   M=(--model opus);   A='Do not use the god-mode skill or any other skill; work as you normally would.' ;;
  sonnet) M=(--model sonnet); A='Do not use the god-mode skill or any other skill; work as you normally would.' ;;
  triad)        M=(--model sonnet); A='Use the god-mode skill with this team policy (you are the Sonnet session): (1) First send the whole request to the `planner` agent (Opus); it returns a requirements checklist, exact steps and pitfalls; save the checklist to .godmode/REQUEST.md. (2) Hand ALL implementation to the `executor-light` agent (Haiku), one brief per cohesive group of steps, each brief containing the step text, the relevant facts from the plan, the pitfalls and the acceptance command. You do not write the production code yourself. (3) You verify: run the tests, check every checklist item against the code, then send the `reviewer` agent the request, the checklist and the base commit for an independent check. Send gaps back to the executor. (4) A step that still fails after two attempts goes to the `solver` agent (Opus).' ;;
  router) M=(--model sonnet); A='Use the god-mode skill.' ;;
  lite)   M=(--model sonnet); A='Use the god-mode-lite skill.'; mkdir -p "$DIR/.claude/skills"; cp -r "$OUT/../real/variant/god-mode-lite" "$DIR/.claude/skills/"; cp -r <HOME>/.claude/skills/god-mode/scripts "$DIR/.claude/skills/god-mode-lite/scripts" ;;
  haikugm) M=(--model haiku); A='Use the god-mode skill.' ;;
  haiku) M=(--model haiku); A='Do not use the god-mode skill or any other skill; work as you normally would.' ;;
esac
case "$TASK" in ml) BODY="$ML" ;; refactor) BODY="$REFACTOR" ;; cache) BODY="$CACHE" ;; ladder) BODY="$LADDER" ;; plugin) BODY="$PLUGIN" ;; esac
S=$(date +%s)
( cd "$DIR" && timeout 3600 claude -p "$BODY

$A

The plan is pre-approved: proceed without waiting for approval and finish the whole task." "${M[@]}" \
    --output-format stream-json --verbose --allowedTools Read Write Edit Glob Grep Skill Agent TodoWrite Bash \
    --disallowedTools "Bash(pip *)" "Bash(python -m pip*)" > "$OUT/$TASK-$ARM.jsonl" 2>&1 )
echo "$TASK-$ARM done in $(( $(date +%s) - S ))s"
