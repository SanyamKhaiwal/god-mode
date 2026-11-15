# Receiving code review quick reference
Core rule: verify before implementing, ask before assuming; technical correctness over social comfort.

Steps:
1. READ all feedback without reacting.
2. UNDERSTAND: restate each requirement in your own words (or ask).
3. VERIFY against the codebase.
4. EVALUATE: is it sound for THIS codebase (breaks anything? reason for current code? works on all platforms/versions? reviewer has full context?).
5. RESPOND with a technical acknowledgment or reasoned pushback.
6. IMPLEMENT one item at a time, testing each: blocking issues first, then simple fixes, then complex ones; verify no regressions.

Never:
- Say "You're absolutely right!", "Great point!", or any performative agreement; restate or just act.
- Implement before verifying.
- Implement part of the feedback when any item is unclear; ask about unclear items first.
- Add an unused "proper" feature: grep for real usage first (YAGNI).
- Override the user's prior decisions silently; stop and discuss with the user.

Full guide: superpowers/receiving-code-review/GUIDE.md
