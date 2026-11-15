# 41-File Event Bus Refactoring Benchmark (Opus 5.5)

**Date:** November 12, 2026  
**Harness:** Headless `claude -p --output-format json` using Claude Code 2.1.296  
**Model:** `claude-opus-5-5` (with `claude-sonnet-5-5` subagents)  
**Target Codebase:** 41 Python files across 5 architectural layers (`src/core`, `src/models`, `src/schemas`, `src/services`, `src/api/v1`), 23 unit tests.  
**Task:** Decouple all direct cross-service calls between billing, subscription, webhook, and audit services by introducing an in-process Event Bus (`src/core/events.py`).  
**Verification:** Restored original 23 unit tests (`hidden_tests/`) + structural import checks (`check.sh`).

---

## 1. Measured Results

| Run | Total Cost (USD) | Tokens (all models) | Trajectory Turns | Duration | Subagent Share | Correctness (Tests & Checks) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Plain Opus #1** | $0.765 | 607,778 | 23 | 137s | — | 23/23 tests pass, all imports decoupled |
| **Plain Opus #2** | $0.598 | 592,996 | 15 | 115s | — | 23/23 tests pass, all imports decoupled |
| **God Mode (Auto) #1** | $0.625 | 550,999 | 9 | 79s | None | 23/23 tests pass, all imports decoupled |
| **God Mode (Auto) #2** | **$0.592** | **407,506** | **7** | **80s** | None | 23/23 tests pass, all imports decoupled |
| **God Mode (Full) #1** | $1.041 | 1,196,881 | 30 | 183s | Sonnet: $0.051 | 23/23 tests pass, all imports decoupled |
| **God Mode (Full) #2** | $0.883 | 1,139,626 | 21 | 150s | Sonnet: $0.055 | 23/23 tests pass, all imports decoupled |

---

## 2. Statistical Averages & Impact

| Metric | Plain Opus (Baseline) | God Mode (Auto Triage) | God Mode (Forced Full) | Impact (Auto vs Plain) |
|---|:---:|:---:|:---:|:---:|
| **Average Cost** | $0.682 | **$0.609** | $0.962 | **~11% lower cost** |
| **Average Tokens** | 600,387 | **479,252** | 1,168,253 | **~20% fewer tokens** |
| **Average Turns** | 19 turns | **8 turns** | 25.5 turns | **~58% fewer turns (7–9 vs 15–23)** |
| **Average Duration**| 126s | **80s** | 167s | **37% faster wall-clock completion** |
| **Correctness** | 100% (2/2) | 100% (2/2) | 100% (2/2) | Flawless execution across all runs |

---

## 3. Key Engineering Findings

### A. The Core Win: Speed & Turn Efficiency in Auto Mode
God Mode in Auto Triage mode completed the entire cross-service refactor in **7 to 9 turns** (taking **79–80 seconds**), compared to **15 to 23 turns** (taking **115–137 seconds**) for Plain Opus.
- The structured AST awareness and triage prompt focused Opus immediately on the decoupling requirements without circular wandering.
- Cost was slightly lower or comparable ($0.609 vs $0.682 average).

### B. The Coordination Tax of Forced Subagents at ~1,100 LOC
Forcing the full subagent pipeline (`God Mode Full`) cost **~41% more** ($0.962 vs $0.682) and took **~33% longer**.
- Even though the Sonnet executor subagent was cheap (costing only ~$0.05), Opus spent significant token volume on planning, writing exhaustive executor briefs, and verifying the subagent output.
- **Architectural Lesson:** On codebases around ~1,100 LOC, subagent serialization overhead outweighs execution savings. Auto Triage correctly avoided delegating for this reason. Multi-agent delegation becomes cost-positive on larger codebases (multi-thousand LOC) with extensive test outputs.

---

## 4. Reproducibility Files

- `TASK.txt`: Exact user prompt passed to `claude -p`.
- `check.sh`: Automated test verification script (runs unmodified original tests against the output).
- `hidden_tests/`: Clean copy of the original 23 unit tests.
- `plain1.json`, `plain2.json`: Raw Claude Code execution logs for Plain Opus.
- `gm1.json`, `gm2.json`: Raw execution logs for God Mode Auto Triage.
- `full1.json`, `full2.json`: Raw execution logs for God Mode Forced Full.
- `RESULTS.md`: Original benchmark log table.

