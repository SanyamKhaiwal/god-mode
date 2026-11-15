"""Self-test for ladder-hook.py. Usage: python -I test_ladder_hook.py"""
import json
import os
import subprocess
import sys
import uuid

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ladder-hook.py")
checks = []


def send(sid, payload):
    payload = {"session_id": sid, **payload}
    out = subprocess.run([sys.executable, "-I", HOOK], input=json.dumps(payload), capture_output=True, text=True).stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else ""


def run_ok(sid, cmd, stdout):   # exit 0 (e.g. piped through tail): PostToolUse with the output
    return send(sid, {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": cmd},
                      "tool_response": {"stdout": stdout, "stderr": ""}})


def run_fail(sid, cmd, err):    # non-zero exit: PostToolUseFailure
    return send(sid, {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash", "tool_input": {"command": cmd},
                      "error": err, "is_interrupt": False})


def edit(sid):
    return send(sid, {"hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_input": {"file_path": "x.py"}})


def chk(name, ok):
    checks.append((name, bool(ok)))


T = 'python -m unittest discover -s tests 2>&1 | tail -5'
s = "t-" + uuid.uuid4().hex
chk("first failing run (piped) is silent: just observing", run_ok(s, T, "Ran 154 tests\nFAILED (failures=12, errors=6)") == "")
edit(s)
a = run_ok(s, T, "Ran 154 tests\nFAILED (failures=12, errors=6)")
chk("piped output: failure after an edit that didn't help -> debugging guide", "failed attempt 1" in a and "systematic-debugging/QUICK.md" in a)
edit(s)
chk("progress (fewer failures) -> no message", run_ok(s, T, "FAILED (failures=3)") == "")
edit(s)
b = run_ok(s, T, "FAILED (failures=3)")
chk("no progress again -> Opus solver", "failed attempt 2" in b and "solver" in b)
chk("rerun without an edit -> no message", run_ok(s, T, "FAILED (failures=3)") == "")
edit(s)
c = run_fail(s, T, "Exit code 1\nFAILED (failures=3)")
chk("exit-code failure counts too -> ask the user", "failed attempt 3" in c and "ask the user" in c)
run_ok(s, T, "Ran 154 tests\nOK")
edit(s)
chk("pass resets the family", run_ok(s, T, "FAILED (failures=1)") == "")

s2 = "t-" + uuid.uuid4().hex
chk("non-test commands ignored", run_fail(s2, "ls nothing", "Exit code 2") == "")
for cmd, out in (("mvn -q test", "Tests run: 10, Failures: 2, Errors: 0"), ("npm test", "Tests: 2 failed, 8 passed"),
                 ("bash build.sh", "Pass 515, Fail 2"), ("javac -d out src/*.java", "Foo.java:3: error: ';' expected")):
    sx = "t-" + uuid.uuid4().hex
    run_ok(sx, cmd, out); edit(sx)
    chk(f"detects failures in `{cmd}` output", "failed attempt 1" in run_ok(sx, cmd, out))
s3 = "t-" + uuid.uuid4().hex
chk("passing output is never a failure", run_ok(s3, "pytest -q", "52 passed in 1.2s") == "" and run_ok(s3, "pytest -q", "52 passed") == "")

# verification-before-completion (Stop), receiving-code-review (reviewer agent), docs edits
def stop(sid, active=False):
    payload = {"session_id": sid, "hook_event_name": "Stop", "stop_hook_active": active}
    out = subprocess.run([sys.executable, "-I", HOOK], input=json.dumps(payload), capture_output=True, text=True).stdout.strip()
    return json.loads(out) if out else {}

s4 = "t-" + uuid.uuid4().hex
chk("Stop: silent when no tests were ever run", (edit(s4), stop(s4))[1] == {})
run_ok(s4, "pytest -q", "5 passed")
chk("Stop: silent when tests ran after the last edit", stop(s4) == {})
edit(s4)
blk = stop(s4)
chk("Stop: blocks once when code was edited after the last test run", blk.get("decision") == "block" and "Re-run" in blk.get("reason", ""))
chk("Stop: does not block twice", stop(s4) == {})
edit(s4)
chk("Stop: respects stop_hook_active", stop(s4, active=True) == {})
s5 = "t-" + uuid.uuid4().hex
run_ok(s5, "pytest -q", "5 passed")
send(s5, {"hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_input": {"file_path": "D:/x/.godmode/REQUEST.md"}})
send(s5, {"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": "README.md"}})
chk("Stop: ledger and docs edits don't count as code edits", stop(s5) == {})
rv = send(s5, {"hook_event_name": "PostToolUse", "tool_name": "Agent", "tool_input": {"subagent_type": "reviewer", "prompt": "x"}})
chk("reviewer result -> receiving-code-review rule", "receiving review" in rv and "receiving-code-review/QUICK.md" in rv)
chk("other agents -> no message", send(s5, {"hook_event_name": "PostToolUse", "tool_name": "Agent", "tool_input": {"subagent_type": "executor"}}) == "")

for n, ok in checks:
    print(("PASS " if ok else "FAIL ") + n)
print(f"{sum(ok for _, ok in checks)}/{len(checks)}")
sys.exit(0 if all(ok for _, ok in checks) else 1)
