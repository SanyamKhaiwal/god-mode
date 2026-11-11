---
name: god-mode
description: "Orchestrates coding work in Claude Code: triages each task by complexity, plans with the main (Opus) session, delegates execution to cheaper subagents (Haiku/Sonnet) by tier, verifies every step with real commands, escalates failures, and keeps a lossless-as-possible handoff ledger in .godmode/ so work survives /clear, compaction, and new sessions. Use this skill for ANY coding or implementation task — features, bug fixes, refactors, tests, build or config changes — even small ones, because triage decides whether the pipeline is needed. Also use it when a session starts with an unfinished .godmode/PLAN.md, or when the user says \"god mode\", \"/god-mode\", \"quick\", or \"full\"."
---

# God Mode

Plan with the strongest model, execute with the cheapest model that can do each step correctly, verify everything, and never lose state.

The core bet: a precise plan lets cheap models execute without thinking much, and automatic verification catches the cases where they get it wrong. Both halves matter. A vague plan makes cheap executors fail; skipped verification lets their mistakes through silently.

## 0. Start of every task

1. **Overrides.** If the user wrote `quick`, use the Direct route. If they wrote `full`, use the Full route. Skip triage in both cases.
2. **Resume check.** If `.godmode/PLAN.md` exists in the project and its `Status` is not `done`, read it and `.godmode/HANDOFF.md` first. Ask the user whether the new message continues that task or starts a new one. If new, archive the old task (section 6) before starting.
3. **Project settings.** If the project's `CLAUDE.md` has a `## God Mode settings` section, it overrides the defaults here. It names the project record, the results log, the build and test commands, the risk areas, and any build or research limits.
4. **Triage.** Read `references/triage.md` and pick a route: Direct, Light, or Full. State the route in one line ("Route: Light — 3 files, clear spec, tests exist") so the user can override it.

When unsure between two routes, pick the higher one. Under-routing a hard task costs far more than the extra planning on an easy one.

## 1. Direct route

Do the task yourself, in this session. No `.godmode/` files, no subagents. Run the relevant tests or build if they exist. If the change produced a result worth keeping (a measured number, a fixed bug's cause, a quirk), add it to the project's results log or record (section 6, step 2) before finishing.

If the task turns out bigger than it looked (more files, a failing test you don't understand), stop and re-triage upward. Say so in one line. Touching a project risk area always means at least Light.

## 2. Light route

1. Create `.godmode/` if missing and copy `assets/PLAN.template.md` to `.godmode/PLAN.md` and `assets/HANDOFF.template.md` to `.godmode/HANDOFF.md`.
2. Write a short plan: goal, 1–4 steps, each with files, acceptance check and tier tag. No research phase, no approval pause.
3. Set the git checkpoint (section 4), execute steps, verify, then finish (section 6).
4. A step in a project risk area is tagged T3 and done in this session. If any step is, run the reviewer before finishing (section 4, "Review").

## 3. Full route

### 3a. Research
On multi-file codebases, ensure `.godmode/project-map.json` is fresh via `scripts/build-graph.py` so researchers query the pre-indexed dependency graph first instead of blind crawling.

Delegate reading by the kind of question (see "Research routing" in `references/triage.md`):
- Lookups go to `researcher` (Haiku).
- Questions about how code behaves go to `researcher-deep` (Sonnet).
- Risk-area behaviour, and anything a T3 step will change, you read yourself.

Give each researcher one narrow, neutral question ("How does input flow from the gamepad to the tire model? List files and the key functions.") rather than "read the codebase", and never a hypothesis to confirm. Run independent questions in parallel. Researchers return summaries; keep their raw reading out of this context.

Before the plan relies on a researcher's **Load-bearing claims**, open each `path:line` and check it. Close any gap the **Not read** list reveals.

Also check current docs for any external API, library, or engine feature the plan will touch, rather than relying on memory. Versions change.

### 3b. Plan
Fill `.godmode/PLAN.md` from the template. Every step needs:
- **Files**: exact paths.
- **Change**: what to do, concretely. Name functions, signatures, data shapes.
- **Acceptance**: a command to run and what passing looks like.
- **Tier**: T1, T2, or T3 (see `references/triage.md`).
- **Depends on**: earlier steps, if any.

The test of a good step: could a model that has never seen this conversation complete it from the step text plus the files listed? If not, add detail. See `references/examples.md` for a vague step rewritten into an executable one.

Include a whole-task verification section (full test suite, build, lint).

### 3c. Approval
Show the user the plan (step titles, tiers, and anything risky) and wait for approval or edits. This is the cheapest point to catch a wrong assumption. Set `Status: approved` once they agree.

Then execute (section 4) and finish (section 6).

## 4. Executing steps

**Git checkpoint first.** Before the first step, if the project is a git repo, record `git rev-parse HEAD` as `Base commit:` in PLAN.md. If the working tree has uncommitted changes, tell the user and ask whether to commit or stash them first, so the task's diff stays separate from their own work. The reviewer diffs against this base, and it's the rollback point if an executor makes a mess. Not a git repo: say so once and continue.

Route each step by tier:

| Tier | Who executes | Typical work |
|---|---|---|
| T1 | `executor-light` subagent (Haiku) | Mechanical: boilerplate, renames, wiring, tests written from a spec, docs |
| T2 | `executor` subagent (Sonnet) | Normal logic with a clear spec |
| T3 | You, in this session | Hard reasoning: physics, numerics, concurrency, state machines, security, cross-cutting refactors |

If those agents aren't installed, use a general-purpose subagent and say in the brief which model it should run as, if you can set that; otherwise keep T1/T2 steps here.

**Executor brief.** Subagents don't see this conversation. Each brief must contain: the step text from PLAN.md, the relevant facts from research, the exact acceptance command, any dead ends from HANDOFF.md that apply, and the instruction to return a short report (what changed, files touched, acceptance output, anything surprising). See `references/examples.md`.

**Subagents have a fixed cost.** Each one starts at about 10–11k tokens (its system prompt and tools) before reading anything, and it re-reads files you may already have open. So:
- Combine small T1/T2 steps that touch related files into one brief.
- Don't delegate a step whose brief would be as long as the edit itself. Writing exact text into a brief costs you the same output tokens as writing it into the file, so do those steps yourself.
- Delegation pays off when the executor reads, builds, tests or iterates. That work stays out of your context.

Independent steps (no shared files, no dependency) can run in parallel, except when their acceptance commands compile or build the same project. Concurrent builds lock or corrupt each other (Unreal and C++ builds especially), so run those steps one at a time. Follow the project settings' build limits (for example, "Unreal build: main session only").

**Steps that can't be checked by a command.** Some acceptance is inherently human: how a car feels to drive, whether a UI looks right, behaviour on real hardware. Mark those steps `Acceptance: MANUAL — <what the user should check>`. Batch manual checks where possible, ask the user to run them, and log their answer in HANDOFF.md before marking the step done. Never mark a manual step done on your own judgment.

**Files executors can't edit.** Binary or editor-owned assets (Unreal `.uasset`/`.umap` and Blueprints, Qt Designer files when the project treats them as generated, images, compiled outputs) can't be changed safely through text edits. Plan those changes as MANUAL steps with exact instructions for the user, or do them through code (C++, Python) where the engine allows.

**After each step:**
1. Run the step's acceptance command yourself, through `~/.claude/skills/god-mode/scripts/godmode-run.sh <step-id> <command>`. It trims noisy output and appends date, step, PASS/FAIL, exit code and the summary line (plus the failing tail) to `.godmode/test-log.md`. A script writes the test record, not memory, so it survives compaction.
2. Pass: mark the step `done` in PLAN.md, and update HANDOFF.md (Current step, Next action, Files touched, and any Results).
3. Fail: log the exact error and what was tried under Dead ends, then retry with a corrected brief.

**Escalation.** A step that fails twice at its tier moves up one tier (T1 → T2 → T3). A T3 step that fails twice: stop and ask the user, with the dead ends summarized. Don't loop.

**Review.** After the last step passes, send the `reviewer` subagent the plan's goal, the acceptance criteria, and the base commit (it runs `git diff <base>`). Do this for Full-route tasks, and for any task with a step in a project risk area. Fix anything real it finds; log what you rejected and why under Decisions.

## 5. The handoff ledger

`.godmode/HANDOFF.md` is the task's memory. Update it as you go, not at the end:
- **Rewrite in place**: Status, Current step, Next action.
- **Append**: Test log entries, Dead ends, Decisions, Learnings.

Dead ends are the most valuable section. A future session that doesn't know an approach already failed will try it again.

**The Stop hook enforces this.** `scripts/check-handoff.sh` runs when you're about to end a turn. If a task is in progress and project files changed after HANDOFF.md was last written, it blocks the stop once and asks you to update HANDOFF.md first. When it fires, update the ledger; don't argue with it.

**Checkpoints.** After every few completed steps, and whenever the conversation is getting long, make sure HANDOFF.md is fully current. When context is getting heavy (many tool calls, long outputs, or a system note about context), finalize the ledger and tell the user in one line that it's a good point to run `/clear`. The session-start hook reloads PLAN.md and HANDOFF.md, so nothing structured is lost. You can't run `/clear` yourself.

If a past detail is missing from the ledger, the full session transcript is still stored by Claude Code locally and can be searched rather than guessed.

## 6. Finishing a task

1. Run the whole-task verification from PLAN.md, through `godmode-run.sh`.
2. **Merge into the project record.** `.godmode/` is scratch for one task. What lasts goes into the files named in the project's `## God Mode settings`:
   - **Project record** (e.g. `Docs/4_Session_Handoff.md`):
     - Rewrite its "Current state" block (between `<!-- godmode:inject:start -->` and `<!-- godmode:inject:end -->`): date, commit, what works, what's open, the next action. Keep it under about 40 lines; the session-start hook prints it into every new, cleared or compacted session.
     - Add the task's one-line Learnings to the block's Learnings list.
     - Fold Decisions and Next steps into the record's matching sections.
     - Write the task outcome where the record keeps history.
   - **Results log** (e.g. `Docs/Results.md`): append a row for every number in HANDOFF.md's Results, and for the final test counts from `.godmode/test-log.md`, each with date and commit.
   - **CLAUDE.md** gets a new line only for a new hard rule or convention, never a task summary. It's loaded on every request, so every line costs on every turn.
   - With no project record configured: put Learnings in `CLAUDE.md` under `## Learnings` (one line each), and suggest setting up a project record.

   Tell the user, in a few lines, what you added and where.
3. Set `Status: done` in both files.
4. Move PLAN.md, HANDOFF.md and test-log.md into `.godmode/archive/<YYYY-MM-DD>-<task-slug>/`.
5. If `.godmode/` isn't in the project's `.gitignore`, suggest adding it once.

## 7. Token discipline

- Subagents return summaries, never raw file dumps or full logs.
- Run acceptance and verification commands through `scripts/godmode-run.sh <step> <command>`, so they're trimmed and logged. For other noisy commands, use `scripts/filter-output.sh` directly; it keeps failures, errors and the tail of the output. Example: `~/.claude/skills/god-mode/scripts/filter-output.sh npm test`.
- From Git Bash, write Windows script paths with forward slashes (`Tools/Build.ps1`). Backslashes can get lost on the way through the shell.
- Don't re-read a file you've already read unless it changed.
- Keep PLAN.md and HANDOFF.md tight: facts, commands, errors. No narrative.

## Reference files

- `references/triage.md`: route rubric and tier definitions. Read at every triage.
- `references/examples.md`: worked triage decisions, plan steps, executor brief, handoff entries. Read before writing your first plan in a session.
- `assets/PLAN.template.md`, `assets/HANDOFF.template.md`: copied into `.godmode/` per task.
- `scripts/session-start.sh`: SessionStart hook. On every start, `/clear` and compaction it prints the project record's "Current state" block and the end of the results log, then any unfinished PLAN/HANDOFF.
- `scripts/check-handoff.sh`: Stop hook. Blocks ending a turn once when a task is in progress and HANDOFF.md is older than the changed files.
- `scripts/godmode-run.sh`: runs an acceptance command (trimmed by filter-output.sh) and appends the result to `.godmode/test-log.md`.
- `scripts/filter-output.sh`: runs a command and trims its output.
- `scripts/selftest.sh`: tests the three scripts above in temp folders. Run it after editing any of them.
