# god-mode

**A field report and toolkit on cutting Claude Code cost: what we tried, what held up, and what is still unknown.**

The short version: on well-specified coding tasks, **Sonnet and even Haiku matched Opus at a fraction of the price**. You can get most of that saving with `/model sonnet` and no extra tooling. This repo adds a few guard rails around that (a requirements checklist, a "no done without tests" gate, shorter test logs, a session log) and records every experiment, including the ones that found nothing.

---

## What it does, in plain words

You use Claude Code the way you always do. Hooks run in the background and do five jobs:

| Job | What you get |
|---|---|
| **Cheap by default** | Sessions start on Sonnet. A hint appears when a task looks simple enough for Haiku, or hard enough to deserve a stronger model. You decide; nothing switches on its own. |
| **Doesn't forget what you asked** | Your request becomes a numbered checklist in `.godmode/REQUEST.md`. A hook also writes every prompt you send, word for word, to `.godmode/SESSION.md`. Open a new session in the same folder, say "continue", and it picks up where you left off. |
| **No "done" without proof** | A hook blocks the finish once if code changed after the last test run, or if checklist items are still unticked. It is a nudge you can answer, not a hard lock. |
| **Shorter test logs** | Plain test commands (`pytest`, `npm test`, `go test`...) are run through a filter that keeps failures and the tail. A 315-line failing run came back as 51 lines, exit code intact. |
| **Help when stuck** | After repeated failing fix attempts, a hook suggests systematic debugging, then a stronger agent, then asking you. (Built and unit-tested; it has not yet fired on a real stuck task.) |

Guidance from five of the bundled Superpowers-style guides (TDD, brainstorming, debugging, verification, review handling) is added by hooks when your words or your test output match, so you don't type any slash commands.

## What we measured (small samples: read the caveats)

We scored runs with hidden tests: real merged GitHub pull requests (the maintainers' own tests) and harder tasks we wrote ourselves, in Python, Java and C++.

- **Plain Sonnet was enough on well-specified tasks.** Haiku, Sonnet and Opus all passed the six real-issue tasks that any of them could solve. Haiku cost **$0.10** for the six, Sonnet **$1.08**, Opus **$2.16**.
- **god-mode on Sonnet vs Opus on our own tasks:** 9 tasks, **$3.05 vs $5.10 (-40%)**, and a second set of 6 tasks, **$2.80 vs $4.05 (-31%)**. The sets overlap. Each cell is **one run**. Opus ran at *high* effort and Sonnet at *medium*, so part of the gap is effort, not model.
- **god-mode itself added no measurable saving over plain Sonnet** ($1.09 vs $1.08 on the six real tasks). The saving comes from the model choice.
- **The requirements checklist helped across sessions:** with Claude Code's built-in memory switched **off**, a session with nothing carried over lost every mid-session change (8 of 13 checks, 3 runs). With the checklist, or the hook-written log, all 13 passed (3 runs each). With built-in memory **on**, plain Claude Code also passed 13 of 13. One task, one artificial interruption.
- **A stronger planner or the built-in `/advisor` did not help:** Opus planning for a Haiku worker, and Haiku with an Opus advisor, cost 7-14x more than Haiku alone and scored the same, on tasks no tier could solve (2-6 runs). Treat that as "no evidence of benefit", not as proof.

## What it does NOT do

- It does not make a model smarter. On every task we could score, plain Sonnet matched it.
- The six hard real-issue tasks failed for every model, because their tests check internals the issue never states. They don't tell us where the models break.
- Caching is Anthropic's and we can't change it. The savings come from model choice and from restarting a long session with a short handoff.
- Some bundled guidance is only a written rule the model may ignore. Five guides fire from hooks; four are rules only.

## Things to know before installing

- **The test-output filter rewrites test commands.** It never approves anything: your normal permission rules apply to the rewritten command. If you allow only narrow patterns such as `Bash(pytest*)`, the rewritten command will ask for approval. Set `GODMODE_NO_FILTER=1` to turn it off.
- **The session log records every prompt you type**, including anything you paste. It lives in `.godmode/SESSION.md` in your project. Add `.godmode/` to `.gitignore` and don't paste secrets. `GODMODE_NO_SESSION_LOG=1` turns it off. It only runs in folders that already have a `.godmode/` folder.
- Install: `git clone` the repo and run `python install.py` (see INSTALL.md). Needs `bash` (Git Bash on Windows) and Python 3 on your PATH.

## The research gap (where we'd love help)

Everyone says one model is "better at coding". Coding is huge, and that sentence says little. Nobody we know of has published a map of where each model actually breaks.

**Open questions:**
- **Where does Haiku fail, and where does Sonnet?** Every task we could score was solved by every tier. We haven't found the breaking point.
- **Which kinds of coding are hard for which models?** Our guess is web work is easy, backend and security work (vulnerability finding, pen-testing) are harder, and signal-processing or RF code harder still. Untested.
- **Does a stronger model rescue a stuck task?** The escalation path exists but has never fired live.
- **How much does restarting a long session really save?** Cache reads are about a fifth of the bill in our logs. We haven't measured the saving from a clean restart.

## What's next

1. A **breaking-point map** by domain (web, backend, systems, numerics, security, RF), several runs per cell, with cost.
2. **Tasks where one tier passes and another fails**, so escalation can be proven or dropped.
3. **Matched-effort, repeated runs** of the Sonnet-vs-Opus comparison, with variance.
4. A measured **restart-vs-continue** cost comparison on real sessions.

## What's inside

- Hooks (Python and shell, standard library only): model advisor, test-output filter, ledger and verification checks, session log, failure ladder.
- A requirements-checklist workflow and nine bundled Superpowers guides (MIT licence, credited to Jesse Vincent).
- Optional extras, not measured to help: Opus planner, solver and reviewer agents, a Haiku executor, a code-graph query tool.
- Research notes, scripts and score files in `research/`, so you can check every number.
- Tests: hooks 14 + 35 + 21 + 32 and a 62-check skill selftest, all passing.

## Honest status

A research project with working tooling. Single runs are noisy and we say so. If you find a task where the cheap model fails and the expensive one wins, open an issue. That is the result we're looking for.
