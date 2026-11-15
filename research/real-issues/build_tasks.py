"""Build SWE-bench-style tasks from real merged fixes. Usage: python build_tasks.py repo#pr [repo#pr ...]
For each: task folder <WORKDIR>/real-tasks/<id>/ with base/ (source tree at the pre-fix commit, fresh git history),
hidden/ (the maintainers' test files from the fix commit), meta.json (issue text, F2P / P2P test ids, how to run)."""
import json, os, re, shutil, subprocess, sys
REPOS = "<WORKDIR>/test-repos/real"
OUT = "<WORKDIR>/real-tasks"
def sh(cmd, cwd=None, env=None, timeout=900):
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return p.returncode, p.stdout, p.stderr
def gh(*a):
    rc, o, e = sh(["gh", *a])
    if rc: raise RuntimeError(e[:200])
    return o
def run_tests(tree, files):
    pp = os.path.join(tree, "src") if os.path.isdir(os.path.join(tree, "src")) else tree
    env = dict(os.environ, PYTHONPATH=pp, PYTHONDONTWRITEBYTECODE="1")
    rc, o, e = sh([sys.executable, "-m", "pytest", "-q", "--tb=no", "-rA", "-p", "no:cacheprovider", *files], cwd=tree, env=env, timeout=600)
    res = {}
    for l in (o + e).splitlines():
        m = re.match(r"(PASSED|FAILED|ERROR) (\S+)", l)
        if m: res[m.group(2)] = m.group(1)
    return res, (o + e)[-300:]
for spec in sys.argv[1:]:
    repo, pr = spec.split("#"); name = repo.split("/")[1]; tid = f"{name}-{pr}"
    tdir = os.path.join(OUT, tid)
    try:
        info = json.loads(gh("pr", "view", pr, "-R", repo, "--json", "title,body,mergeCommit,files,closingIssuesReferences,baseRefOid"))
        issue = json.loads(gh("issue", "view", str(info["closingIssuesReferences"][0]["number"]), "-R", repo, "--json", "title,body"))
        rdir = os.path.join(REPOS, name)
        if not os.path.isdir(rdir):
            os.makedirs(REPOS, exist_ok=True)
            rc, _, e = sh(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", f"https://github.com/{repo}.git", rdir])
            if rc: raise RuntimeError("clone: " + e[:150])
        merge = info["mergeCommit"]["oid"]
        sh(["git", "fetch", "-q", "origin", merge], cwd=rdir)
        rc, o, e = sh(["git", "rev-parse", merge + "^"], cwd=rdir)
        if rc: raise RuntimeError("no parent: " + e[:100])
        base = o.strip()
        files = [f["path"] for f in info["files"]]
        tests = [f for f in files if "test" in f.lower() and f.endswith(".py")]
        srcs = [f for f in files if f.endswith(".py") and f not in tests]
        shutil.rmtree(tdir, ignore_errors=True); os.makedirs(tdir)
        # base tree without history
        bdir = os.path.join(tdir, "base"); os.makedirs(bdir)
        rc, _, e = sh(f'git archive {base} | tar -x -C "{bdir}"', cwd=rdir) if False else (0, "", "")
        sh(["git", "worktree", "add", "-f", "--detach", os.path.join(tdir, "_wt_base"), base], cwd=rdir)
        sh(["git", "worktree", "add", "-f", "--detach", os.path.join(tdir, "_wt_fix"), merge], cwd=rdir)
        wb, wf = os.path.join(tdir, "_wt_base"), os.path.join(tdir, "_wt_fix")
        # hidden tests = fix-commit versions
        hid = os.path.join(tdir, "hidden")
        for t in tests:
            os.makedirs(os.path.dirname(os.path.join(hid, t)), exist_ok=True); shutil.copy(os.path.join(wf, t), os.path.join(hid, t))
        # run hidden tests on base (with hidden test files copied in) and on fix
        for t in tests: os.makedirs(os.path.dirname(os.path.join(wb, t)), exist_ok=True); shutil.copy(os.path.join(hid, t), os.path.join(wb, t))
        rb, tail_b = run_tests(wb, tests); rf, tail_f = run_tests(wf, tests)
        f2p = sorted(k for k, v in rf.items() if v == "PASSED" and rb.get(k) != "PASSED")
        p2p = sorted(k for k, v in rf.items() if v == "PASSED" and rb.get(k) == "PASSED")
        # clean base tree: checkout of base minus our copied tests, as a fresh repo
        sh(["git", "checkout", "-q", "--", "."], cwd=wb)
        for item in os.listdir(wb):
            if item == ".git": continue
            s = os.path.join(wb, item); d = os.path.join(bdir, item)
            shutil.copytree(s, d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")) if os.path.isdir(s) else shutil.copy(s, d)
        # remove only files that did not exist at base (tests added by the PR)
        rc, o, _ = sh(["git", "ls-tree", "-r", "--name-only", base], cwd=rdir); inbase = set(o.splitlines())
        for t in tests:
            if t not in inbase and os.path.exists(os.path.join(bdir, t)): os.remove(os.path.join(bdir, t))
        sh(["git", "init", "-q"], cwd=bdir); sh(["git", "add", "-A"], cwd=bdir)
        sh(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base"], cwd=bdir)
        meta = dict(id=tid, repo=repo, pr=int(pr), title=info["title"], issue_title=issue["title"], issue_body=issue["body"], test_files=tests, src_files=srcs,
                    f2p=f2p, p2p=p2p, pythonpath="src" if os.path.isdir(os.path.join(bdir, "src")) else ".", base=base, fix=merge)
        json.dump(meta, open(os.path.join(tdir, "meta.json"), "w", encoding="utf-8"), indent=1)
        for w in (wb, wf): sh(["git", "worktree", "remove", "--force", w], cwd=rdir)
        print(f"{tid:26} F2P {len(f2p):2}  P2P {len(p2p):3}  src-files {len(srcs)}  {'OK' if f2p else 'NO FAIL->PASS (unusable)'}   {issue['title'][:60]}")
        if not f2p: print("      base:", tail_b.strip().splitlines()[-1:], "| fix:", tail_f.strip().splitlines()[-1:])
    except Exception as ex:
        print(f"{tid:26} ERROR {str(ex)[:140]}")
