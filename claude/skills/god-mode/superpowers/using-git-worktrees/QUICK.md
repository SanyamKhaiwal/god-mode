# Using git worktrees quick reference
Core rule: detect existing isolation first, then use native tools, then fall back to git; never fight the harness.

Steps:
0. Detect: compare GIT_DIR and GIT_COMMON (git rev-parse --git-dir / --git-common-dir). Different and not a submodule = already in a worktree: skip to step 2. Else ask consent unless the user already stated a preference; if declined, work in place.
1a. Use a native worktree tool if you have one (EnterWorktree, /worktree, --worktree).
1b. Else `git worktree add "$LOCATION/$BRANCH" -b "$BRANCH"`. Directory: user preference, else existing .worktrees (wins) or worktrees, else .worktrees/. Verify it is git-ignored (`git check-ignore`); if not, add to .gitignore and commit first.
2. Project setup: auto-detect and run it (npm install, cargo build, pip/poetry, go mod download).
3. Run the tests for a clean baseline; report failures and ask before proceeding.

Never:
- Create a worktree when already in one.
- Create a project-local worktree directory that is not git-ignored.
- Use `git worktree add` when a native tool exists.
- Create a worktree without consent or a stated preference.
- Start work on a failing baseline without asking.
- If the sandbox blocks worktree creation: say so and work in place.

Full guide: superpowers/using-git-worktrees/GUIDE.md
