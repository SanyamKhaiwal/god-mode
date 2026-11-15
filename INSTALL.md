# Install god-mode

One command:

```bash
git clone https://github.com/SanyamKhaiwal/god-mode.git
cd god-mode
python install.py
```

Then start a new Claude Code session. That's it.

Needs Python 3 and `bash` (on Windows, Git Bash from Git for Windows). Standard library only, no `pip install`, no network.

## What the installer does

- Copies the skill, the hook scripts and (optionally) the agents into `~/.claude`.
- Merges the hook entries into `~/.claude/settings.json` without touching your own hooks or settings.
- Sets `"model": "sonnet"` only if you have no `model` setting yet.
- Saves your original `settings.json` to `settings.json.godmode-backup` the first time.
- Is safe to run twice: it detects what is already installed and adds nothing.
- Refuses to continue, changing nothing, if your `settings.json` isn't valid JSON.

## Options

```bash
python install.py --dry-run     # show what would change, change nothing
python install.py --no-agents   # skip the optional agents (planner, solver, reviewer, executors, researchers)
python install.py --no-model    # don't set the Sonnet default
python install.py --uninstall   # remove the hooks, the skill and the hook scripts (your own hooks stay)
```

The agents are optional. We found no measured benefit from them (see the README), so `--no-agents` is a reasonable minimal install.

## Check it works

```bash
python ~/.claude/hubs/test_ladder_hook.py        # expect 21/21
python ~/.claude/hubs/test_test_filter_hook.py   # expect 35/35
python ~/.claude/hubs/test_session_log_hook.py   # expect 14/14
python ~/.claude/hubs/test_advisor.py            # expect 35/35
bash ~/.claude/skills/god-mode/scripts/selftest.sh | grep -c FAIL   # expect 0
```

Then, in a project folder, send "fix the IndexError in parser.py". A short test-first note should be added to the conversation. To try resume: create a `.godmode/` folder in the project, ask for a multi-step change, quit, open a new session in the same folder and type "continue".

## How it behaves (read before you rely on it)

- **Nothing switches your model.** The advisor only prints a hint; you run `/model` yourself.
- **The test filter** rewrites plain test commands (`pytest`, `npm test`, `go test`, `mvn test`, `cargo test`, `make test`...) so long output is trimmed. It never approves a command: your permission rules apply to the rewritten command. If you allow only narrow patterns such as `Bash(pytest*)`, the rewritten command will ask for approval. `GODMODE_NO_FILTER=1` turns it off.
- **The session log records every prompt you type**, including anything you paste, in `.godmode/SESSION.md`. Add `.godmode/` to your `.gitignore` and don't paste secrets. It only writes in folders that already have a `.godmode/` folder. `GODMODE_NO_SESSION_LOG=1` turns it off.
- **"Continue" works only** in the same project folder, while `.godmode/REQUEST.md` has unticked items (or a `PLAN.md` is unfinished).
- **The finish check is a nudge.** It blocks once per stop and asks for a test run or a ticked checklist; you can answer it and move on.
- The hooks look for each other under `~/.claude`, so the default install location is the supported one.

## Install by hand

Copy `claude/skills/god-mode`, `claude/hubs` and (optionally) `claude/agents` into `~/.claude`, then add the hook entries listed in `wanted_hooks()` in `install.py` to your `settings.json`. Seven events are used: SessionStart, PostModelSwitch, UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure and Stop.
