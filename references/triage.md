# Triage

Pick a route before doing anything else. The goal is to spend orchestration overhead only where it buys quality or saves tokens.

## Signals

| Signal | Direct | Light | Full |
|---|---|---|---|
| Files touched | 1–2 | 3–5 | 6+ or unknown |
| Spec clarity | Exact ("rename X to Y") | Clear goal, obvious approach | Vague, or several valid approaches |
| Kind of change | Edit to existing code | Small new piece or contained edit | New subsystem, refactor, cross-module change |
| Tests | Exist or not needed | Exist or easy to add | Missing, or behaviour hard to test |
| Risk area touched | No | Yes, if small and well understood (step is T3, reviewed) | Yes, if also large or unclear (see project CLAUDE.md) |
| Needs research first | No | No | Yes: unfamiliar code or external API |

Choose the route where most signals land. **Needs-research pushes to Full on its own. A risk area rules out Direct, and pushes to Full only when the change is also large or unclear.** When split between two routes, take the higher one.

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

**A step in a risk area is T3 and gets the reviewer, on any route.** A risk area pushes the whole task to Full only when the change is also large or unclear. A small, well-understood risk-area fix can stay Light, as long as its step is T3 and it's reviewed.

## Research routing

Research feeds the plan, and the planner can't see what a researcher left out. Route each question by its kind:

| Question | Who |
|---|---|
| Lookup: where is X, what calls Y, which file defines Z, what does library version N support | `researcher` (Haiku) |
| Behaviour: how does X behave, why does symptom S happen, data flow across modules, numerics, timing, threading, state | `researcher-deep` (Sonnet) |
| Behaviour of a project risk area, or whatever a T3 step will change | Main session reads it directly |

Phrase questions neutrally ("how does the render time get chosen?"), never as a hypothesis to confirm. Before a plan relies on a researcher's "Load-bearing claim", open its `path:line` and check it; that costs seconds. Treat a non-empty "Not read" list as a gap: read those spots yourself or ask a follow-up question.

## Tiers (per step, Light and Full routes)

**T1 (Haiku).** The step is fully determined by its text. No judgment calls. Examples: add a field and wire it through files that already follow the pattern; write tests from a listed set of cases; rename across files; add a config entry; write docstrings.

**T2 (Sonnet).** Clear spec but needs normal programming judgment: choosing data structures, handling edge cases, writing a function from a described behaviour, fixing a bug whose cause is known.

**T3 (stay in main session).** Needs deep reasoning or is costly if wrong: physics and math, concurrency, state machines, protocol handling, security-sensitive code, debugging an unknown cause, any step in a risk area.

Tagging rule: if you can't write the step precisely enough for it to be T1 or T2, it's T3. Don't tag a vague step T1 and hope.
