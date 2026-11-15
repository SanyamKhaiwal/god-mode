"""Hidden check: plugin domains (architecture task). Usage: python -I hidden_plugin.py <repo> <base_repo>
Contract given in the prompt: plugins/<name>/data.csv + plugins/<name>/plugin.json {"search_cols": [...], "output_cols": [...]}
at the repository root (next to data/)."""
import json
import os
import re
import shutil
import subprocess
import sys

REPO, BASE = sys.argv[1], sys.argv[2]
S, BS, PY = os.path.join(REPO, "scripts"), os.path.join(BASE, "scripts"), sys.executable
checks = []
chk = lambda n, ok: checks.append((n, bool(ok)))
cli = lambda cwd, *a: subprocess.run([PY, "search.py", *a], cwd=cwd, capture_output=True, text=True, encoding="utf-8")

pdir = os.path.join(REPO, "plugins", "petshop")
shutil.rmtree(pdir, ignore_errors=True)
os.makedirs(pdir)
with open(os.path.join(pdir, "data.csv"), "w", encoding="utf-8", newline="") as f:
    f.write("Name,Keywords,Advice\nCat Tower,cat climbing fluffy indoor,Place near a window\n"
            "Dog Leash,dog walking outdoor strong,Use a padded handle\nFish Tank,fish aquarium water filter,Cycle the water first\n")
json.dump({"search_cols": ["Name", "Keywords"], "output_cols": ["Name", "Advice"]}, open(os.path.join(pdir, "plugin.json"), "w"))

r = cli(S, "fluffy cat climbing", "--domain", "petshop", "--json")
try:
    res = json.loads(r.stdout).get("results", [])
    chk("plugin domain searchable via --domain", any(x.get("Name") == "Cat Tower" for x in res))
    chk("plugin output_cols respected", res and set(res[0]) >= {"Name", "Advice"} and "Keywords" not in res[0])
except Exception:
    chk("plugin domain searchable via --domain", False); chk("plugin output_cols respected", False)

json.dump({"search_cols": ["Nope"]}, open(os.path.join(pdir, "plugin.json"), "w"))
r = cli(S, "cat", "--domain", "petshop")
chk("invalid plugin.json: clean error, no traceback", r.returncode != 0 and "Traceback" not in r.stderr and r.stderr.strip())
shutil.rmtree(os.path.join(REPO, "plugins", "petshop"), ignore_errors=True)

r = cli(S, "cat", "--domain", "nosuchdomain")
chk("unknown domain still rejected", r.returncode != 0)
diffs = [" ".join(c) for c in (["navigation menu", "--domain", "ux", "--json"], ["minimal dashboard", "--domain", "style"], ["form validation", "--stack", "react"], ["saas", "--design-system"])
         if cli(S, *c).stdout != cli(BS, *c).stdout]
chk(f"built-in domains unchanged (differs: {diffs})", not diffs)
core = open(os.path.join(S, "core.py"), encoding="utf-8").read()
chk("no plugin names hardcoded in core", "petshop" not in core)
p = subprocess.run([PY, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], cwd=S, capture_output=True, text=True, encoding="utf-8")
out = p.stdout + p.stderr
ran = int((re.search(r"Ran (\d+) tests", out) or [0, 0])[1]); f = int((re.search(r"failures=(\d+)", out) or [0, 0])[1]); e = int((re.search(r"errors=(\d+)", out) or [0, 0])[1])
chk(f"suite: no regressions, new tests added (ran {ran}, failures {f}, errors {e})", f == 0 and e == 4 and ran > 154)
for n, ok in checks:
    print(("PASS " if ok else "FAIL ") + n)
print(f"{sum(ok for _, ok in checks)}/{len(checks)}")
