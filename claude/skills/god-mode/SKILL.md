---
name: god-mode
description: "Sonnet-first coding workflow for Claude Code: runs the main session on Sonnet, calls an Opus planner/solver agent only for vague, hard or failing work and Haiku for large mechanical steps, picks graph or grep search by question, keeps a requirements ledger in .godmode/REQUEST.md so nothing is lost across sessions, and verifies every step. Use it for multi-step coding work, refactors, unfamiliar or risky code, work likely to span sessions, or an unfinished .godmode/ task."
---

# God Mode

Run on the cheapest model that keeps quality, call a stronger model only where it pays, verify everything, never lose state. Every rule here was kept because a measurement supported it; guides load only when their trigger fires.

## 1. Start

1. **Overrides.** `quick` → Direct. `full` → Full.
2. **Resume.** If `.godmode/REQUEST.md` has unchecked items or `.godmode/PLAN.md` isn't `done` (the SessionStart hook prints them), or the user says "continue": read them first, check **every** checklist item against the current code (ticked or not), fix gaps, then continue. If the new message is a different task, archive the old files to `.godmode/archive/<date>-<slug>/` first.
3. **Route.** State it in one line ("Route: Direct — 3 files, clear spec, tests exist").
   - **Direct**: one coherent change you can finish in one sitting, in code you can locate with a few searches (even 3–5 files).
   - **Full**: 6+ files or unknown scope, several dependent steps, vague spec or several valid designs, unfamiliar code or external API to research, large change in a risk area, or work likely to span sessions. Then read `references/full-route.md` and follow it. A stated Full is binding; upgrading Direct → Full is always allowed.
   - Risk areas (auth/security, data migrations or deletion, concurrency, numerics/physics, protocols/serialization, build/release config, plus any in the project's `CLAUDE.md` → "God Mode settings") always get the reviewer.
4. **Requirements ledger (every route).** Before the first edit, write `.godmode/REQUEST.md`: the request verbatim, then a numbered checklist of every acceptance requirement (`- [ ] 1. …`; exact formats, flags, error texts and "must stay unchanged" items included). Tick items as you finish them. Skip it only for a single-requirement, one-spot change.

## 2. Who does the work

The session runs on Sonnet. Stronger models work as short-lived agents with a fresh context, because re-reading a long conversation is what makes them expensive.

| Situation | Who | How |
|---|---|---|
| Normal step | You | Do it yourself |
| Large mechanical step (~50+ lines of boilerplate, renames across many files, tests from a listed spec) | `executor-light` (Haiku) | Brief it; if it fails twice, do it yourself |
| Vague request, several valid designs, or a Full task | `planner` (Opus) | Send the request; put its checklist into REQUEST.md and follow its plan |
| Hard step: concurrency, security, numerics, state machines, a cause you can't pin down | `solver` (Opus) | Hand it that step with its context |

If `planner`/`solver` aren't installed, tell the user once that a stronger model (`/model opus`) is recommended for the hard part.

## 3. Disciplines (read the QUICK file only when the trigger fires)

All paths are under `superpowers/` in this skill's folder; each folder also has the full `GUIDE.md`.

| Trigger | Read | Enforced by |
|---|---|---|
| Open software design: architecture, new subsystem, 2+ valid approaches | `brainstorming/QUICK.md` before planning | prompt hook note |
| Bug fix | `test-driven-development/QUICK.md`: failing regression test first | prompt hook note |
| New behaviour with a clear spec and a test framework | same: test first. Not for refactors with existing tests, docs, config, visual UI | this rule |
| A test/build still fails after your fix attempt | `systematic-debugging/QUICK.md`; 2nd failed attempt → `solver`; 3rd → ask the user | hook: `GOD-MODE LADDER` lines |
| About to say "done" | Run the tests/build after your last code edit and report the real output | Stop hook |
| Sending work to the `reviewer` (risk area, ~150+ changed lines, or behaviour your tests don't cover) | `requesting-code-review/QUICK.md` | this rule |
| The reviewer returned findings | `receiving-code-review/QUICK.md`: verify each finding before acting | hook note |
| Full route, 2+ independent steps | `dispatching-parallel-agents/QUICK.md` | full-route.md |
| Parallel steps that could touch the same files, or the user asks for isolation | `using-git-worktrees/QUICK.md` | full-route.md |
| Task finished on a feature branch, or the user asks to merge / open a PR | `finishing-a-development-branch/QUICK.md` | this rule |

Follow hook notes (`GOD-MODE LADDER`, `God-mode:`) when they appear; they fire only when needed.

## 4. Search

| Question | Use |
|---|---|
| Who imports/uses X? What breaks if I change it? | `python <skill-dir>/scripts/graph-query.py refs <Name>` or `importers <file>` |
| Where is symbol X defined? (300+ files, or C/C++/Java/Unreal where names repeat) | `graph-query.py where <Name>` |
| What's in this unfamiliar file? | `graph-query.py outline <file>` |
| Literal text, how a function behaves, small repos | Grep, then read the function |

`graph-query.py` builds its index on first use (1–2 s). Ask one specific query at a time; never paste a whole graph into context.

## 5. Direct route

1. Do the work in this session. Record `git rev-parse HEAD` first if a review may be needed.
2. Run tests and builds through `<skill-dir>/scripts/godmode-run.sh TEST <command>`: it trims the output (−75–84% tokens) but keeps each failure's location.
3. Review only where it pays (section 3). On clear features with passing tests the reviewer changed nothing in 6 measured runs.
4. Finish: every REQUEST.md item ticked and true in the code, tests run after the last edit, then move REQUEST.md to `.godmode/archive/<YYYY-MM-DD>-<slug>/`. Add a result worth keeping (a measured number, a bug's root cause, a quirk) to the project's record or `CLAUDE.md` → `## Learnings`, one line.
5. If it turns out bigger than it looked (more files, dependent steps, a failure you don't understand), say so in one line and switch to Full.

## 6. Token discipline

- Don't re-read a file you've already read unless it changed.
- Subagents return summaries, never file dumps or full logs.
- Keep ledger files to facts, commands and errors.
- Between unrelated tasks, suggest `/clear`: the ledger makes it safe, and a short context is the biggest cost lever.

## Files

- `references/full-route.md`: research, plan, execution, handoff ledger and finish for Full tasks.
- `references/triage.md`, `references/examples.md`: tiers, risk areas, worked examples (Full route).
- `superpowers/`: nine vendored guides (MIT), each with `QUICK.md` and `GUIDE.md`.
- `scripts/`: `godmode-run.sh`, `filter-output.sh`, `graph-query.py`, `build-graph.py`, hooks (`session-start.sh`, `check-handoff.sh`), `selftest.sh`.
- Hooks outside the skill: `~/.claude/hubs/ladder-hook.py` (ladder, verification, review notes), `~/.claude/hubs/model-advisor.py` (model suggestion, design and bug-fix notes).
