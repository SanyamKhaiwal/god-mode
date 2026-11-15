# Dispatching parallel agents quick reference
Core rule: one agent per independent problem domain, working concurrently, each with exactly the context it needs and none of yours.

Use when: 2+ failures or tasks with different root causes, understandable alone, no shared state. Not when failures are related, need whole-system state, or agents would interfere.

Steps:
1. Group the problems into independent domains (one test file or subsystem each).
2. Write a focused prompt per agent: specific scope, clear goal, constraints (e.g. don't change other code), expected output.
3. Dispatch all agents in the same response (multiple calls in one response = parallel).
4. When they return: read each summary, check the fixes don't conflict, run the full suite, integrate.

Prompts must be focused, self-contained (paste error messages and test names), and specific about what to return.

Never:
- Give a broad prompt ("fix all the tests").
- Omit context (error messages, file, test names).
- Dispatch agents that share state or edit the same files.
- Skip the conflict check and full test run after integration.

Full guide: superpowers/dispatching-parallel-agents/GUIDE.md
