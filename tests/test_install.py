import json, os, subprocess, sys, tempfile, shutil
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ok = total = 0
def check(n, g):
    global ok, total; total += 1; ok += bool(g); print("PASS" if g else "FAIL", n)
def run(*a, home):
    env = dict(os.environ, USERPROFILE=home, HOME=home)
    return subprocess.run([sys.executable, f"{REPO}/install.py", *a], capture_output=True, text=True, env=env)
H = tempfile.mkdtemp().replace("\\", "/"); C = H + "/.claude"; os.makedirs(C)
mine = {"model": "opus", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}, "theme": "dark"}
json.dump(mine, open(C + "/settings.json", "w"))
# dry run changes nothing
r = run("--dry-run", home=H)
check("dry-run changes nothing", json.load(open(C + "/settings.json")) == mine and not os.path.exists(C + "/skills") and "Would copy" in r.stdout)
# install
r = run(home=H); s = json.load(open(C + "/settings.json"))
check("install exits 0", r.returncode == 0)
check("user hook and settings preserved", any(h["command"] == "echo mine" for e in s["hooks"]["Stop"] for h in e["hooks"]) and s["theme"] == "dark")
check("existing model not overwritten", s["model"] == "opus")
check("all 7 events present", {"SessionStart","PostModelSwitch","UserPromptSubmit","PreToolUse","PostToolUse","PostToolUseFailure","Stop"} <= set(s["hooks"]))
check("backup created", os.path.exists(C + "/settings.json.godmode-backup"))
check("files copied", all(os.path.exists(C + p) for p in ["/skills/god-mode/SKILL.md", "/hubs/model-advisor.py", "/hubs/session-log-hook.py", "/agents/planner.md"]))
check("no pycache copied", not any("__pycache__" in r_ for r_, _, _ in os.walk(C)))
# every hook command points at a file that exists
import re
cmds = [h["command"] for ev in s["hooks"].values() for e in ev for h in e["hooks"] if "echo mine" not in h["command"]]
paths = [m for c in cmds for m in re.findall(r'"([^"]+\.(?:py|sh))"', c)]
check("every hook script exists", paths and all(os.path.exists(p) for p in paths))
# idempotent
before = open(C + "/settings.json").read(); r = run(home=H)
check("second run adds nothing", open(C + "/settings.json").read() == before and "already installed" in r.stdout)
# hook scripts really run from the installed location
tests_ok = all(subprocess.run([sys.executable, C + f"/hubs/{t}"], capture_output=True, text=True, env=dict(os.environ, USERPROFILE=H, HOME=H)).returncode == 0
               for t in ["test_ladder_hook.py", "test_test_filter_hook.py", "test_session_log_hook.py"])
check("installed hook tests pass (fake HOME)", tests_ok)
# uninstall
r = run("--uninstall", home=H); s = json.load(open(C + "/settings.json"))
left = [h["command"] for ev in s.get("hooks", {}).values() for e in ev for h in e["hooks"]]
check("uninstall removes ours, keeps the user's hook", left == ["echo mine"])
check("uninstall deletes skill and hook scripts", not os.path.exists(C + "/skills/god-mode") and not os.path.exists(C + "/hubs/model-advisor.py"))
# no-agents / no-model on a fresh home
H2 = tempfile.mkdtemp().replace("\\", "/"); r = run("--no-agents", "--no-model", home=H2); s2 = json.load(open(H2 + "/.claude/settings.json"))
check("--no-agents skips agents, --no-model skips model", not os.path.exists(H2 + "/.claude/agents") and "model" not in s2)
H3 = tempfile.mkdtemp().replace("\\", "/"); r = run(home=H3)
check("fresh install sets model sonnet", json.load(open(H3 + "/.claude/settings.json")).get("model") == "sonnet")
# invalid settings.json: refuse, change nothing
H4 = tempfile.mkdtemp().replace("\\", "/"); os.makedirs(H4 + "/.claude"); open(H4 + "/.claude/settings.json", "w").write("{ not json")
r = run(home=H4)
check("invalid settings.json: error and nothing copied", r.returncode != 0 and not os.path.exists(H4 + "/.claude/skills") and open(H4 + "/.claude/settings.json").read() == "{ not json")
print(f"{ok}/{total}")
