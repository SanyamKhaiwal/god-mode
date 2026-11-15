# Finishing a development branch quick reference
Core rule: verify tests, detect environment, present options, execute the choice, clean up.

Steps:
1. Run the full test suite. If failing, report and stop; no menu until green.
2. Detect environment (GIT_DIR vs GIT_COMMON, capture WORKTREE_PATH while inside the workspace).
3. Determine the base branch; if unknown, ask and confirm before merging.
4. Present exactly 3 options (normal repo or named branch): 1 merge locally, 2 push and create PR, 3 keep as-is. Detached HEAD: exactly 2 (push as new branch and PR, keep as-is). Wait for the answer.
5. Execute: merge = checkout base, pull, merge, re-run tests on the result, then clean up worktree and `git branch -d`. PR = push -u, create PR, report URL, keep worktree. Keep = report branch and path.
6. Cleanup (merge and confirmed discard only): remove the worktree only if it is under .worktrees/ or worktrees/ (we created it); otherwise leave it.

Never:
- Offer or perform discard unless the user explicitly asks; then require typed 'discard' and show what will be deleted.
- Present the menu with failing tests.
- Merge into an unconfirmed base branch.
- Clean up the worktree for options 2 or 3, or after a failed merged-result test.
- Decide the integration choice for the user.

Full guide: superpowers/finishing-a-development-branch/GUIDE.md
