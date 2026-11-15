"""Checks for the resume test: original --explain checks (minus the 2dp one) + the two mid-session amendments.
Usage: python -I hidden_amend.py <project_root> <base_root>"""
import json, re, subprocess, sys, os
root, base = sys.argv[1], sys.argv[2]
H = os.path.dirname(os.path.abspath(__file__))
def run(r, *a):
    p = subprocess.run([sys.executable, "search.py", *a], cwd=f"{r}/scripts", capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout, p.stderr
checks = []
p = subprocess.run([sys.executable, "-I", os.path.join(H, "..", "hidden-explain.py"), root, base], capture_output=True, text=True, encoding="utf-8")
for l in p.stdout.splitlines():
    m = re.match(r"(PASS|FAIL) (.*)", l)
    if m and "2dp" not in m.group(2):
        checks.append(("orig: " + m.group(2), m.group(1) == "PASS"))
orig = len(checks)
_, out, _ = run(root, "dashboard analytics", "--domain", "style", "--json", "--explain")
try:
    res = json.loads(out).get("results", [])
    sc = [x["score"] for x in res]
    checks.append(("amend1 json: scores rounded to 3 decimals", bool(sc) and all(round(s, 3) == s for s in sc) and any(round(s, 2) != s for s in sc)))
    checks.append(("amend2 json: matched_terms sorted", bool(res) and all(x["matched_terms"] == sorted(x["matched_terms"]) for x in res)))
except Exception:
    checks.append(("amend1 json: scores rounded to 3 decimals", False)); checks.append(("amend2 json: matched_terms sorted", False))
_, out, _ = run(root, "dashboard analytics", "--domain", "style", "--explain")
checks.append(("amend1 text: score: X.XXX (matched: ...)", any(re.match(r"score: \d+\.\d{3} \(matched:", l.strip()) for l in out.splitlines())))
for n, ok in checks: print(("PASS " if ok else "FAIL ") + n)
print(f"{sum(ok for _, ok in checks)}/{len(checks)} amend {sum(ok for n, ok in checks if n.startswith('amend'))}/3")
