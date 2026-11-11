# Plan: <task title>

Status: planning
Route: <Light | Full>
Created: <YYYY-MM-DD>
Base commit: <git rev-parse HEAD before step 1 | not a git repo>

## Goal
<One or two sentences: what done looks like, from the user's point of view.>

## Context
<Facts from research the steps depend on: relevant files, how the current code works, API/library versions checked.>

## Constraints and non-goals
- <What must not change; what this task deliberately doesn't do.>

## Steps

### S1: <title> [T1|T2|T3] [status: todo]
- Files: <exact paths>
- Change: <concrete: functions, signatures, data shapes>
- Acceptance: `<command>` → <what passing looks like>  (or: MANUAL — <what the user checks>)
- Depends on: <none | S#>

### S2: <title> [T#] [status: todo]
- Files:
- Change:
- Acceptance:
- Depends on:

## Whole-task verification
- `<full test command>`
- `<build command>`
- `<lint command>`
