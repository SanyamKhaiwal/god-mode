# Research notes

Everything here is the evidence behind the numbers in the main README. All runs were headless `claude -p` on Claude Code 2.1.296 in November 2026, scored by hidden tests. Costs are Claude Code's own `total_cost_usd`. **Samples are small (mostly one run per cell); read every number with that in mind.**

The scripts are the exact ones we ran. They contain `<HOME>` and `<WORKDIR>` placeholders where our machine's paths were; set them before running. Raw `.jsonl` run logs are not included (they are large); the score files and summaries are.

## Findings

| Question | Result | Where |
|---|---|---|
| Do cheaper models match Opus on well-specified tasks? | Yes on every task we could score. Haiku, Sonnet and Opus passed the same 6 real-issue tasks. Cost for the six: Haiku $0.10, Sonnet $1.08, Opus $2.16. | `real-issues/results/` |
| Which real tasks could nobody solve? | 6 click tasks failed for every tier. The hidden tests assert internals the issue never states (for example a private name `_click_default_help`). They show a ceiling on spec-from-issue tasks, not a model difference. | `real-issues/results/` |
| Does adding the maintainers' PR description help? | Partly: partial scores rose (for example 0/10 to 5/10 on one task) but no task flipped to a pass, and tiers still tied. | `real-issues/results/*-h.score.json` |
| Does an Opus plan help a Haiku worker? | No evidence. About 12x the cost of Haiku alone, no better score (6 tasks nobody solved). | `real-issues/results/*plan-haiku*` |
| Does the built-in `/advisor` help? | No evidence. Haiku with an Opus advisor cost 7 to 14x Haiku alone with the same score (2 runs, then stopped). | not archived |
| Does god-mode beat plain Sonnet on cost or pass rate? | No. $1.09 vs $1.08 on the six solvable real tasks; same 6/6. A leaner 324-word variant was not cheaper ($1.14). | `real-issues/results/` |
| Sonnet-default vs Opus-default on our own tasks | God-mode on Sonnet cost 31 to 40% less than Opus (9 tasks: $3.05 vs $5.10; 6 tasks: $2.80 vs $4.05). The sets overlap, each cell is one run, and Opus ran at high effort vs Sonnet at medium, so part of the gap is effort. | `hard-tasks/`, `legacy-event-bus-41/` |
| Do hard tasks separate the tiers? | Not in our set. All three arms passed 4 of 5 hard tasks fully; on the refactor task the scores were 9/9 (god-mode), 8/9 (Sonnet), 7/9 (lean variant), within single-run noise. | `hard-tasks/` |
| Does a written requirements file help across sessions? | Yes, when Claude Code's built-in memory is off. Nothing carried over: 8 of 13 checks (3 runs). Ledger file, hook-written log, or log plus a reply state block: 13 of 13 (3 runs each). With built-in memory on, plain Claude Code also scored 13 of 13. One task, one artificial interruption. | `resume-test/results/` |

## What is not established

- Where Haiku or Sonnet actually break. Every scorable task was solved by every tier.
- Whether escalating to a stronger model rescues a stuck task. The ladder is built and unit-tested but never fired on a real stuck task.
- Whether the codebase graph beats plain grep (we measured no benefit), or how much the test-output filter changes total cost.
- Anything about domains we did not test: security work, signal processing, low-level code.

## Folders

- `real-issues/`: builds tasks from merged GitHub pull requests (base = the parent of the merge commit, hidden tests = the maintainers' tests) and scores runs. We do not ship the third-party code or tests; `build_tasks.py` rebuilds them.
- `hard-tasks/`: our own harder tasks (ML gradient bugs, a file split, a concurrent cache, a plugin design, a two-cause bug), their hidden checks and the runner.
- `resume-test/`: the memory-off resume experiment: task, a mid-session spec change, a fresh session fed only files.
- `legacy-event-bus-41/`: the earlier benchmark that the first README was built on. The numbers reproduce from its raw logs (two runs per arm, Opus only, one task). See its README.

See `COST-MODEL.md` for where tokens go.
