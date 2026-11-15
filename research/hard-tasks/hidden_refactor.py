"""Hidden check for H2 (split core.py into a package). Usage: python -I hidden_refactor.py <repo> <base_repo>"""
import json
import os
import re
import subprocess
import sys

REPO, BASE = sys.argv[1], sys.argv[2]
S, BS = os.path.join(REPO, "scripts"), os.path.join(BASE, "scripts")
PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))
checks = []


def chk(name, ok):
    checks.append((name, bool(ok)))


def py(code, cwd):
    return subprocess.run([PY, "-c", code], cwd=cwd, capture_output=True, text=True, encoding="utf-8")


# 1. structure
core_lines = sum(1 for _ in open(os.path.join(S, "core.py"), encoding="utf-8"))
chk(f"core.py is a thin facade (<=150 lines, now {core_lines})", core_lines <= 150)
changed = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout
new_py = [l[3:].strip() for l in changed.splitlines() if l.startswith("??") and l.strip().endswith(".py") and "/tests/" not in l and "\\tests\\" not in l]
sizes = {f: sum(1 for _ in open(os.path.join(REPO, f), encoding="utf-8")) for f in new_py}
chk(f"split into >=4 new modules (found {len(sizes)})", len(sizes) >= 4)
chk(f"no new module over 400 lines (max {max(sizes.values(), default=0)})", sizes and max(sizes.values()) <= 400)

# 2. every name core.py had (public and private) still works as core.<name>
names = json.load(open(os.path.join(HERE, "core_names.json"), encoding="utf-8"))
r = py("import sys,json; sys.path.insert(0,'.'); import core; n=json.loads(sys.stdin.read()) if False else None;"
       f"names={names!r}; print(json.dumps([x for x in names if not hasattr(core, x)]))", S)
missing = json.loads(r.stdout.strip() or '["<import failed>"]') if r.returncode == 0 else ["<import failed: " + r.stderr[-200:] + ">"]
chk(f"all {len(names)} former core names still available (missing: {missing[:5]})", not missing)

# 3. shared state: the cache core exposes is the one the search code actually uses
r = py("import sys; sys.path.insert(0,'.'); import core; core._bm25_cache.clear(); core.search('mobile navigation menu','ux',3);"
       "print(len(core._bm25_cache) > 0)", S)
chk("core._bm25_cache is the live cache used by search()", r.stdout.strip().endswith("True"))

# 4. every new module imports on its own (no circular-import traps)
bad = []
for f in sizes:
    mod_dir, mod_file = os.path.split(os.path.join(REPO, f))
    rel = os.path.relpath(os.path.join(REPO, f), S).replace("\\", "/")
    modname = rel[:-3].replace("/", ".")
    r = py(f"import sys; sys.path.insert(0,'.'); import importlib; importlib.import_module({modname!r})", S)
    if r.returncode != 0:
        bad.append(modname)
chk(f"each new module imports standalone (failed: {bad[:4]})", not bad)

# 5. behaviour: CLI output byte-identical to the base for representative commands
cmds = [["minimal dashboard", "--domain", "style"], ["navigation menu", "--domain", "ux", "--json"],
        ["form validation", "--stack", "react"], ["react 17 class component", "--stack", "react", "--json"],
        ["saas analytics", "--design-system"], ["fintech", "--design-system", "-f", "markdown"]]
diff = []
for c in cmds:
    a = subprocess.run([PY, "search.py", *c], cwd=S, capture_output=True, text=True, encoding="utf-8").stdout
    b = subprocess.run([PY, "search.py", *c], cwd=BS, capture_output=True, text=True, encoding="utf-8").stdout
    if a != b:
        diff.append(" ".join(c[1:]) or c[0])
chk(f"CLI output identical to the base (differs: {diff})", not diff)

# 6. test suite unchanged
p = subprocess.run([PY, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], cwd=S, capture_output=True, text=True, encoding="utf-8")
out = p.stdout + p.stderr
ran = int((re.search(r"Ran (\d+) tests", out) or [0, 0])[1]); f = int((re.search(r"failures=(\d+)", out) or [0, 0])[1]); e = int((re.search(r"errors=(\d+)", out) or [0, 0])[1])
chk(f"test suite at baseline (ran {ran}, failures {f}, errors {e}; baseline 154/0/4)", ran >= 154 and f == 0 and e == 4)
tests_changed = [l for l in changed.splitlines() if "/tests/" in l and not l.startswith("??")]
chk("existing tests not modified", not tests_changed)

for n, ok in checks:
    print(("PASS " if ok else "FAIL ") + n)
print(f"{sum(ok for _, ok in checks)}/{len(checks)}")
