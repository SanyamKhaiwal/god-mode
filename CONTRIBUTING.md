# Contributing to God Mode

Thank you for contributing. The most valuable contributions to God Mode are **real comparison benchmarks** and **test edge cases**: runs that show where the pipeline saves tokens, catches mistakes, or where a subagent brief was ambiguous.

---

## Ways to Contribute

| Contribution | How |
|---|---|
| **Share a Comparison Run** | Run the same multi-file coding task in Claude Code with and without God Mode. Report token usage, cost difference, and whether any bugs were caught before or after building |
| **Report an Edge Case** | If an acceptance command had unusual output that bypassed `filter-output.sh` or caused a hook failure, open an issue with the command and trimmed log |
| **Improve Prompts** | Subagent prompt tweaks in `agents/` that improve compliance without inflating prompt token costs |
| **CI / Test Additions** | Add tests to `scripts/selftest.sh` covering quirks across platforms |

---

## Development & Testing

Before submitting a Pull Request, verify that all 22 unit tests pass:

```bash
bash scripts/selftest.sh
```

All 22 tests must output `PASS`.

---

## Guidelines
1. Keep `SKILL.md` and reference docs dense, concrete, and factual. Avoid vague narrative instructions.
2. Ensure subagent prompts in `agents/` require structured, low-token responses (`Changed`, `Files touched`, `Acceptance`, `Decisions`).
3. Maintain shell compatibility: scripts in `scripts/` must run in bash on Linux, macOS, and Git Bash on Windows.

