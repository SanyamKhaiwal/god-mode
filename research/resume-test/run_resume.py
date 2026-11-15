"""Resume test. Usage: python run_resume.py <arm> <rep>   arm: A (nothing) | B (ledger) | C (ledger + session-log hook)
Session 1: task, stop halfway. Session 1 (continued): mid-session amendment. Session 2 (fresh): 'continue'.
Only files carry over. Score with hidden_amend.py."""
import json, os, shutil, subprocess, sys
arm, rep = sys.argv[1], sys.argv[2]
H = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
D = f"<WORKDIR>/resume-runs2/{arm}{rep}"
shutil.rmtree(D, ignore_errors=True); os.makedirs(os.path.dirname(D), exist_ok=True)
subprocess.run(["git", "clone", "-q", "<WORKDIR>/godmode-big-test", D], check=True)
subprocess.run(["git", "-C", D, "checkout", "-q", "4ad5748"], check=True)
for k, v in (("user.email", "t@t"), ("user.name", "t")):
    subprocess.run(["git", "-C", D, "config", k, v], check=True)
os.makedirs(f"{D}/.claude", exist_ok=True)
hooks = {}
if arm in ("B", "C", "D"):
    os.makedirs(f"{D}/.godmode", exist_ok=True)
    ctx = f'python -I "{H}/ctx.py"' + (" log" if arm in ("C", "D") else "")
    hooks["SessionStart"] = [{"hooks": [{"type": "command", "command": ctx}]}]
if arm in ("C", "D"):
    cmd = 'python -I "<HOME>/.claude/hubs/session-log-hook.py"'
    hooks["UserPromptSubmit"] = [{"hooks": [{"type": "command", "command": cmd}]}]
    hooks["Stop"] = [{"hooks": [{"type": "command", "command": cmd}]}]
os.environ["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
json.dump({"hooks": hooks, "autoMemoryEnabled": False}, open(f"{D}/.claude/settings.json", "w"))
EXPLAIN = open(f"{H}/explain_task.txt", encoding="utf-8").read()
LEDGER = ("\n\nKeep a requirements ledger: before your first edit write .godmode/REQUEST.md containing the request verbatim "
          "and a numbered checklist of every requirement (- [ ] 1. ...). Update it whenever I change or add a requirement, "
          "and tick items as you finish them.") if arm in ("B", "C") else ""
STATE = ("\n\nEnd every reply with a short block headed STATE: the overall goal, every requirement I have stated so far "
         "(including changes I made later), what is done, what is still open, and decisions made.") if arm == "D" else ""
P1 = (EXPLAIN + LEDGER + STATE + "\n\nThe plan is pre-approved: proceed without waiting for approval. IMPORTANT for this test: once roughly half of "
      "the work is done (for example after the core.py changes, before the CLI wiring and tests), stop and end your turn, as if the session were interrupted.")
P2 = ("One more thing from me, for the whole --explain feature: scores must be shown with 3 decimals instead of 2 (JSON values "
      "rounded to 3 decimals; text line `score: X.XXX (matched: ...)`), and matched_terms must be sorted alphabetically. "
      "Do no more implementation now: just make sure this is recorded wherever you keep track of the task, then end your turn." + (" Include it in your STATE block." if arm == "D" else ""))
P3 = "Continue where the previous session left off and finish the task."
TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "TodoWrite", "Bash"]
DENY = ["Bash(pip *)", "Bash(python -m pip*)"]
def call(p, extra, tag):
    r = subprocess.run(["claude", "-p", p, "--model", "sonnet", "--output-format", "json", "--setting-sources", "project",
                        "--allowedTools", *TOOLS, "--disallowedTools", *DENY, *extra], cwd=D, capture_output=True, text=True,
                       encoding="utf-8", timeout=2400)
    try: j = json.loads(r.stdout)
    except ValueError: j = {}
    open(f"{H}/logs2/{arm}{rep}-{tag}.json", "w", encoding="utf-8").write(r.stdout)
    return j
os.makedirs(f"{H}/logs2", exist_ok=True)
j1 = call(P1, [], "s1")
j2 = call(P2, ["--resume", j1.get("session_id", "")], "s1b")
j3 = call(P3, [], "s2")
cost = sum((j.get("total_cost_usd") or 0) for j in (j1, j2, j3))
s = subprocess.run([sys.executable, "-I", f"{H}/hidden_amend.py", D, "<WORKDIR>/p1-base"], capture_output=True, text=True, encoding="utf-8").stdout
open(f"{H}/logs2/{arm}{rep}.score.txt", "w", encoding="utf-8").write(s + f"cost ${cost:.2f}\n")
print(arm, rep, s.strip().splitlines()[-1], f"${cost:.2f}")
