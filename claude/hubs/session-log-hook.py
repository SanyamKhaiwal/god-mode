"""Session log: a hook that writes the conversation's state to disk, at no model cost.

  UserPromptSubmit  -> appends the user's prompt verbatim to <project>/.godmode/SESSION.md
  Stop              -> appends the assistant's final message plus a digest of what it did that turn
                       (files edited, commands run) taken from the transcript
  python session-log-hook.py tail [N]  -> prints the last N lines (default 60), for SessionStart

Only active in projects that already have a .godmode/ folder (the requirements ledger creates it), so it
never writes into unrelated projects. Disable with GODMODE_NO_SESSION_LOG=1. Stdlib only; always exits 0.
SESSION.md is capped (~120 KB): older content moves to .godmode/archive/SESSION-<timestamp>.md."""
import json
import os
import sys
import time

MAX_BYTES = 120_000
PROMPT_MAX = 4000
REPLY_MAX = 1500


def _dir(data):
    base = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    d = os.path.join(base, ".godmode")
    return d if os.path.isdir(d) else None


def _append(d, text):
    path = os.path.join(d, "SESSION.md")
    try:
        if os.path.exists(path) and os.path.getsize(path) > MAX_BYTES:
            arch = os.path.join(d, "archive")
            os.makedirs(arch, exist_ok=True)
            os.replace(path, os.path.join(arch, "SESSION-" + time.strftime("%Y%m%d-%H%M%S") + ".md"))
        new = not os.path.exists(path)
        with open(path, "a", encoding="utf-8") as f:
            if new:
                f.write("# Session log (written by a hook, not by the model)\n"
                        "Every user prompt verbatim, and what the assistant did each turn.\n\n")
            f.write(text)
    except OSError:
        pass


def _clip(s, n):
    s = (s or "").strip()
    return s if len(s) <= n else s[:n] + " ...[cut]"


def log_prompt(data):
    prompt = str(data.get("prompt", ""))
    if not prompt.strip() or "<task-notification>" in prompt or "SYSTEM NOTIFICATION" in prompt:
        return
    d = _dir(data)
    if d:
        _append(d, f"## {time.strftime('%Y-%m-%d %H:%M')} USER\n{_clip(prompt, PROMPT_MAX)}\n\n")


def turn_digest(path):
    """Files edited and commands run since the last real user message in the transcript."""
    edited, cmds = [], []
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return edited, cmds
    events = []
    for l in lines:
        try:
            events.append(json.loads(l))
        except ValueError:
            pass
    start = 0
    for i, e in enumerate(events):
        if e.get("type") == "user" and not e.get("isSidechain"):
            c = (e.get("message") or {}).get("content")
            has_result = isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c)
            if not has_result:
                start = i
    for e in events[start:]:
        if e.get("type") != "assistant" or e.get("isSidechain"):
            continue
        c = (e.get("message") or {}).get("content")
        for b in c if isinstance(c, list) else []:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            inp = b.get("input") or {}
            if b.get("name") in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
                p = inp.get("file_path") or inp.get("notebook_path")
                if p and p not in edited:
                    edited.append(p)
            elif b.get("name") == "Bash" and inp.get("command"):
                cmds.append(" ".join(str(inp["command"]).split())[:90])
    return edited, cmds


def log_stop(data):
    if data.get("stop_hook_active"):
        return
    d = _dir(data)
    if not d:
        return
    edited, cmds = turn_digest(data.get("transcript_path") or "")
    parts = [f"### {time.strftime('%H:%M')} ASSISTANT\n{_clip(data.get('last_assistant_message'), REPLY_MAX)}"]
    if edited:
        parts.append("Edited: " + ", ".join(os.path.basename(p) for p in edited[:12]) + (" ..." if len(edited) > 12 else ""))
    if cmds:
        parts.append(f"Commands ({len(cmds)}): " + " | ".join(cmds[:5]) + (" ..." if len(cmds) > 5 else ""))
    _append(d, "\n".join(parts) + "\n\n")


def tail(n, base):
    path = os.path.join(base, ".godmode", "SESSION.md")
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return ""
    return "\n".join(lines[-n:])


def main():
    if os.environ.get("GODMODE_NO_SESSION_LOG") == "1":
        return
    if len(sys.argv) > 1 and sys.argv[1] == "tail":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        out = tail(n, os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        if out:
            print("----- .godmode/SESSION.md (last %d lines: what was asked and done) -----\n%s" % (n, out))
        return
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    ev = data.get("hook_event_name")
    if ev == "UserPromptSubmit":
        log_prompt(data)
    elif ev == "Stop":
        log_stop(data)


if __name__ == "__main__":
    main()
