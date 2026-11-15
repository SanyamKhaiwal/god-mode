"""SessionStart context for the resume test: prints the ledger (and, with 'log', the tail of the session log)."""
import os, subprocess, sys
d = os.getcwd()
r = os.path.join(d, ".godmode", "REQUEST.md")
if os.path.exists(r):
    print("=== OPEN TASK: .godmode/REQUEST.md ===\n" + open(r, encoding="utf-8").read())
if "log" in sys.argv:
    out = subprocess.run([sys.executable, "-I", "<HOME>/.claude/hubs/session-log-hook.py", "tail", "80"],
                         capture_output=True, text=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=d)).stdout
    print(out)
