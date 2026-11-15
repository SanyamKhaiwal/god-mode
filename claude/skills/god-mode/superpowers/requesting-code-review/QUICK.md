# Requesting code review quick reference
Core rule: review early, review often; a reviewer subagent gets crafted context, never your session history.

When: mandatory after each task from the plan, after a major feature, before merge to main. Optional: when stuck, before refactoring, after a complex bug fix.

Steps:
1. Get SHAs: BASE_SHA (e.g. HEAD~1 or origin/main) and HEAD_SHA (HEAD).
2. Dispatch a `general-purpose` subagent using the template code-reviewer.md, filling {DESCRIPTION}, {PLAN_OR_REQUIREMENTS}, {BASE_SHA}, {HEAD_SHA}.
3. Act on feedback: fix Critical immediately, fix Important before proceeding, note Minor for later.
4. Push back, with reasoning, if the reviewer is wrong.

Never:
- Skip review because the change is "simple".
- Ignore Critical issues.
- Proceed with unfixed Important issues.
- Review the diff inline yourself instead of dispatching a reviewer.
- Argue with valid technical feedback.

Full guide: superpowers/requesting-code-review/GUIDE.md
