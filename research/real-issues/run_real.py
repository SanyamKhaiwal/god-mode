"""Real-issue benchmark runner. Usage:
  python run_real.py run   <task-id> <arm>     arms: haiku | sonnet | opus | gm (sonnet + god-mode) | gmhaiku
  python run_real.py score <task-id> <arm>     grade with the maintainers' hidden tests, print one JSON line
  python run_real.py table [arms...]           summary table over all tasks/arms with a result file"""
import glob, json, os, re, shutil, subprocess, sys, time
TASKS = "<WORKDIR>/real-tasks"
RUNS = "<WORKDIR>/real-runs"
LOGS = "<WORKDIR>/real-issues/logs"
os.makedirs(LOGS, exist_ok=True)
ARMS = {
    "haiku": (["--model", "haiku"], "Do not use any skill; work as you normally would."),
    "sonnet": (["--model", "sonnet"], "Do not use any skill; work as you normally would."),
    "opus": (["--model", "opus"], "Do not use any skill; work as you normally would."),
    "gm": (["--model", "sonnet"], "Use the god-mode skill."),
    "gmhaiku": (["--model", "haiku"], "Use the god-mode skill."),
    # spec-hint arms: the issue plus the maintainers' PR description of the intended change
    "haiku-h": (["--model", "haiku"], "Do not use any skill; work as you normally would."),
    "sonnet-h": (["--model", "sonnet"], "Do not use any skill; work as you normally would."),
    "opus-h": (["--model", "opus"], "Do not use any skill; work as you normally would."),
    "gmlite": (["--model", "sonnet"], "Use the god-mode-lite skill."),
    "haiku-adv-h": (["--model", "haiku", "--advisor", "opus"], "Consult the advisor before committing to an approach and before declaring the task done."),
    # Opus writes PLAN.md (read-only on the code), then Haiku executes it
    "plan-haiku": (["--model", "haiku"], "Do not use any skill; work as you normally would."),
}
ALLOWED = ["Read", "Write", "Edit", "Glob", "Grep", "Skill", "Agent", "TodoWrite", "Bash"]
DENY = ["Bash(pip *)", "Bash(python -m pip*)", "Bash(curl *)", "Bash(wget *)", "Bash(gh *)", "Bash(git clone*)", "Bash(git fetch*)", "Bash(git pull*)"]


def sh(cmd, cwd=None, env=None, timeout=900):
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def pytest(tree, files, pythonpath):
    env = dict(os.environ, PYTHONPATH=os.path.join(tree, pythonpath) if pythonpath != "." else tree, PYTHONDONTWRITEBYTECODE="1")
    rc, out = sh([sys.executable, "-m", "pytest", "-q", "--tb=no", "-rA", "-p", "no:cacheprovider", *files], cwd=tree, env=env, timeout=600)
    res = {}
    for l in out.splitlines():
        m = re.match(r"(PASSED|FAILED|ERROR) (\S+)", l)
        if m: res[m.group(2)] = m.group(1)
    return res


def run(tid, arm):
    meta = json.load(open(f"{TASKS}/{tid}/meta.json", encoding="utf-8"))
    d = f"{RUNS}/{tid}-{arm}"
    shutil.rmtree(d, ignore_errors=True); os.makedirs(RUNS, exist_ok=True)
    shutil.copytree(f"{TASKS}/{tid}/base", d)
    margs, armtext = ARMS[arm]
    if arm == 'gmlite':
        shutil.copytree(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'variant', 'god-mode-lite'), f'{d}/.claude/skills/god-mode-lite')
        shutil.copytree('<HOME>/.claude/skills/god-mode/scripts', f'{d}/.claude/skills/god-mode-lite/scripts')
    pp = meta["pythonpath"]
    prompt = (f"Resolve this issue from the project's GitHub tracker. The repository is in the current folder (a Python project).\n\n"
              f"## {meta['issue_title']}\n\n{meta['issue_body']}\n\n"
              f"Make the change in the source code, and add or update tests where appropriate. To run tests: "
              f"`{'PYTHONPATH=' + pp + ' ' if pp != '.' else ''}python -m pytest -q <test files>` (do not install packages and do not use the network). "
              f"The plan is pre-approved: proceed without asking questions and finish the whole task.\n\n{armtext}")
    if arm.endswith("-h"):
        hint = (f"## Maintainer's description of the intended change (pull request: {meta.get('pr_title', '')})\n\n"
                f"{(meta.get('pr_body') or '')[:6000]}\n\n")
        prompt = prompt.replace("Make the change", hint + "Make the change", 1)
    t0 = time.time()

    def call(pr, model_args, log, tools=ALLOWED):
        with open(log, "w", encoding="utf-8") as lf:
            subprocess.run(["claude", "-p", pr, *model_args, "--output-format", "stream-json", "--verbose",
                            "--allowedTools", *tools, "--disallowedTools", *DENY], cwd=d, stdout=lf, stderr=subprocess.STDOUT, timeout=3600)

    if arm == "plan-haiku":
        plan_prompt = (prompt.split("The plan is pre-approved")[0] +
                       "Do NOT change any source or test file. Read the code and write a precise implementation plan to PLAN.md in the repository root: "
                       "the exact files, functions and names to change, every behaviour and edge case the fix must handle, the exact messages or formats the issue implies, "
                       "and how to verify it. Then stop.")
        call(plan_prompt, ["--model", "opus"], f"{LOGS}/{tid}-{arm}.plan.jsonl", ["Read", "Write", "Glob", "Grep", "Bash"])
        prompt = prompt.replace("The plan is pre-approved", "A senior engineer has written an implementation plan in PLAN.md at the repository root: read it first and follow it. The plan is pre-approved", 1)
    call(prompt, margs, f"{LOGS}/{tid}-{arm}.jsonl")
    print(f"{tid}-{arm} done in {time.time() - t0:.0f}s")


def usage(log):
    cost = turns = 0; ms = 0; agents = []; skills = []; seen = False
    if os.path.exists(log.replace('.jsonl', '.plan.jsonl')):
        c2, t2, m2, _, _ = usage(log.replace('.jsonl', '.plan.jsonl')); cost, turns, ms = c2, t2, m2 * 60000
    for l in open(log, encoding="utf-8", errors="replace"):
        try: e = json.loads(l)
        except ValueError: continue
        if e.get("type") == "result" and not seen:
            seen = True; cost += e.get("total_cost_usd") or 0; turns += e.get("num_turns") or 0; ms += e.get("duration_ms") or 0
        if e.get("type") == "assistant" and not e.get("parent_tool_use_id"):
            for b in e["message"]["content"]:
                if b.get("type") == "tool_use" and b["name"] == "Agent": agents.append(b["input"].get("subagent_type"))
                if b.get("type") == "tool_use" and b["name"] == "Skill": skills.append(b["input"].get("skill"))
    return cost, turns, ms / 60000, agents, skills


def score(tid, arm):
    meta = json.load(open(f"{TASKS}/{tid}/meta.json", encoding="utf-8"))
    d = f"{RUNS}/{tid}-{arm}"
    for t in meta["test_files"]:
        os.makedirs(os.path.dirname(f"{d}/{t}"), exist_ok=True); shutil.copy(f"{TASKS}/{tid}/hidden/{t}", f"{d}/{t}")
    res = pytest(d, meta["test_files"], meta["pythonpath"])
    f2p = sum(1 for k in meta["f2p"] if res.get(k) == "PASSED"); p2p_bad = sum(1 for k in meta["p2p"] if res.get(k) != "PASSED")
    cost, turns, mins, agents, skills = usage(f"{LOGS}/{tid}-{arm}.jsonl")
    out = dict(task=tid, arm=arm, f2p=f"{f2p}/{len(meta['f2p'])}", p2p_broken=p2p_bad, success=(f2p == len(meta["f2p"]) and p2p_bad == 0),
               cost=round(cost, 3), turns=turns, minutes=round(mins, 1), agents=agents, skills=skills)
    json.dump(out, open(f"{LOGS}/{tid}-{arm}.score.json", "w"))
    print(json.dumps(out))


def table(arms):
    rows = {}
    for f in glob.glob(f"{LOGS}/*.score.json"):
        r = json.load(open(f)); rows.setdefault(r["task"], {})[r["arm"]] = r
    arms = arms or sorted({a for v in rows.values() for a in v})
    print(f"{'task':24}" + "".join(f"{a:>22}" for a in arms))
    tot = {a: [0, 0.0, 0] for a in arms}
    for t in sorted(rows):
        line = f"{t:24}"
        for a in arms:
            r = rows[t].get(a)
            if r:
                line += f"{('PASS' if r['success'] else 'FAIL') + ' ' + r['f2p'] + ' $' + format(r['cost'], '.2f'):>22}"
                tot[a][0] += r["success"]; tot[a][1] += r["cost"]; tot[a][2] += 1
            else: line += f"{'-':>22}"
        print(line)
    print(f"{'TOTAL passed / cost':24}" + "".join(f"{str(tot[a][0]) + '/' + str(tot[a][2]) + ' $' + format(tot[a][1], '.2f'):>22}" for a in arms))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "run": run(sys.argv[2], sys.argv[3])
    elif cmd == "score": score(sys.argv[2], sys.argv[3])
    elif cmd == "table": table(sys.argv[2:])
