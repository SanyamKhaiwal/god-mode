"""Tests for session-log-hook.py. Run: python test_session_log_hook.py"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "session-log-hook.py")
ok = total = 0


def run(payload, args=(), env=None):
    e = dict(os.environ, **(env or {}))
    return subprocess.run([sys.executable, "-I", HOOK, *args], input=json.dumps(payload), capture_output=True,
                          text=True, env=e).stdout


def check(name, good):
    global ok, total
    total += 1
    ok += bool(good)
    print(("PASS" if good else "FAIL"), name)


def proj(godmode=True):
    d = tempfile.mkdtemp()
    if godmode:
        os.makedirs(os.path.join(d, ".godmode"))
    return d


def log(d):
    p = os.path.join(d, ".godmode", "SESSION.md")
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


# prompt logged verbatim, in order
d = proj()
run({"hook_event_name": "UserPromptSubmit", "cwd": d, "prompt": "Add --explain. Round scores to 2 decimals."})
run({"hook_event_name": "UserPromptSubmit", "cwd": d, "prompt": "Change of plan: round to 3 decimals instead."})
s = log(d)
check("prompts logged verbatim", "Round scores to 2 decimals." in s and "round to 3 decimals instead." in s)
check("prompts in order", s.index("2 decimals") < s.index("3 decimals"))
check("header written once", s.count("# Session log") == 1)

# no .godmode folder -> nothing written anywhere
d2 = proj(False)
run({"hook_event_name": "UserPromptSubmit", "cwd": d2, "prompt": "hello there"})
check("no .godmode -> no file", not os.path.exists(os.path.join(d2, ".godmode")))

# background notifications ignored
d3 = proj()
run({"hook_event_name": "UserPromptSubmit", "cwd": d3, "prompt": "<task-notification>x</task-notification>"})
check("task notifications not logged", log(d3) == "")

# kill switch
d4 = proj()
run({"hook_event_name": "UserPromptSubmit", "cwd": d4, "prompt": "something"}, env={"GODMODE_NO_SESSION_LOG": "1"})
check("kill switch", log(d4) == "")

# long prompt clipped
d5 = proj()
run({"hook_event_name": "UserPromptSubmit", "cwd": d5, "prompt": "x" * 9000})
check("long prompt clipped", "[cut]" in log(d5) and len(log(d5)) < 4600)

# stop: reply + digest from transcript, only the current turn
d6 = proj()
tr = os.path.join(d6, "t.jsonl")
ev = [
    {"type": "user", "message": {"role": "user", "content": "first request"}},
    {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit", "input": {"file_path": "/p/old.py"}}]}},
    {"type": "user", "message": {"role": "user", "content": "second request"}},
    {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit", "input": {"file_path": "/p/core.py"}},
                                                  {"type": "tool_use", "name": "Bash", "input": {"command": "python -m pytest -q"}}]}},
    {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]}},
    {"type": "assistant", "isSidechain": True, "message": {"content": [{"type": "tool_use", "name": "Edit", "input": {"file_path": "/p/side.py"}}]}},
]
open(tr, "w").write("\n".join(json.dumps(e) for e in ev))
run({"hook_event_name": "Stop", "cwd": d6, "transcript_path": tr, "last_assistant_message": "Done: added the flag."})
s = log(d6)
check("stop logs the final message", "Done: added the flag." in s)
check("stop digest lists this turn's edits only", "Edited: core.py" in s and "old.py" not in s and "side.py" not in s)
check("stop digest lists commands", "Commands (1): python -m pytest -q" in s)

# stop_hook_active -> silent
d7 = proj()
run({"hook_event_name": "Stop", "cwd": d7, "stop_hook_active": True, "last_assistant_message": "again"})
check("stop_hook_active silent", log(d7) == "")

# rotation
d8 = proj()
p = os.path.join(d8, ".godmode", "SESSION.md")
open(p, "w").write("y" * 130_000)
run({"hook_event_name": "UserPromptSubmit", "cwd": d8, "prompt": "after rotation"})
arch = os.path.join(d8, ".godmode", "archive")
check("rotation archives the old log", os.path.isdir(arch) and len(os.listdir(arch)) == 1 and "after rotation" in log(d8) and len(log(d8)) < 2000)

# tail
d9 = proj()
for i in range(40):
    run({"hook_event_name": "UserPromptSubmit", "cwd": d9, "prompt": f"prompt number {i}"})
out = subprocess.run([sys.executable, "-I", HOOK, "tail", "10"], capture_output=True, text=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=d9)).stdout
check("tail prints the last lines", "prompt number 39" in out and "prompt number 0\n" not in out)

# malformed input never crashes
r = subprocess.run([sys.executable, "-I", HOOK], input="not json", capture_output=True, text=True)
check("malformed input is silent", r.returncode == 0 and r.stdout == "")
print(f"{ok}/{total}")
sys.exit(0 if ok == total else 1)
