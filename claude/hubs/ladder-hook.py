"""Escalation-ladder hook for test/build commands (god-mode).

Wired to PostToolUseFailure (Bash), PostToolUse (Bash) and PostToolUse (Edit|Write|MultiEdit).
Measured 2026-11-13: instructions alone were ignored, and tests are often piped (`... | tail`), which hides
the exit code, so failures are detected from the exit code OR the test output itself.

Per session and per command family:
- the first failing run is just observing the problem: no message;
- a later run that still fails after an edit, with no fewer failures, is a failed attempt: escalate
    1st: read god-mode's systematic-debugging guide,  2nd: hand to the Opus `solver` agent,  3rd+: ask the user;
- a run with fewer failures is progress (no message); a passing run resets the family.
Costs nothing unless a test/build run fails after an edit. Stdlib only."""
import json
import os
import re
import sys
import tempfile

TEST_RE = re.compile(
    r"(\bpytest\b|\bunittest\b|\bnpm (run )?test\b|\byarn test\b|\bpnpm test\b|\bjest\b|\bvitest\b|"
    r"\bgo test\b|\bcargo (test|build)\b|\bmvn\b|\bgradlew?\b|\bctest\b|\bdotnet (test|build)\b|"
    r"\bjavac\b|\bjava -cp\b|\bmake\b|\bcmake --build\b|\bbuild\.sh\b|\btox\b|\bgradcheck\.py\b|"
    r"\bgodmode-run\.sh\b|\bxmltest\b|\bmsbuild\b|\bUnrealBuildTool\b|\bBuild\.(bat|sh)\b)", re.I)
COUNT_RES = [  # (regex, how many groups to sum)
    re.compile(r"FAILED \((?:failures=(\d+))?(?:, )?(?:errors=(\d+))?"),          # unittest
    re.compile(r"\b(\d+) failed\b"),                                                # pytest / jest / vitest
    re.compile(r"Failures: (\d+), Errors: (\d+)"),                                  # JUnit / Maven
    re.compile(r"\bFail (\d+)\b"),                                                  # tinyxml2-style "Pass N, Fail M"
    re.compile(r"\bFAIL: (\d+)\b"),
]
BUILD_ERR = re.compile(r"(\berror C\d{4}\b|\berror: |\bBUILD FAILED\b|\bCOMPILATION ERROR\b|\bfatal error\b)", re.I)
QUICK = os.path.join(os.path.expanduser("~"), ".claude", "skills", "god-mode", "superpowers").replace("\\", "/")
GUIDE = QUICK + "/systematic-debugging/QUICK.md"


def family(cmd):
    m = TEST_RE.search(cmd)
    return (m.group(1).lower() + "|" + re.sub(r"\s+", " ", cmd[m.end():m.end() + 40]).strip()) if m else ""


def failures(text, exit_failed):
    """Number of failures this run shows (0 = passed)."""
    n = 0
    for rx in COUNT_RES:
        for m in rx.finditer(text):
            n = max(n, sum(int(g) for g in m.groups() if g))
    if n == 0:
        n = len(BUILD_ERR.findall(text))
    if n == 0 and exit_failed:
        n = 1
    return n


def state_path(sid):
    return os.path.join(tempfile.gettempdir(), f"godmode-ladder-{sid or 'nosession'}.json")


def load(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def rung(k, cmd, n):
    where = f"`{cmd[:110]}` still shows {n} failure(s) after your last edit"
    if k == 1:
        return (f"GOD-MODE LADDER, failed attempt 1: {where}. Before the next attempt, read {GUIDE} and follow it: "
                "reproduce, trace the failure to its root cause, test one hypothesis at a time. No guess-fixes. "
                "(If these exact failures also fail on the untouched base commit, they are pre-existing: ignore this.)")
    if k == 2:
        return (f"GOD-MODE LADDER, failed attempt 2: {where}. Don't attempt a third fix yourself: hand the problem to the "
                "`solver` agent (Opus) with the goal, this failing output, and your debugging notes (what you traced, "
                "what you ruled out). If no `solver` agent exists, recommend `/model opus` to the user. "
                "(Ignore if the failures are pre-existing on the base commit.)")
    return (f"GOD-MODE LADDER, failed attempt {k}: {where}. Stop and ask the user, with the dead ends summarized.")


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    path = state_path(data.get("session_id"))
    st = load(path)
    tool, event = data.get("tool_name"), data.get("hook_event_name")
    if event == "Stop":
        # verification-before-completion: code was edited after the last test/build run of this session.
        if data.get("stop_hook_active") or not st.get("_edited") or st.get("_stop_warned"):
            return
        if not any(not k.startswith("_") for k in st):
            return                                        # no test/build command seen: nothing to re-run
        st["_stop_warned"] = True
        json.dump(st, open(path, "w", encoding="utf-8"))
        print(json.dumps({"decision": "block", "reason":
              "God-mode verification: code was edited after the last test/build run in this session. Re-run the "
              "tests/build now and report the actual result (no \"should work\"). If the edit can't affect them, say so in one line. Then stop."}))
        return
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        fp = str((data.get("tool_input") or {}).get("file_path", "")).replace("\\", "/").lower()
        if "/.godmode/" in fp or fp.endswith((".md", ".txt", ".rst")):
            return                                        # ledger and docs edits are not code attempts
        st["_edited"] = True
        st.pop("_stop_warned", None)
        json.dump(st, open(path, "w", encoding="utf-8"))
        return
    if tool in ("Agent", "Task"):
        if event == "PostToolUse" and str((data.get("tool_input") or {}).get("subagent_type", "")).lower() == "reviewer":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext":
                  "God-mode, receiving review: before changing anything, check each finding against the code. Fix the ones that are "
                  "real, push back (with the evidence) on the ones that are wrong or out of scope, and never apply a suggestion you "
                  f"haven't verified. Rules: {QUICK}/receiving-code-review/QUICK.md"}}))
        return
    if tool != "Bash":
        return
    cmd = str((data.get("tool_input") or {}).get("command", ""))
    fam = family(cmd)
    if not fam:
        return
    if event == "PostToolUseFailure":
        if data.get("is_interrupt"):
            return
        n = failures(str(data.get("error", "")), True)
    elif event == "PostToolUse":
        resp = data.get("tool_response") or {}
        n = failures(f"{resp.get('stdout', '')}\n{resp.get('stderr', '')}", False)
    else:
        return
    edited = st.pop("_edited", False)
    fs = st.get(fam, {"seen": False, "last": 0, "k": 0})
    msg = None
    if n == 0:
        fs = {"seen": True, "last": 0, "k": 0}
    elif not fs["seen"] or fs["last"] == 0:
        fs.update(seen=True, last=n)                      # first sight of the problem: just observing
    elif edited and n >= fs["last"]:
        fs["k"] += 1
        msg = rung(fs["k"], cmd, n)
    fs["last"] = n
    st[fam] = fs
    json.dump(st, open(path, "w", encoding="utf-8"))
    if msg:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": msg}}))


if __name__ == "__main__":
    main()
