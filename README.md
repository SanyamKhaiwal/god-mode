# god-mode

### Your Claude Code bill, explained. Control the part you can. Skip the part you can't.

[![CI](https://github.com/SanyamKhaiwal/god-mode/actions/workflows/ci.yml/badge.svg)](https://github.com/SanyamKhaiwal/god-mode/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

We measured where the tokens go, tested what actually saves money, and built the parts that held up. No hype: every number links to the experiment behind it, and the failures are published too.

```bash
git clone https://github.com/SanyamKhaiwal/god-mode.git && cd god-mode && python install.py
```

One command. No network, no `pip install`. Needs Python 3 and bash. [`--dry-run` to preview, `--uninstall` to remove.](INSTALL.md)

**Recommended, and the installer asks:** in a terminal it offers to put a 4-line block in your `~/.claude/CLAUDE.md` (default yes), so Claude picks the skill for multi-step work without being told. The hooks run without it, but the skill, the `quick` / `full` overrides and four of the guides need it. `--claude-md` adds it without asking, `--no-claude-md` skips the question, scripted installs never edit the file unasked, and `--uninstall` removes only that block.

---

## The surprise

We gave the same six real GitHub issues (scored with the maintainers' own hidden tests) to three models.

```
              passed   cost for all six
Haiku          6 / 6   $0.10  ▏
Sonnet         6 / 6   $1.08  █████
Opus           6 / 6   $2.16  ██████████
```

**Same results, 10 to 20 times the price.** On well-specified tasks the cheaper model was enough. Most of what you can save is just *choosing the model*, and god-mode makes that choice easy.

## Where your tokens actually go

```
Cache writes  ██████████████████████████  ~49%   new context: files, tool output, skills
Output        ███████████████             ~28%   what the model writes
Cache reads   ████████████                ~23%   re-reading the conversation every turn
```

| You control it | You don't |
|---|---|
| Which **model** runs (the biggest lever) | Prompt caching (it's why re-reading is ~10x cheaper) |
| How **long** a session gets | Anthropic's prices |
| How much **junk** enters context | How hard the model thinks |

god-mode works on the left column only.

---

## What you get

| | |
|---|---|
| **A nudge to the right model** | "This looks Haiku-sized" or "this one deserves Opus", only when the signal is clear. You decide; nothing switches itself. |
| **Shorter test logs** | A 315-line failing test run comes back as 51 lines, failures kept, exit code intact. Automatic, no setup. |
| **Say "continue" and pick up where you left off** | Your request becomes a checklist; every prompt you send is logged by a hook. Open a new session, type `continue`. |
| **No "done" without proof** | If code changed after the last test run, or checklist items are still open, the finish is held back once. |
| **Five Superpowers guides, picked for you** | Test-first on bug fixes, brainstorming on design requests, systematic debugging when a fix fails. No slash commands. |

### See it work

**The filter** (abridged; a real 315-line run was trimmed to 51 lines, shown here shortened further):
```
$ python -m pytest -q
[filter-output] 315 lines, exit 1. Showing error/failure lines, then the last 40 lines.
----- matches -----
...assert 1 == 2
----- failure locations -----
...
[exit code: 1]
```

**The session log** (`.godmode/SESSION.md`, written by a hook, zero model tokens):
```
## 2026-11-15 20:15 USER
Create a file hello.txt containing the word hi, then tell me you did it.

### 20:16 ASSISTANT
I created hello.txt in the project root, containing the word hi.
Edited: hello.txt
```

**Resume** (a new session in the same folder; illustrative layout, the real output prints your own checklist):
```
> continue
=== GOD MODE: unfinished requirements in .godmode/REQUEST.md ===
- [x] 1. --explain adds score and matched_terms
- [ ] 2. Scores shown with 3 decimals        <- picks up here
```

---

## Honest by design

**We tested whether a stronger model rescues a stuck task, whether an Opus planner helps a cheap worker, and whether Claude's built-in `/advisor` pays off. In our runs: no evidence it does** (5 to 14 times the cost, same score). So the tooling stays small, and the README says so.

- god-mode itself did **not** beat plain Sonnet on cost or pass rate ($1.09 vs $1.08). The saving is the model choice.
- Mostly **one run per cell**. Small samples are noisy and we say so.
- **We never found where Haiku or Sonnet break.** Every task we could score, every model solved. Six harder real tasks failed for all models because their tests check details the issue never states.
- Hooks match the *words* of your prompt, not your intent.

<details>
<summary><b>The full token map: what's in your hands, what isn't, and what we tried</b></summary>

Fitted from our own run logs on Sonnet and Opus sessions. Shares are of the bill by billing category. Opus costs about 1.7 to 2.2x Sonnet per token; Haiku runs cost about 7 to 13% of a Sonnet run.

| Bucket | Share | In your hands? | What controls it | What we did | What we found |
|---|:---:|:---:|---|---|---|
| **Model choice** | x all | **Yes, biggest** | `/model`, `settings.json` default | Sonnet default; hints for Haiku/Opus | Tiers tied on every scorable task; Haiku $0.10, Sonnet $1.08, Opus $2.16 for six tasks |
| **Cache writes** | ~48-49% | **Partly** | What you let into context | Test-output filter | 315 lines to 51 (about -83%); effect on the total bill not measured |
| **Cache reads** | ~21-24% | **Partly** | Session length | Checklist + session log so a short fresh session can resume | Memory-off resume test: 13/13 with files vs 8/13 without; saving from restarting not measured |
| **Output** | ~27-29% | **Barely** | The model and the task | Finish gate and failure ladder, aimed at fewer wasted retries | Effect on cost unmeasured; ladder never fired on a real stuck task |
| **Fixed startup** | ~1.3k tokens | Yes, small | How many skills/MCP servers load | Skill text loads only when triggered | Under a cent per session |
| **Prompt caching** | | **No** | Anthropic | Nothing: it can't be edited mid-session | |

A spawned agent costs about 19k cache-write tokens (roughly $0.15 on Opus) before it does any work. See [`research/COST-MODEL.md`](research/COST-MODEL.md).

</details>

<details>
<summary><b>What we measured (with caveats)</b></summary>

| Question | Result | Caveat |
|---|---|---|
| Does a cheaper model match Opus? | Yes on every scorable task | The scorable tasks are the ones every tier solved |
| Sonnet-default vs Opus-default | God-mode on Sonnet cost 31-40% less (9 tasks: $3.05 vs $5.10; 6 tasks: $2.80 vs $4.05) | Sets overlap, one run per cell, Opus at high effort vs Sonnet medium |
| Does god-mode beat plain Sonnet? | No: $1.09 vs $1.08, same 6/6 | The saving is the model choice |
| Does the checklist help across sessions? | Yes with built-in memory off: 13/13 vs 8/13 (3 runs each) | With built-in memory on, plain Claude Code also scored 13/13. One task |
| Does a stronger planner or `/advisor` help? | No evidence | 2-6 runs, on tasks no tier solved |
| Where do the models break? | **Not found** | See above |

Scripts, score files and the full write-up: [`research/`](research/README.md).

</details>

<details>
<summary><b>The nine bundled Superpowers guides: which are picked automatically</b></summary>

The nine guides from [Superpowers](https://github.com/obra/superpowers) (MIT, Jesse Vincent) are **bundled and integrated**: no separate install, no slash command. When your prompt or test output matches a situation, a hook points the model at the right guide.

| Guide | When it is picked | Automatic? |
|---|---|:---:|
| **test-driven-development** | A bug-fix prompt with a code signal (a file, identifier or error type) | Yes, by hook |
| **brainstorming** | An open design: architecture, a plugin system, "design a module" | Yes, by hook |
| **systematic-debugging** | A fix attempt didn't reduce the failing tests | Yes, by hook |
| **verification-before-completion** | The model is about to say "done" after editing code | Yes, by hook |
| **receiving-code-review** | The review agent just returned findings | Yes, by hook |
| requesting-code-review, dispatching-parallel-agents, using-git-worktrees, finishing-a-development-branch | Written into the skill as rules | No: may be ignored |

Five of nine fire on their own; a bug described with no file or error name won't trigger the TDD note. In a normal run the model reads our shorter `QUICK.md` summary of each guide (the full originals, Superpowers 6.2.0, are bundled too). We did not measure whether the guides improve results.

</details>

<details>
<summary><b>Everything else in the box</b></summary>

| Piece | What it is | Status |
|---|---|---|
| **`quick` / `full` overrides** | `quick` keeps a task in the plain Direct route; `full` runs the multi-step Full route | Works as written; no hook enforces it |
| **Full route** | Research, plan, execute, handoff, review, with `.godmode/PLAN.md` and `HANDOFF.md` (templates in `assets/`) | Built and unit-tested; no benchmark showed it beating plain Sonnet |
| **Optional agents** | `planner`, `solver` (Opus); `executor`, `researcher-deep` (Sonnet); `executor-light`, `researcher` (Haiku); `reviewer` (Sonnet). Skip with `--no-agents` | **No measured benefit**; the model rarely delegated to them |
| **Test-run wrapper** (`godmode-run.sh`) | Runs a command through the filter, logs PASS/FAIL to `.godmode/test-log.md`, prints the next failure-ladder step | Works; the model has to choose to use it |
| **Code-graph tool** | Dependency and symbol index (Python, Java, C/C++, JS/TS), built on first use in 1-2 s; `where`, `importers`, `refs`, `outline` | Works and is tested; **not shown to beat grep**; nothing triggers it automatically |
| **Project state at start** | If `CLAUDE.md` has a `Project record:` line, its marked block is printed at session start | Works; optional |
| **Self-test** | 62 checks on scripts and hooks, run by CI on Linux and macOS | Passing |

</details>

<details>
<summary><b>Safety, privacy and turning things off</b></summary>

- **The test-output filter rewrites test commands but never approves anything.** Your normal permission rules apply to the rewritten command. If you allow only narrow patterns such as `Bash(pytest*)`, it will ask for approval.
- **The session log records every prompt you type**, including anything you paste, in `.godmode/SESSION.md`. Add `.godmode/` to `.gitignore` and don't paste secrets. It only runs in folders that already have a `.godmode/` folder.

| To disable | Do this |
|---|---|
| Test-output filter | `GODMODE_NO_FILTER=1`, or remove its `PreToolUse` entry |
| Session log | `GODMODE_NO_SESSION_LOG=1`, or remove its two entries |
| Model advisor | Remove its two `settings.json` entries (no environment switch) |
| The `CLAUDE.md` block (if you added it) | `python install.py --uninstall` removes only that block |
| Everything | `python install.py --uninstall` (your own hooks stay) |

</details>

---

## The research gap: help us find where the models break

Everyone says one model is "better at coding". Coding is huge, and that sentence says little. We know of no published map of where each model actually breaks.

- **Where do Haiku and Sonnet fail?** We haven't found it.
- **Which kinds of coding are hard for which models?** Our guess: web work is easy; backend and security work (vulnerability finding, pen-testing) harder; signal-processing or RF code harder still. **Untested.**
- **Does a stronger model rescue a stuck task?** The escalation path exists but has never fired live.
- **How much does restarting a long session really save?** Cache reads are about a fifth of the bill; the saving is unmeasured.

**Next:** a breaking-point map by domain (web, backend, systems, numerics, security, RF) with several runs per cell; tasks where one tier passes and another fails; matched-effort repeated runs; a restart-vs-continue cost measurement.

> **Found a task where the cheap model fails and the expensive one wins? Open an issue.** That is the result we're looking for.

---

## In this repo

`claude/` is exactly what gets installed into `~/.claude` (the skill, four hooks, optional agents) · `install.py` and `tests/` · `research/` (findings, cost model, scripts, score files; `legacy-event-bus-41/` is the earlier benchmark, relabelled with what it does and doesn't show) · CI installs the project and runs every test on Linux and macOS.

MIT licensed. Bundled Superpowers guides: MIT, credited to Jesse Vincent.
