#!/usr/bin/env python3
"""One-command installer for god-mode.

    python install.py                 install into ~/.claude
    python install.py --dry-run       show what would change, change nothing
    python install.py --no-agents     skip the optional agents
    python install.py --no-model      don't set "model": "sonnet"
    python install.py --claude-md     also add a short god-mode block to ~/.claude/CLAUDE.md (opt-in)
    python install.py --uninstall     remove the hooks, skill and hook scripts
    python install.py --target DIR    install somewhere other than ~/.claude (testing)

Copies the files from ./claude into the target, then merges the hook entries into settings.json.
Safe to run twice: existing entries are detected and not duplicated, and settings.json is backed up
(settings.json.godmode-backup) before the first change. Your own hooks and settings are left alone.
Standard library only."""
import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAYLOAD = os.path.join(HERE, "claude")
COPY = [("skills/god-mode", True), ("hubs", True), ("agents", False)]  # (folder, required)
HUB_FILES = ["model-advisor.py", "ladder-hook.py", "test-filter-hook.py", "session-log-hook.py"]
MARKERS = ["god-mode/scripts/session-start.sh", "god-mode/scripts/check-handoff.sh"] + ["hubs/" + h for h in HUB_FILES]


def cmd_py(cdir, hub, *args):
    return f'python -I "{cdir}/hubs/{hub}"' + "".join(" " + a for a in args)


def cmd_sh(cdir, script):
    p = f"{cdir}/skills/god-mode/scripts/{script}"
    return f'[ ! -f "{p}" ] || bash "{p}"'


def wanted_hooks(home):  # `home` is the Claude config folder, e.g. C:/Users/you/.claude
    """event -> list of (matcher or None, command, timeout)"""
    return {
        "SessionStart": [(None, cmd_sh(home, "session-start.sh"), 10), (None, cmd_py(home, "model-advisor.py", "track"), 5)],
        "PostModelSwitch": [(None, cmd_py(home, "model-advisor.py", "track"), 5)],
        "UserPromptSubmit": [(None, cmd_py(home, "model-advisor.py"), 5), (None, cmd_py(home, "session-log-hook.py"), 5)],
        "PreToolUse": [("Bash", cmd_py(home, "test-filter-hook.py"), 5)],
        "PostToolUse": [("Bash|Edit|Write|MultiEdit|NotebookEdit|Agent|Task", cmd_py(home, "ladder-hook.py"), 5)],
        "PostToolUseFailure": [("Bash", cmd_py(home, "ladder-hook.py"), 5)],
        "Stop": [(None, cmd_sh(home, "check-handoff.sh"), 20), (None, cmd_py(home, "ladder-hook.py"), 5),
                 (None, cmd_py(home, "session-log-hook.py"), 5)],
    }


def is_ours(command):
    c = command.replace("\\", "/")
    return any(m in c for m in MARKERS)


def has_cmd(entries, command):
    for e in entries:
        for h in e.get("hooks", []):
            if h.get("command", "").replace("\\", "/") == command.replace("\\", "/"):
                return True
    return False


def merge(settings, cdir, want_model):
    added = []
    hooks = settings.setdefault("hooks", {})
    for event, items in wanted_hooks(cdir).items():
        entries = hooks.setdefault(event, [])
        for matcher, command, timeout in items:
            if has_cmd(entries, command):
                continue
            entry = {"hooks": [{"type": "command", "command": command, "timeout": timeout}]}
            if matcher:
                entry = {"matcher": matcher, **entry}
            entries.append(entry)
            added.append(f"{event}: {command.split('/')[-1].strip(chr(34))[:40]}")
    if want_model and "model" not in settings:
        settings["model"] = "sonnet"
        added.append('model: "sonnet"')
    return added


def strip_ours(settings):
    removed = 0
    hooks = settings.get("hooks", {})
    for event in list(hooks):
        kept = []
        for e in hooks[event]:
            inner = [h for h in e.get("hooks", []) if not is_ours(h.get("command", ""))]
            removed += len(e.get("hooks", [])) - len(inner)
            if inner:
                kept.append({**e, "hooks": inner})
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    if not hooks:
        settings.pop("hooks", None)
    return removed


def read_settings(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except ValueError:
        sys.exit(f"ERROR: {path} is not valid JSON. Fix or move it, then run the installer again. Nothing was changed.")


def write_settings(path, settings, dry):
    if dry:
        return
    backup = path + ".godmode-backup"
    if os.path.exists(path) and not os.path.exists(backup):
        shutil.copy2(path, backup)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")


MD_START, MD_END = "<!-- god-mode:start -->", "<!-- god-mode:end -->"
MD_BLOCK = (MD_START + "\n"
            "## God Mode (coding workflow)\n"
            "Use the `god-mode` skill for multi-step coding work: features spanning many files, refactors, unfamiliar or\n"
            "risky code, work that may span sessions, or resuming an unfinished `.godmode/REQUEST.md`. For small, clear\n"
            "changes just do the work and run the tests. I can say `quick` or `full` to override.\n"
            + MD_END + "\n")


def add_claude_md(target, dry):
    """Opt-in (--claude-md): append a short marked block to CLAUDE.md so the skill is picked for multi-step work."""
    path = os.path.join(target, "CLAUDE.md")
    text = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
    if MD_START in text:
        print("CLAUDE.md already has the god-mode block")
        return
    print(("Would append" if dry else "Appended") + f" a short god-mode block to {path}")
    if dry:
        return
    sep = "" if not text else ("\n" if text.endswith("\n") else "\n\n")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text + sep + ("\n" if text else "") + MD_BLOCK)


def remove_claude_md(target, dry):
    path = os.path.join(target, "CLAUDE.md")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    a, b = text.find(MD_START), text.find(MD_END)
    if a < 0 or b < a:
        return
    new = (text[:a].rstrip("\n") + "\n" + text[b + len(MD_END):].lstrip("\n")).strip("\n")
    print(("Would remove" if dry else "Removed") + " the god-mode block from CLAUDE.md")
    if not dry:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new + "\n" if new else "")


def check_requirements():
    problems = []
    if shutil.which("python") is None and shutil.which("python3") is None:
        problems.append("Python was not found on PATH (the hooks call `python`).")
    if shutil.which("bash") is None:
        problems.append("bash was not found on PATH (on Windows, install Git for Windows and use Git Bash).")
    return problems


def install(target, dry, agents, want_model, claude_md=False):
    if not os.path.isdir(PAYLOAD):
        sys.exit(f"ERROR: payload folder not found: {PAYLOAD}")
    base = target.replace("\\", "/")
    settings_path = os.path.join(target, "settings.json")
    settings = read_settings(settings_path)   # fail before copying anything if settings.json is unreadable
    for p in check_requirements():
        print("WARNING:", p)
    copied = 0
    for folder, required in COPY:
        if folder == "agents" and not agents:
            continue
        src = os.path.join(PAYLOAD, folder)
        if not os.path.isdir(src):
            if required:
                sys.exit(f"ERROR: missing payload folder {src}")
            continue
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in files:
                if name.endswith(".pyc"):
                    continue
                rel = os.path.relpath(os.path.join(root, name), PAYLOAD)
                dest = os.path.join(target, rel)
                copied += 1
                if not dry:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(os.path.join(root, name), dest)
    added = merge(settings, base, want_model)
    write_settings(settings_path, settings, dry)
    verb = "Would copy" if dry else "Copied"
    print(f"{verb} {copied} files into {target}")
    print(("Would add" if dry else "Added") + f" {len(added)} settings entries" + (":" if added else " (already installed)"))
    for a in added:
        print("  +", a)
    if claude_md:
        add_claude_md(target, dry)
    if not dry:
        print("\nDone. Start a new Claude Code session to load the hooks.")
        print(f"Your previous settings were saved to {settings_path}.godmode-backup (first run only).")
        print("Privacy: the session log saves every prompt you type to .godmode/SESSION.md in projects that have a")
        print("  .godmode/ folder. Add .godmode/ to .gitignore. GODMODE_NO_SESSION_LOG=1 turns it off.")


def uninstall(target, dry):
    settings_path = os.path.join(target, "settings.json")
    settings = read_settings(settings_path)
    removed = strip_ours(settings)
    write_settings(settings_path, settings, dry)
    print(("Would remove" if dry else "Removed") + f" {removed} hook entries from {settings_path}")
    remove_claude_md(target, dry)
    for rel in ["skills/god-mode"] + ["hubs/" + h for h in HUB_FILES] + ["hubs/test_" + h.replace("-", "_") for h in HUB_FILES] + ["hubs/test_advisor.py"]:
        p = os.path.join(target, rel)
        if os.path.exists(p):
            print(("  would delete " if dry else "  deleted ") + rel)
            if not dry:
                shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    print("Project .godmode/ folders were left alone; delete them yourself if you no longer need them.")


def main():
    ap = argparse.ArgumentParser(description="Install god-mode into ~/.claude")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-agents", action="store_true")
    ap.add_argument("--no-model", action="store_true", help='do not set "model": "sonnet"')
    ap.add_argument("--claude-md", action="store_true",
                    help="also append a short god-mode block to ~/.claude/CLAUDE.md (off by default)")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--target", default=os.path.join(os.path.expanduser("~"), ".claude"))
    a = ap.parse_args()
    target = os.path.abspath(a.target)
    if a.uninstall:
        uninstall(target, a.dry_run)
    else:
        install(target, a.dry_run, not a.no_agents, not a.no_model, a.claude_md)


if __name__ == "__main__":
    main()
