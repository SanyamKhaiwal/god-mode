"""Model advisor: a UserPromptSubmit hook that suggests a cheaper or stronger model for the task.
It never switches models; it only shows a short notice, and only when the signals are clear.
Stdlib only, no model call (runs in ~50 ms).

Hook input (stdin JSON): prompt, session_id, ... (model if Claude Code provides it).
Output: {"systemMessage": "..."} on stdout, or nothing. Always exits 0 so the prompt proceeds.

Evidence (measured 2026-11-12): Sonnet matched Opus on clear features and bug fixes (13/13, 7/7)
at ~50% of the cost; differences appeared only after interruptions (fixed by god-mode's REQUEST.md)."""
import json
import os
import re
import sys
import tempfile

HARD = [
    (r"\b(race condition|deadlock|concurren\w*|thread[- ]?safe\w*|multithread\w*|mutex|atomic)\b", "concurrency"),
    (r"\b(memory leak|use[- ]after[- ]free|segfault|undefined behaviou?r|heap corruption)\b", "low-level memory bug"),
    (r"\b(intermittent\w*|flaky|heisenbug|only sometimes|randomly fail\w*|can'?t reproduce|no idea why)\b", "unclear root cause"),
    (r"\b(security|vulnerab\w*|exploit\w*|injection|xss|csrf|privilege escalation|pen[- ]?test\w*|cryptograph\w*)\b", "security"),
    (r"\b(architect\w*|system design|redesign the|re-architect|distributed|scalab\w*|sharding)\b", "architecture"),
    (r"\b(migrat\w+ (the|all|our)|data migration|schema migration)\b", "migration"),
    (r"\b(numerical|floating[- ]point|precision loss|physics|simulation|solver)\b", "numerics"),
    (r"\b(trace (how|the|every)|investigat\w* (how|why|the|what)|end[- ]to[- ]end (flow|path)|deep[- ]dive|root[- ]cause analysis|how does .{3,60} work across)", "deep investigation"),
    (r"\b(entire codebase|whole (codebase|project|repo)|across all (modules|services))\b", "codebase-wide change"),
]
SIMPLE = re.compile(
    r"\b(rename|typo|spelling|reword|comment|docstring|readme|docs?|format(ting)?|lint|indent\w*|bump|"
    r"version number|add (a )?(unit )?tests? for|add a (flag|option|field|log line)|small|simple|quick|minor)\b", re.I)
HAIKU_OK = re.compile(
    r"\b(rename|typo|spelling|reword|docstring|readme|format(ting)?|lint|indent\w*|bump|version number|"
    r"add (a )?(unit )?tests? for|add (a )?(log line|comment))\b", re.I)
QUESTION = re.compile(r"^\s*(what|why|how|where|which|explain|can you explain|is it|does)\b", re.I)


def _state_file(session_id):
    return os.path.join(tempfile.gettempdir(), f"model-advisor-{session_id}-model")


def track(data):
    """SessionStart (may carry `model`) and PostModelSwitch (`to_model`): remember the session's model."""
    m = data.get("to_model") or data.get("model")
    if isinstance(m, dict):
        m = m.get("id") or m.get("display_name")
    sid = data.get("session_id")
    if m and sid:
        try:
            open(_state_file(sid), "w", encoding="utf-8").write(str(m))
        except OSError:
            pass


def current_model(data):
    m = data.get("model")
    if not m and data.get("session_id"):
        try:
            m = open(_state_file(data["session_id"]), encoding="utf-8").read().strip()
        except OSError:
            m = None
    if isinstance(m, dict):
        m = m.get("id") or m.get("display_name")
    if not m:
        m = os.environ.get("ANTHROPIC_MODEL", "")
    if not m:
        for p in (os.path.join(data.get("cwd") or ".", ".claude", "settings.local.json"),
                  os.path.join(data.get("cwd") or ".", ".claude", "settings.json"),
                  os.path.expanduser("~/.claude/settings.json")):
            try:
                v = json.load(open(p, encoding="utf-8")).get("model")
                if v:
                    m = v
                    break
            except (OSError, ValueError):
                pass
    m = str(m).lower()
    return "opus" if "opus" in m or "fable" in m or m in ("best",) else "haiku" if "haiku" in m else "sonnet" if "sonnet" in m else "unknown"


def classify(prompt):
    hits = [label for pat, label in HARD if re.search(pat, prompt, re.I)]
    if hits:
        return "hard", sorted(set(hits))
    if SIMPLE.search(prompt) or QUESTION.search(prompt) or len(prompt) < 400:
        return "normal", []
    return "normal", []


def already_told(session_id, kind):
    if not session_id:
        return False
    marker = os.path.join(tempfile.gettempdir(), f"model-advisor-{session_id}-{kind}")
    if os.path.exists(marker):
        return True
    try:
        open(marker, "w").close()
    except OSError:
        pass
    return False


def advise(data):
    prompt = str(data.get("prompt", ""))
    if len(prompt.strip()) < 15 or prompt.strip().startswith("/"):
        return None
    model = current_model(data)
    level, why = classify(prompt)
    if level == "hard" and model in ("sonnet", "haiku"):
        if already_told(data.get("session_id"), "up"):
            return None
        return (f"Model advisor: this looks like it needs extra reasoning ({', '.join(why)}). "
                f"Consider a stronger model (`/model opus` or `/model fable`) for this task, then `/model sonnet` afterwards. Your call.")
    if level == "normal" and model == "opus":
        if already_told(data.get("session_id"), "down"):
            return None
        return ("Model advisor: this looks like a standard task. In our small benchmark Sonnet matched Opus on "
                "tasks like this at roughly half the cost: `/model sonnet`. Your call.")
    if (level == "normal" and model == "sonnet" and len(prompt) < 600 and HAIKU_OK.search(prompt)
            and not QUESTION.search(prompt)):
        if already_told(data.get("session_id"), "haiku"):
            return None
        return ("Model advisor: this is a clear, single-purpose change. In our small benchmark Haiku solved 6 of 6 such "
                "tasks at about a tenth of Sonnet's cost: `/model haiku`. If it stalls or the result looks off, "
                "`/model sonnet`. Your call.")
    return None


DESIGN = re.compile(
    r"\b(architect\w*|plugin (system|mechanism|architecture)|extension (system|mechanism|points?)|new subsystem|"
    r"design (a|an|the) (system|api|module|service|schema|data model|architecture|mechanism|framework)|"
    r"(api|schema|data[- ]model|module|package) design|how should (we|i) (structure|design|organi[sz]e)|"
    r"extensib\w+|pluggable)\b", re.I)
BRAINSTORM = os.path.join(os.path.expanduser("~"), ".claude", "skills", "god-mode", "superpowers",
                          "brainstorming", "QUICK.md").replace("\\", "/")


def design_context(prompt):
    """Context for Claude (not shown to the user) when the prompt asks for an open software design."""
    if not DESIGN.search(prompt) or prompt.strip().startswith("/"):
        return None
    return (f"God-mode: this request is an open software design. Before writing a plan or code, read {BRAINSTORM} "
            "and follow it: clarify intent and constraints, compare 2-3 approaches with trade-offs, pick one with a reason. "
            "If nobody can answer questions (headless or told not to wait), record the open questions as assumptions in "
            ".godmode/REQUEST.md and continue. Record the chosen and rejected approaches.")


BUGFIX = re.compile(r"\b(fix(es|ed|ing)?|bug|crash(es|ing)?|regression|broken|traceback|exception|"
                    r"(index|key|type|value|attribute)error|fails? (with|when|on)|doesn'?t work|not working)\b", re.I)
TDD = BRAINSTORM.replace("brainstorming/QUICK.md", "test-driven-development/QUICK.md")


CODE_EVIDENCE = re.compile(
    r"(`[^`]+`|\b\w+\.(py|js|ts|tsx|jsx|java|cpp|cc|c|h|hpp|cs|go|rs|rb|php|swift|kt|sh)\b|\b\w+_\w+\b|\b\w+\(\)|"
    r"\b\w+(Error|Exception)\b|\btraceback\b|\bstack ?trace\b|\b(function|method|class|endpoint|module|script|"
    r"query|api|handler|parser|compiler|build)\b)", re.I)


def bugfix_context(prompt):
    """One line for Claude when the prompt is a bug fix: regression test first. Needs a bug word AND code evidence
    (a file, identifier, error type or code noun), so casual mentions of "fix"/"bug" stay silent."""
    if not BUGFIX.search(prompt) or not CODE_EVIDENCE.search(prompt) or QUESTION.search(prompt) or prompt.strip().startswith("/"):
        return None
    return ("God-mode: this is a bug fix. First reproduce it with a failing test (the regression test), then fix the root "
            f"cause, then show that test passing along with the rest of the suite. Rules: {TDD}")


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    if len(sys.argv) > 1 and sys.argv[1] == "track":
        track(data)
        return
    prompt = str(data.get("prompt", ""))
    if "<task-notification>" in prompt or "SYSTEM NOTIFICATION" in prompt:
        return                                            # background-task events, not something the user typed
    msg = advise(data)
    ctx = " ".join(c for c in (design_context(prompt), bugfix_context(prompt)) if c) or None
    out = {}
    if msg:
        out["systemMessage"] = msg
    if ctx:
        out["hookSpecificOutput"] = {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}
    if out:
        print(json.dumps(out))


if __name__ == "__main__":
    main()
