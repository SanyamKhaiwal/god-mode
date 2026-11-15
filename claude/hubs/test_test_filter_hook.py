"""Tests for test-filter-hook.py. Run: python test_test_filter_hook.py"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("tfh", os.path.join(HERE, "test-filter-hook.py"))
tfh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tfh)

REWRITE = [
    "pytest", "pytest -q tests/test_a.py", "python -m pytest -x tests", "PYTHONPATH=src python -m pytest -q tests",
    "npm test", "npm run test", "npx jest --runInBand", "mvn test", "mvn -q test", "./gradlew test", "ctest --output-on-failure",
    "cargo test", "go test ./...", "dotnet test", "python -m unittest discover -s tests", "make test",
]
UNCHANGED = [
    "pytest | tail -5", "pytest > out.txt", "pytest && git commit -m x", "pytest; rm -rf build", "echo pytest",
    "git status", "ls tests", "pip install pytest", "bash godmode-run.sh S1 pytest", "bash filter-output.sh pytest",
    "pytest $(cat args)", "cat <<EOF\npytest\nEOF", "npm install", "python script.py", "pytest `which x`",
]
ok = 0
total = 0
for c in REWRITE:
    total += 1
    out = tfh.rewrite(c)
    good = bool(out) and "filter-output.sh" in out and c in out.replace("'\"'\"'", "'")
    ok += good
    print(("PASS" if good else "FAIL"), "rewrites ", repr(c))
for c in UNCHANGED:
    total += 1
    good = tfh.rewrite(c) is None
    ok += good
    print(("PASS" if good else "FAIL"), "unchanged", repr(c))

# kill switch
os.environ["GODMODE_NO_FILTER"] = "1"
total += 1
good = tfh.rewrite("pytest") is None
ok += good
print(("PASS" if good else "FAIL"), "GODMODE_NO_FILTER=1 disables")
del os.environ["GODMODE_NO_FILTER"]

# hook protocol: stdout JSON for a test command, silence otherwise, non-Bash ignored
def run(payload):
    return subprocess.run([sys.executable, "-I", os.path.join(HERE, "test-filter-hook.py")], input=json.dumps(payload),
                          capture_output=True, text=True).stdout.strip()

total += 1
o = run({"tool_name": "Bash", "tool_input": {"command": "pytest -q", "description": "d"}})
j = json.loads(o) if o else {}
hs = j.get("hookSpecificOutput", {})
good = "permissionDecision" not in hs and "filter-output.sh" in hs.get("updatedInput", {}).get("command", "") \
    and hs["updatedInput"].get("description") == "d"
ok += good
print(("PASS" if good else "FAIL"), "hook JSON keeps other tool_input fields")
total += 1
good = run({"tool_name": "Bash", "tool_input": {"command": "git status"}}) == "" and \
    run({"tool_name": "Read", "tool_input": {"command": "pytest"}}) == "" and run({"tool_name": "Bash"}) == ""
ok += good
print(("PASS" if good else "FAIL"), "silent for other commands / tools / missing input")

# end to end: the rewritten command keeps the exit code and trims long output
tmp = tempfile.mkdtemp()
script = os.path.join(tmp, "noisy.sh")
open(script, "w", newline="\n").write("for i in $(seq 1 300); do echo line $i; done\necho 'FAILED test_x - AssertionError'\nexit 3\n")
r = subprocess.run(["bash", "-c", f'bash "{tfh.FILTER}" bash -c {tfh.shlex.quote("bash " + script.replace(chr(92), "/"))}'],
                   capture_output=True, text=True)
total += 1
good = r.returncode == 3 and "[filter-output]" in r.stdout and "FAILED test_x" in r.stdout and len(r.stdout.splitlines()) < 150
ok += good
print(("PASS" if good else "FAIL"), "filtered command preserves exit code, trims, keeps failure line")
print(f"{ok}/{total}")
sys.exit(0 if ok == total else 1)
