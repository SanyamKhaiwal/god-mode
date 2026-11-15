# Systematic debugging quick reference
Core rule: no fixes without root-cause investigation first; symptom fixes are failure.

Steps:
1. Root cause: read errors fully; reproduce reliably; check recent changes; in multi-component systems log at each boundary to find WHERE it breaks; trace bad data back to its source (root-cause-tracing.md).
2. Pattern: find similar working code, read the reference fully, list every difference, understand dependencies.
3. Hypothesis: state one ("X is the cause because Y"), change the smallest thing, one variable at a time. Failed = form a NEW hypothesis, do not stack fixes. If you don't know, say so.
4. Implement: write a failing reproduction test first, make ONE fix at the root cause, verify (test passes, nothing else broke, issue resolved).
5. If a fix fails: fewer than 3 tries = back to step 1 with new info. 3 or more = stop and question the architecture with the user.

Never:
- Propose a fix before completing step 1.
- "Just try changing X" or bundle multiple changes.
- Skip the failing test or add "while I'm here" refactors.
- Attempt fix #4 without discussing architecture.
- Skip the process because it seems simple or urgent.

Full guide: superpowers/systematic-debugging/GUIDE.md
