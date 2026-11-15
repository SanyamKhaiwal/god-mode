# Brainstorming quick reference
Core rule: no code, scaffolding, or implementation action until a design is presented and the user approves it, however simple the project.

Non-interactive session (headless, or told not to wait): ask nothing; write 2–3 approaches, pick one with a one-line reason, record open questions as assumptions in .godmode/REQUEST.md, continue.

Steps:
1. Explore project context (files, docs, recent commits). If the request spans several independent subsystems, flag it and decompose first.
2. Ask clarifying questions one per message, preferring multiple choice (purpose, constraints, success criteria).
3. Propose 2-3 approaches with trade-offs; lead with your recommendation. YAGNI ruthlessly.
4. Present the design in sections scaled to complexity (architecture, components, data flow, error handling, testing); get approval after each.
5. Write the design doc (docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md unless the user prefers elsewhere) and commit it.
6. Self-review it: placeholders, contradictions, scope, ambiguity; fix inline.
7. Ask the user to review the written spec, then write god-mode's .godmode/PLAN.md.

Never:
- Start implementation before approval.
- Ask more than one question per message.
- Offer the visual companion upfront; only when a question is clearer shown.
- Propose unrelated refactoring.
- Invoke other skills from here; the end state is PLAN.md.

Full guide: superpowers/brainstorming/GUIDE.md
