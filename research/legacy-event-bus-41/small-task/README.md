# Small-Task Empirical Evaluation (5-File Python Project)

**Date:** November 12, 2026  
**Harness:** Headless `claude -p` using Claude Code CLI  
**Model:** `claude-opus-5-5` (with `claude-sonnet-5-5` subagents)  
**Evaluation Scope:** 5-file Python shop package (`models.py`, `pricing.py`, `discounts.py`, `tax.py`, `invoice.py`, `tests/test_invoice.py`).  
**Verification:** 5 hidden unit tests (`hidden_test.py`) unexposed during execution.

---

## 1. Executive Summary & Core Finding

> **Key Takeaway:** On small tasks (1–5 files), **Plain Opus is cheaper and faster** than God Mode. Prompt caching allows monolithic Opus to complete small tasks in ~3 turns for ~$0.23. The orchestration overhead of evaluating triage rules and skill guidance adds 3–4 extra Opus turns, costing ~$0.42–$0.44. **God Mode is designed for large, multi-file refactoring and long sessions, not small edits.**

---

## 2. Benchmark Results

| Run | Total Cost (USD) | Total Tokens | Duration | Subagents Spawned | Hidden Tests Passed |
|---|:---:|:---:|:---:|:---:|:---:|
| **Plain Opus #1** | $0.506* | 149,900 | 36s | None | 5/5 Pass |
| **Plain Opus #2** | **$0.230** | 148,225 | 37s | None | 5/5 Pass |
| **Plain Opus #3** | **$0.235** | 150,240 | 38s | None | 5/5 Pass |
| **God Mode (Auto) #1** | $0.441 | 357,897 | 45s | None *(Triage selected Light; executed directly)* | 5/5 Pass |
| **God Mode (Auto) #2** | $0.417 | 291,474 | 46s | None *(Triage selected Light; executed directly)* | 5/5 Pass |
| **God Mode (Full) #1** | $0.566 | 515,572 | 83s | `reviewer` on Sonnet ($0.036) | 5/5 Pass |
| **God Mode (Full) #2** | $0.553 | 452,374 | 74s | `reviewer` on Sonnet ($0.047) | 5/5 Pass |

*\*Run #1 incurred a one-time ephemeral prompt-cache creation cost. Runs #2 and #3 represent steady-state warm prompt-cache performance.*

---

## 3. Detailed Architectural Observations

### A. The Cost of Orchestration on Small Codebases
In `plain2.json` and `plain3.json`, plain Opus required only **3 turns** to inspect the files, write the code, and run unittest. Thanks to prompt caching, each turn cost only ~$0.06 in cache reads.

In `godmode.json` (`auto`), God Mode required **7 turns**. Even though the model correctly triaged the task as small and avoided spawning subagents, reading the skill instructions, evaluating complexity tiers, and recording triage thoughts cost an extra 4 turns of Opus thinking (~$0.19 in cached reads).

### B. Subagent Triage Rationality
In both `godmode.json` and `full2.json`, Opus demonstrated proper triage behavior:
> *"I did the steps in this session instead of handing them to executor subagents, because the instructions for each would have been as long as the edit itself."*

The prompt successfully prevented wasteful over-delegation on small tasks.

### C. Quality Assurance in Action (Reviewer Subagent)
In `full1.json`, the forced pipeline included an independent diff review by a Sonnet subagent. Opus noted in its final handoff:
> *"The reviewer flagged that my first version of this test didn't really test the cap, and I fixed it."*

While all runs passed the hidden tests, the reviewer subagent actively caught a test quality gap that plain Opus missed.

---

## 4. Raw Reproducibility Files

All raw run artifacts, logs, and outputs from Claude Code CLI are preserved in this directory:
- `TASK.txt`: Exact user prompt passed to `claude -p`.
- `hidden_test.py`: The 5 unexposed verification tests.
- `plain.json`, `plain2.json`, `plain3.json`: Raw Claude Code execution logs for Plain Opus.
- `godmode.json`, `gm2.json`: Raw execution logs for God Mode Auto Triage.
- `full1.json`, `full2.json`: Raw execution logs for God Mode Full Pipeline.

