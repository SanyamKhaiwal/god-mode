"""Hidden acceptance check for the --explain task (never shown to the runs).
Usage: python -I hidden-explain.py <project_root> <base_root>"""
import json, subprocess, sys
root, base = sys.argv[1], sys.argv[2]
def run(r, *a):
    p = subprocess.run([sys.executable, "search.py", *a], cwd=f"{r}/scripts", capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout, p.stderr
checks = []
def chk(name, ok): checks.append((name, bool(ok)))
# 1 json domain
rc, out, _ = run(root, "dashboard analytics", "--domain", "style", "--json", "--explain")
try:
    d = json.loads(out); res = d.get("results", [])
    chk("json domain: results present", len(res) > 0)
    chk("json domain: score is number, 2dp", all(isinstance(x.get("score"), (int, float)) and round(x["score"], 2) == x["score"] for x in res))
    chk("json domain: matched_terms list", all(isinstance(x.get("matched_terms"), list) for x in res))
except Exception as e:
    chk(f"json domain parse ({e})", False)
# 2 text domain
rc, out, _ = run(root, "dashboard analytics", "--domain", "style", "--explain")
chk("text domain: 'score: X.XX (matched: ...)' line", any(l.strip().startswith("score: ") and "(matched:" in l for l in out.splitlines()))
# 3 stack json
rc, out, _ = run(root, "form validation", "--stack", "react", "--json", "--explain")
try:
    res = json.loads(out).get("results", [])
    chk("json stack: score+matched_terms", len(res) > 0 and all("score" in x and "matched_terms" in x for x in res))
except Exception as e:
    chk(f"json stack parse ({e})", False)
# 4 design-system ignores --explain with stderr warning
rc1, out1, err1 = run(root, "fintech dashboard", "--design-system", "--explain")
rc2, out2, err2 = run(root, "fintech dashboard", "--design-system")
chk("design-system: stdout unchanged by --explain", out1 == out2)
chk("design-system: one-line stderr warning", len([l for l in err1.splitlines() if l.strip()]) == 1 and not err2.strip())
# 5 byte-identical without --explain vs base
for args in (["dashboard analytics", "--domain", "style"], ["dashboard analytics", "--domain", "style", "--json"], ["form validation", "--stack", "react"], ["saas", "--design-system"]):
    chk(f"unchanged vs base: {' '.join(args[1:]) or args[0]}", run(root, *args)[1] == run(base, *args)[1])
for n, ok in checks: print(("PASS " if ok else "FAIL ") + n)
print(f"{sum(ok for _, ok in checks)}/{len(checks)}")
