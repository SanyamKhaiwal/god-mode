# God Mode: Full route

Read this only for a Full-route task (long, multi-step, unfamiliar, risky and large, or likely to span sessions). Paths are relative to the god-mode skill folder. SKILL.md's model, search and discipline tables still apply.

## 1. Setup

**Ledger first.** Before your first edit, create `.godmode/` if missing and copy `assets/PLAN.template.md` to `.godmode/PLAN.md` and `assets/HANDOFF.template.md` to `.godmode/HANDOFF.md`. **Keep the template's step format exactly** (`### S1: <title> [T1] [status: todo]`, then `- Files:`, `- Change:`, `- Acceptance:`, `- Executor:`). The Stop hook parses those headings; a free-form plan is blocked.

### 1a. Research
**Dependency graph (optional).** On very large or C/C++ codebases, where text search is weak, you may build an index (`python ~/.claude/skills/god-mode/scripts/build-graph.py . .godmode/project-map.json --quiet`) and answer "where is X / who imports or uses X" with `python ~/.claude/skills/god-mode/scripts/graph-query.py where|importers|refs|outline <arg>`. Measured on a 543-file Python repo it was cost-neutral (−36% searches on one task, +7% cost on another), so don't build it by default; targeted Grep is usually as cheap.

**Research is not optional on Full.** Unless you can name every affected file and function from code you have already read in this session, send at least one question to a researcher. Record each question and the agent that answered it under Decisions in HANDOFF.md.

Delegate reading by the kind of question (see "Research routing" in `references/triage.md`):
- Lookups go to `researcher` (Haiku).
- Questions about how code behaves go to `researcher-deep` (Sonnet).
- Risk-area behaviour, and anything a T3 step will change, you read yourself.

Give each researcher one narrow, neutral question ("How does input flow from the gamepad to the tire model? List files and the key functions.") rather than "read the codebase", and never a hypothesis to confirm. Run independent questions in parallel. Researchers return summaries; keep their raw reading out of this context.

Before the plan relies on a researcher's **Load-bearing claims**, open each `path:line` and check it. Close any gap the **Not read** list reveals.

Also check current docs for any external API, library, or engine feature the plan will touch, rather than relying on memory. Versions change.

### 1b. Plan
**Brainstorm first when the design is open.** (The UserPromptSubmit hook adds a `God-mode: this request is an open software design` note when it detects one.) If the task is architecture, a new subsystem, or has several valid approaches, read `superpowers/brainstorming/QUICK.md` (this skill's folder) and follow it before writing the plan: explore intent and constraints, compare 2–3 approaches with trade-offs, pick one. In a non-interactive session, don't wait for answers: record the open questions as assumptions in REQUEST.md and continue. Record the chosen approach and the rejected ones under Decisions in HANDOFF.md.

Fill `.godmode/PLAN.md` from the template. Every step needs:
- **Files**: exact paths.
- **Change**: what to do, concretely. Name functions, signatures, data shapes.
- **Acceptance**: a command to run and what passing looks like.
- **Tier**: T1, T2, or T3 (see `references/triage.md`).
- **Depends on**: earlier steps, if any.

The test of a good step: could a model that has never seen this conversation complete it from the step text plus the files listed? If not, add detail. See `references/examples.md` for a vague step rewritten into an executable one.

Include a whole-task verification section (full test suite, build, lint).

### 1c. Approval
Show the user the plan (step titles, tiers, and anything risky) and wait for approval or edits. This is the cheapest point to catch a wrong assumption. Set `Status: approved` once they agree.

Then execute (section 2) and finish (section 2).

## 2. Executing steps

**Baseline tests.** Before the first step, run the whole-task test command once through `godmode-run.sh BASELINE <command>` and record any already-failing tests in PLAN.md as `Baseline failures: <names or count>`. FINAL passes when it shows no failures beyond that baseline; say so explicitly in HANDOFF.md rather than treating the known failures as a regression.

**Git checkpoint first.** Before the first step, if the project is a git repo, record `git rev-parse HEAD` as `Base commit:` in PLAN.md. If the working tree has uncommitted changes, tell the user and ask whether to commit or stash them first, so the task's diff stays separate from their own work. The reviewer diffs against this base, and it's the rollback point if an executor makes a mess. Not a git repo: say so once and continue.

Route each step by tier:

| Tier | Who executes | Typical work |
|---|---|---|
| T1 | You (Sonnet), or `executor-light` (Haiku) when large | Mechanical: boilerplate, renames, wiring, tests written from a spec, docs |
| T2 | You (Sonnet) | Normal logic with a clear spec |
| T3 | `solver` agent (Opus) | Hard reasoning: physics, numerics, concurrency, state machines, security, cross-cutting refactors |

If those agents aren't installed, use a general-purpose subagent and say in the brief which model it should run as, if you can set that; otherwise keep T1/T2 steps here.

**Executor brief.** Subagents don't see this conversation. Each brief must contain: the step text from PLAN.md, the relevant facts from research, the exact acceptance command, any dead ends from HANDOFF.md that apply, and the instruction to return a short report (what changed, files touched, acceptance output, anything surprising). See `references/examples.md`.

**Delegation rule (Full route).** Subagents have a fixed cost: each one starts at about 10–11k tokens before reading anything. Use this test, not intuition:
- **Delegate** a T1/T2 step (or a group of related small steps) when it is big enough to repay the startup cost: roughly 100+ changed lines, or a long build/test/iterate loop, or reading you don't want in your context. Measured 2026-11-12: on steps of 5–30 minutes, delegation never lowered total cost.
- **Otherwise do it yourself**, which is the normal case for steps of a few dozen lines.
- **Combine** small T1/T2 steps that touch related files into one brief.
- **Do it yourself** when the test above says so, and write `Executor: self (<reason>)` on the step in PLAN.md, so the decision is visible.
- Every Full-route step carries an `Executor:` line (`executor-light`, `executor`, or `self (reason)`).

**Parallel work.** With 2+ independent steps, read `superpowers/dispatching-parallel-agents/QUICK.md` first; if their edits could touch the same files, or the user wants isolation, also `superpowers/using-git-worktrees/QUICK.md`. Independent steps (no shared files, no dependency) can run in parallel, except when their acceptance commands compile or build the same project. Concurrent builds lock or corrupt each other (Unreal and C++ builds especially), so run those steps one at a time. Follow the project settings' build limits (for example, "Unreal build: main session only").

**Steps that can't be checked by a command.** Some acceptance is inherently human: how a car feels to drive, whether a UI looks right, behaviour on real hardware. Mark those steps `Acceptance: MANUAL — <what the user should check>`. Batch manual checks where possible, ask the user to run them, and log their answer in HANDOFF.md before marking the step done. Never mark a manual step done on your own judgment.

**Files executors can't edit.** Binary or editor-owned assets (Unreal `.uasset`/`.umap` and Blueprints, Qt Designer files when the project treats them as generated, images, compiled outputs) can't be changed safely through text edits. Plan those changes as MANUAL steps with exact instructions for the user, or do them through code (C++, Python) where the engine allows.

**After each step:**
1. Run the step's acceptance command yourself, through `~/.claude/skills/god-mode/scripts/godmode-run.sh <step-id> <command>`, using the real step id (`S1`, `S2`…). One log entry per step, **including steps you executed yourself**, plus `FINAL` for the whole-task check; never fold several steps into one run. It trims noisy output and appends date, step, PASS/FAIL, exit code and the summary line (plus the failing tail) to `.godmode/test-log.md`. A script writes the test record, not memory, so it survives compaction.
2. Pass: mark the step `done` in PLAN.md, and update HANDOFF.md (Current step, Next action, Files touched, and any Results).
3. Fail: log the exact error and what was tried under Dead ends, then retry with a corrected brief.

**Escalation ladder.** A hook (`~/.claude/hubs/ladder-hook.py`, on PostToolUseFailure/PostToolUse for Bash) counts consecutive failures of each test/build command and adds the next rung to your context as a `GOD-MODE LADDER` line; `godmode-run.sh` prints the same rungs per step. Follow it, don't argue with it:
1. **1st failure:** read `superpowers/systematic-debugging/QUICK.md` (this skill's folder) and follow it for the next attempt: reproduce, trace to the root cause, one hypothesis at a time, no guess-fixes. Record what you traced under Dead ends.
2. **2nd failure:** hand the step to the `solver` agent (Opus) with the step text, the failing output and your debugging notes. Don't attempt a third fix yourself.
3. **3rd failure** (the solver's attempt failed too): stop and ask the user, with the dead ends summarized.
A Haiku (`executor-light`) step that fails twice comes back to you first. `BASELINE` runs are exempt (known failures).

**Review.** After the last step passes, send the `reviewer` subagent the plan's goal, the acceptance criteria, and the base commit (it runs `git diff <base>`). Do this for Full-route tasks, and for any task with a step in a project risk area. Fix anything real it finds; log what you rejected and why under Decisions.

## 3. The handoff ledger

`.godmode/HANDOFF.md` is the task's memory. Update it as you go, not at the end:
- **Rewrite in place**: Status, Current step, Next action.
- **Append**: Test log entries, Dead ends, Decisions, Learnings.

Dead ends are the most valuable section. A future session that doesn't know an approach already failed will try it again.

**The Stop hook enforces this.** `scripts/check-handoff.sh` runs when you're about to end a turn. If a task is in progress and project files changed after HANDOFF.md was last written, it blocks the stop once and asks you to update HANDOFF.md first. When it fires, update the ledger; don't argue with it.

**Checkpoints.** After every few completed steps, and whenever the conversation is getting long, make sure HANDOFF.md is fully current. When context is getting heavy (many tool calls, long outputs, or a system note about context), finalize the ledger and tell the user in one line that it's a good point to run `/clear`. The session-start hook reloads PLAN.md and HANDOFF.md, so nothing structured is lost. You can't run `/clear` yourself.

If a past detail is missing from the ledger, the full session transcript is still stored by Claude Code locally and can be searched rather than guessed.

## 4. Finishing a task

A task isn't finished when the last step passes. It's finished when every item below is done, in this order, in the same turn. The Stop hook blocks ending a turn while all steps are `done` but the plan isn't, so a resumed session that completes the last step must also finish here.

1. Run the whole-task verification from PLAN.md, through `godmode-run.sh FINAL <command>`.
1b. Run the reviewer (section 2, "Review") if the route is Full or any step was in a risk area, and handle its findings.
2. **Merge into the project record.** `.godmode/` is scratch for one task. What lasts goes into the files named in the project's `## God Mode settings`:
   - **Project record** (e.g. `Docs/4_Session_Handoff.md`):
     - Rewrite its "Current state" block (between `<!-- godmode:inject:start -->` and `<!-- godmode:inject:end -->`): date, commit, what works, what's open, the next action. Keep it under about 40 lines; the session-start hook prints it into every new, cleared or compacted session.
     - Add the task's one-line Learnings to the block's Learnings list.
     - Fold Decisions and Next steps into the record's matching sections.
     - Write the task outcome where the record keeps history.
   - **Results log** (e.g. `Docs/Results.md`): append a row for every number in HANDOFF.md's Results, and for the final test counts from `.godmode/test-log.md`, each with date and commit.
   - **CLAUDE.md** gets a new line only for a new hard rule or convention, never a task summary. It's loaded on every request, so every line costs on every turn.
   - With no project record configured: put Learnings in `CLAUDE.md` under `## Learnings` (create the section; one line each), and suggest setting up a project record.
   - **Always** write HANDOFF.md's Learnings: at least one line (a quirk, a dead end worth remembering, a command that matters) or the explicit word `none`. Every non-`none` learning must land in the project record or CLAUDE.md before archiving.

   Tell the user, in a few lines, what you added and where.
3. Rewrite HANDOFF.md's header to its final values (`Status: done`, `Current step: none`, `Next action: none`, with a one-line outcome), make sure its Decisions, Dead ends and Learnings reflect the task, then set `Status: done` in PLAN.md.
4. Confirm every REQUEST.md item is ticked and true in the code, then move REQUEST.md, PLAN.md, HANDOFF.md and test-log.md into `.godmode/archive/<YYYY-MM-DD>-<task-slug>/`.
5. On a feature branch, or if the user asked to merge or open a PR: read `superpowers/finishing-a-development-branch/QUICK.md` and follow it.
6. If `.godmode/` isn't in the project's `.gitignore`, suggest adding it once.

## 5. Token discipline

- Subagents return summaries, never raw file dumps or full logs.
- Run acceptance and verification commands through `scripts/godmode-run.sh <step> <command>`, so they're trimmed and logged. For other noisy commands, use `scripts/filter-output.sh` directly; it keeps failures, errors and the tail of the output. Example: `~/.claude/skills/god-mode/scripts/filter-output.sh npm test`.
- From Git Bash, write Windows script paths with forward slashes (`Tools/Build.ps1`). Backslashes can get lost on the way through the shell.
- Don't re-read a file you've already read unless it changed.
- Keep PLAN.md and HANDOFF.md tight: facts, commands, errors. No narrative.

