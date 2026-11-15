# Legacy benchmark: read this first

This is the benchmark the first version of the README was built on. The raw numbers reproduce from the JSON logs in the subfolders (turns, time, cost, tokens), and the code and checks are unchanged.

What it does and does not show:

- **41-file Event Bus refactor:** 2 runs per arm, one task, Claude Opus 5.5 only. God-mode (auto) used 7 to 9 turns against 15 to 23 for plain Opus, and 79 to 80 s against 115 to 137 s. Cost was $0.592 to $0.625 against $0.598 to $0.765: **the ranges overlap, so no cost saving is established**.
- The turn reduction was credited to the code graph. **No test isolated the graph**, so that attribution is unproven.
- No Sonnet baseline was run. Later tests found the Sonnet default, not the skill, accounts for most of the saving.
- **Small task (5 files):** plain Opus was cheaper and faster. This one stands as published.

Current findings and caveats are in `../README.md`.
