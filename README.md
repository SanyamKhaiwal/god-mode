# god-mode

**Where Claude Code's tokens go, which part of that you can actually control, and what we measured when we tried.**

A research project with working tooling for Claude Code. Short version: on well-specified coding tasks, **Sonnet and even Haiku matched Opus at a fraction of the price**, and most of the saving comes from choosing the model. This repo adds guard rails around that (requirements checklist, "not done until tests ran", shorter test logs, a session log) and publishes every experiment, including the ones that found nothing.

---

## 1. Where the tokens go

Fitted from our own run logs on Sonnet and Opus sessions. Shares are of the bill, by billing category.

| Bucket | Share of the bill | What it is |
|---|:---:|---|
| **Cache writes** | ~48-49% | Everything new that enters context: your prompt, files read, tool output, skill text, agent briefs |
| **Output** | ~27-29% | What the model writes: code, edits, explanations |
| **Cache reads** | ~21-24% | Re-reading the whole conversation on every turn (cheap per token, many turns) |
| **Fixed startup** | ~1.3k tokens | Skill and tool descriptions loaded each session (~7.5k with every skill and MCP server) |

All of it is multiplied by the **model price**: Opus costs about 1.7-2.2x Sonnet per token, and Haiku runs cost about 7-13% of a Sonnet run.

## 2. How much of that is in your hands

| Bucket | In your hands? | What controls it | What we did | What we found |
|---|:---:|---|---|---|
| **Model choice** | **Yes, the biggest lever** | `/model`, the default in `settings.json` | Sonnet default; hooks hint when a task looks Haiku-sized or Opus-sized (you decide, nothing switches itself) | Haiku, Sonnet and Opus tied on every task we could score. For the six solvable real tasks: Haiku $0.10, Sonnet $1.08, Opus $2.16 |
| **Cache writes** (tool output, files read) | **Partly** | What you let into context | A filter that trims long test output to failures and the tail | A 315-line failing run came back as 51 lines (about -83%). Effect on the total bill: not measured |
| **Cache reads** (re-reading the conversation) | **Partly** | Session length | Requirements checklist + hook-written session log, so a short fresh session can pick up where you left off | Memory-off resume test: 13/13 with the files vs 8/13 without. Saving from restarting: not measured |
| **Output** (the model's own work) | **Barely** | Mostly the model and the task | A "tests ran after the last edit" gate and a failure ladder, aimed at fewer wasted retries | Gate works as designed; its effect on cost is unmeasured. Ladder never fired on a real stuck task |
| **Fixed startup** | Yes, but small | How many skills/MCP servers you load | Skill text loads only when triggered | About 1.3k tokens, under a cent per session |
| **Prompt caching itself** | **No** | Anthropic | Nothing. It cannot be edited mid-session, and you wouldn't want to: it is what makes re-reading ~10x cheaper | n/a |
| **Token prices, how the model reasons, tokenisation** | **No** | Anthropic | Nothing | n/a |

**In short:** you control which model runs, how long a session gets, and how much junk enters context. You do not control caching, prices or how hard the model thinks. Our work targets the first group.

## 3. What a spawned agent costs

A spawn costs about 19k cache-write tokens (roughly $0.15 on Opus) before it does any work. In our runs an Opus planner, an Opus-plans/Haiku-builds setup, and the built-in `/advisor` cost **5-14x** a single session and scored no higher on any task we could grade. Agents may still pay off when work is large and independent or would flood the main context; they did not for the tasks we tested.

## 4. What we built, per lever

| Lever | Feature | How it works |
|---|---|---|
| Model choice | **Model advisor** | A hook reads your prompt and, when the signals are clear, prints a hint: Haiku for a clear single change, Opus for concurrency/security/architecture-type work. Never switches anything |
| Cache writes | **Test-output filter** | Plain test commands (`pytest`, `npm test`, `go test`...) run through a filter that keeps failures, failure locations and the tail, and preserves the exit code. It never approves a command |
| Cache reads | **Requirements ledger** | `.godmode/REQUEST.md`: your request verbatim plus a numbered checklist, ticked as work finishes |
| Cache reads | **Session log** | A hook writes every prompt you send, verbatim, and a one-line digest of each turn to `.godmode/SESSION.md`. No model tokens |
| Cache reads | **Resume** | At session start, if a task is open, the checklist and the log tail are printed, so "continue" works in a fresh session |
| Output | **Finish gate** | A hook blocks "done" once if code changed after the last test run, or if checklist items are still open. A nudge, not a lock |
| Output | **Failure ladder** | After repeated failing fixes: systematic debugging, then a stronger agent, then ask you |

Guidance from five bundled Superpowers-style guides (TDD, brainstorming, debugging, verification, review handling) is added by hooks when your words or test output match, so there are no slash commands to remember. Four more guides are written rules only and may be ignored.

## 5. What we measured (small samples: read the caveats)

We scored runs with hidden tests: real merged GitHub pull requests (the maintainers' own tests) and harder tasks we wrote, in Python, Java and C++. Details and scripts: [`research/`](research/README.md).

| Question | Result | Caveat |
|---|---|---|
| Does a cheaper model match Opus? | Yes on every scorable task | The tasks we could score are the ones every tier solved |
| Sonnet-default vs Opus-default | God-mode on Sonnet cost 31-40% less (9 tasks: $3.05 vs $5.10; 6 tasks: $2.80 vs $4.05) | Sets overlap, one run per cell, Opus ran at high effort vs Sonnet medium |
| Does god-mode beat plain Sonnet? | No: $1.09 vs $1.08, same 6/6 | The saving comes from the model choice |
| Does the checklist help across sessions? | Yes with built-in memory off: 13/13 vs 8/13 (3 runs each) | With built-in memory on, plain Claude Code also scored 13/13. One task |
| Does a stronger planner or `/advisor` help? | No evidence | 2-6 runs, on tasks no tier solved |
| Where do the models break? | **Not found** | Six hard real tasks failed for every model because their tests check details the issue never states |

## 6. Things to know before installing

- **The test-output filter rewrites test commands.** It never approves anything: your normal permission rules apply to the rewritten command. If you allow only narrow patterns such as `Bash(pytest*)`, the rewritten command will ask for approval. `GODMODE_NO_FILTER=1` turns it off.
- **The session log records every prompt you type**, including anything you paste, in `.godmode/SESSION.md`. Add `.godmode/` to `.gitignore` and don't paste secrets. `GODMODE_NO_SESSION_LOG=1` turns it off. It only runs in folders that already have a `.godmode/` folder.
- Needs `bash` (Git Bash on Windows) and Python 3 on your PATH. No network, no `pip install`.

**Install:**

```bash
git clone https://github.com/SanyamKhaiwal/god-mode.git
cd god-mode
python install.py          # --dry-run to preview, --uninstall to remove
```

See [INSTALL.md](INSTALL.md).

## 7. The research gap (where we'd love help)

Everyone says one model is "better at coding". Coding is huge, and that sentence says little. We know of no published map of where each model actually breaks.

- **Where do Haiku and Sonnet fail?** Every task we could score was solved by every tier.
- **Which kinds of coding are hard for which models?** Our guess: web work is easy; backend and security work (vulnerability finding, pen-testing) harder; signal-processing or RF code harder still. Untested.
- **Does a stronger model rescue a stuck task?** The escalation path exists but has never fired live.
- **How much does restarting a long session really save?** Cache reads are about a fifth of the bill; the saving from a clean restart is unmeasured.

## 8. What's next

1. A **breaking-point map** by domain (web, backend, systems, numerics, security, RF), several runs per cell, with cost.
2. **Tasks where one tier passes and another fails**, so escalation can be proven or dropped.
3. **Matched-effort, repeated runs** of the Sonnet-vs-Opus comparison, with variance.
4. A measured **restart-vs-continue** cost comparison on real sessions.

## What's in this repo

- `claude/`: exactly what gets installed into `~/.claude` (the skill, four hooks, optional agents). Nine bundled Superpowers guides are MIT-licensed, credited to Jesse Vincent.
- `install.py`, `tests/`: the installer and its tests. Hook tests live in `claude/hubs/`.
- `research/`: findings, cost model, scripts and score files. `research/legacy-event-bus-41/` is the earlier benchmark, relabelled with what it does and doesn't show.
- CI installs the project and runs every test on Linux and macOS.

## Honest status

Single runs are noisy and we say so. If you find a task where the cheap model fails and the expensive one wins, open an issue. That is the result we're looking for.
