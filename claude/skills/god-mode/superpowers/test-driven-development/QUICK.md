# TDD quick reference
Core rule: no production code without a failing test first; if you did not watch the test fail, you do not know it tests the right thing.

Steps:
1. RED: write one minimal test for one behavior (clear name, real code, mocks only if unavoidable).
2. Verify RED: run it; it must fail (not error) for the expected reason (feature missing, not a typo). Passes = fix the test.
3. GREEN: write the simplest code that passes. No extra options or features.
4. Verify GREEN: run it; the new test and all others pass, output clean.
5. REFACTOR: clean up while staying green; do not add behavior.
6. Repeat for the next behavior. Bug found: write a failing test that reproduces it first.

Never:
- Write production code before a failing test. Code written first: delete it and start over (no keeping it as "reference").
- Skip watching the test fail.
- Fix a bug without a test.
- Test mock behavior or the text of a file; test behavior at your code's boundaries.
- Skip TDD "just this once"; exceptions (prototypes, generated code, config) need the user's permission.

Full guide: superpowers/test-driven-development/GUIDE.md
