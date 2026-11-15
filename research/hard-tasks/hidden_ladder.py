"""Hidden check: two-cause ranking bug (IDF formula + synonym word boundary). Usage: python -I hidden_ladder.py <repo>"""
import os
import re
import subprocess
import sys

REPO = sys.argv[1]; S = os.path.join(REPO, "scripts"); PY = sys.executable
checks = []
chk = lambda n, ok: checks.append((n, bool(ok)))
run = lambda code: subprocess.run([PY, "-c", "import sys; sys.path.insert(0,'.'); import core;" + code], cwd=S, capture_output=True, text=True, encoding="utf-8").stdout.strip()

chk("cause 1 fixed: IDF never negative", run("b=core.BM25(); b.fit(['dash min','dash dark','dash modern','glass']); print(min(b.idf.values())>=0)").endswith("True"))
chk("cause 2 fixed: synonyms only match whole words ('navigation' unchanged)", run("print(core._normalize('navigation navbar nav'))") == "navigation navbar navigation")
diff = chr(10).join(l for l in subprocess.run(["git", "-C", REPO, "diff", "-U0", "HEAD", "--", "scripts/core.py"], capture_output=True, text=True).stdout.splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---")))
chk("thresholds / stopwords / synonym table untouched", not re.search(r"^[+-]\s*(_DOMAIN_SCORE_FLOORS|_SEARCH_THRESHOLDS|_STACK_THRESHOLD|_STOPWORDS|_SYNONYMS)\s*=|^[+-]\s*\"[\w&/-]+\":\s*\"[\w &]+\",?$", diff, re.M))
names = subprocess.run(["git", "-C", REPO, "diff", "--name-only", "HEAD"], capture_output=True, text=True).stdout
tdel = [l for l in subprocess.run(["git", "-C", REPO, "diff", "-U0", "HEAD", "--", "scripts/tests"], capture_output=True, text=True).stdout.splitlines() if l.startswith("-") and not l.startswith("---")]
chk(f"data untouched, existing tests only added to ({len(tdel)} test lines removed/changed)", not any(l.startswith("data/") for l in names.split()) and not tdel)
p = subprocess.run([PY, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], cwd=S, capture_output=True, text=True, encoding="utf-8")
out = p.stdout + p.stderr
f = int((re.search(r"failures=(\d+)", out) or [0, 0])[1]); e = int((re.search(r"errors=(\d+)", out) or [0, 0])[1])
chk(f"suite back to baseline (failures {f}, errors {e})", f == 0 and e == 4)
for n, ok in checks:
    print(("PASS " if ok else "FAIL ") + n)
print(f"{sum(ok for _, ok in checks)}/{len(checks)}")
