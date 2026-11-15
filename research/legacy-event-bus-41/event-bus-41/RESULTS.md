# God Mode vs plain Opus — 41-file Event Bus refactor (2026-11-12)

Claude Code 2.1.296, model opus (claude-opus-5-5), headless `claude -p --output-format json`.
Cost/tokens = Claude Code's own total_cost_usd / modelUsage. Correctness = check.sh
(original 23 tests restored unmodified + structural checks). Task: TASK.txt.

| Run | Cost | Tokens | Turns | Time | Sonnet share | Correct |
|---|---|---|---|---|---|---|
| Plain Opus #1 | $0.765 | 607,778 | 23 | 137s | – | yes |
| Plain Opus #2 | $0.598 | 592,996 | 15 | 115s | – | yes |
| God-mode auto #1 | $0.625 | 550,999 | 9 | 79s | – | yes |
| God-mode auto #2 | $0.592 | 407,506 | 7 | 80s | – | yes |
| God-mode full #1 | $1.041 | 1,196,881 | 30 | 183s | $0.051 | yes |
| God-mode full #2 | $0.883 | 1,139,626 | 21 | 150s | $0.055 | yes |

Averages: plain $0.682 / 600k tok / 126s; auto $0.609 / 479k tok / 80s; full $0.962 / 1.17M tok / 167s.
