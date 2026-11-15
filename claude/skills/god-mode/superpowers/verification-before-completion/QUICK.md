# Verification before completion quick reference
Core rule: no completion claims without fresh verification evidence; if you did not run the command in this message, you cannot claim it passes.

Steps (before any status claim, satisfaction, commit, push, PR, or next task):
1. IDENTIFY the command that proves the claim.
2. RUN the full command, fresh.
3. READ the full output, check the exit code, count failures.
4. VERIFY the output confirms the claim; if not, state the actual status with evidence.
5. ONLY THEN make the claim, with the evidence.

Never:
- Say "should pass", "probably", "seems to", or express satisfaction ("Done!") before verifying.
- Rely on a previous run, a partial check, or a linter as proof of a build or tests.
- Trust an agent's success report; check the VCS diff.
- Claim a regression test works without red-green: pass, revert the fix, MUST FAIL, restore, pass.
- Claim requirements are met from passing tests alone; re-read the plan and check each line.

Full guide: superpowers/verification-before-completion/GUIDE.md
