# Triage

Pick a route before doing anything else. The goal is to spend orchestration overhead only where it buys quality or saves tokens.

## Signals

| Signal | Direct (+ review) | Full |
|---|---|---|
| Size | 1–5 files, contained | 6+ files, or unknown |
| Spec | Exact, or clear goal with an obvious approach | Vague, or several valid approaches |
| Shape | One coherent change, finishable in one sitting | Several dependent steps; may span sessions or need checkpoints |
| Code familiarity | Familiar, or quickly located with a few searches | Unfamiliar code or an external API to research |
| Tests | Exist or easy to add | Missing, or behaviour hard to test |
| Risk area | Small, well-understood fix (T3 care + reviewer) | Large or unclear change in a risk area |

**Review on Direct:** run the reviewer when the change is a feature or touches 3+ files; skip it for a one- or two-line fix.

**Cost note (measured 2026-11-12):** plain Claude Code solved clear 3–5 file features 100% correctly with few searches; every extra layer (ledger, research, graph) only added cost there. Full pays off only when work is long, multi-step, unfamiliar or interruptible.

Choose the route where most signals land. **Needs-research or several dependent steps push to Full on their own.** When genuinely torn, take Full.

Questions that need no code changes ("what does this function do?", "why is this test flaky?") are not tasks. Answer them directly without triage.

## Re-triage

Re-triage upward mid-task when:
- the change spreads to more files than expected,
- you hit a risk area you didn't anticipate,
- a test fails for a reason you don't understand.

Say it in one line ("Upgrading to Full: the fix touches the replay system too") and continue from the matching section of the workflow. Never re-triage downward mid-task.

## Risk areas

Default risk areas for any project: authentication and security, data migrations or anything that deletes data, concurrency and threading, numerical or physics code, protocol and serialization code, build and release configuration.

Projects add their own in their `CLAUDE.md`, under `## God Mode settings` → "Risk areas" (or an older `## Risk areas` section). Read it during triage.

**A step in a risk area is T3 and gets the reviewer, on any route.** A risk area pushes the whole task to Full only when the change is also large or unclear; a small, well-understood risk-area fix stays Direct, done carefully in this session and reviewed.

## Research routing

Research feeds the plan, and the planner can't see what a researcher left out. Route each question by its kind:

| Question | Who |
|---|---|
| Lookup: where is X, what calls Y, which file defines Z, what does library version N support | `researcher` (Haiku) |
| Behaviour: how does X behave, why does symptom S happen, data flow across modules, numerics, timing, threading, state | `researcher-deep` (Sonnet) |
| Behaviour of a project risk area, or whatever a T3 step will change | Main session reads it directly |

Phrase questions neutrally ("how does the render time get chosen?"), never as a hypothesis to confirm. Researchers read `.godmode/graph-brief.txt` first (short: hub files, boundaries), Grep `.godmode/project-map.json` only for a specific file's importers, and fall back to Grep for calls and unmapped connections. Before a plan relies on a researcher's "Load-bearing claim", open its `path:line` and check it; that costs seconds. Treat a non-empty "Not read" list as a gap: read those spots yourself or ask a follow-up question.

## Tiers (per step, Full route)

**T1 (Haiku).** The step is fully determined by its text. No judgment calls. Examples: add a field and wire it through files that already follow the pattern; write tests from a listed set of cases; rename across files; add a config entry; write docstrings.

**T2 (Sonnet).** Clear spec but needs normal programming judgment: choosing data structures, handling edge cases, writing a function from a described behaviour, fixing a bug whose cause is known.

**T3 (stay in main session).** Needs deep reasoning or is costly if wrong: physics and math, concurrency, state machines, protocol handling, security-sensitive code, debugging an unknown cause, any step in a risk area.

Tagging rule: if you can't write the step precisely enough for it to be T1 or T2, it's T3. Don't tag a vague step T1 and hope.
