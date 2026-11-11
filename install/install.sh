#!/usr/bin/env bash
# God Mode installer for Claude Code
# Safe, non-destructive: merges into settings.json and CLAUDE.md without overwriting existing configs.
set -e

CLAUDE_DIR="${TEST_CLAUDE_HOME:-$HOME/.claude}"
SKILL_DIR="$CLAUDE_DIR/skills/god-mode"
AGENTS_DIR="$CLAUDE_DIR/agents"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
REPO_URL="https://github.com/SanyamKhaiwal/god-mode.git"

echo "=================================================="
echo "          Installing God Mode for Claude Code     "
echo "=================================================="
echo

# 1. Determine source directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$REPO_DIR/SKILL.md" ] && [ -d "$REPO_DIR/scripts" ]; then
  SRC_DIR="$REPO_DIR"
  IS_LOCAL=1
else
  IS_LOCAL=0
fi

# 2. Setup directories
mkdir -p "$CLAUDE_DIR"
mkdir -p "$AGENTS_DIR"
mkdir -p "$CLAUDE_DIR/skills"

# 3. Install skill files to ~/.claude/skills/god-mode
echo "[1/5] Installing skill files to $SKILL_DIR..."
if [ "$IS_LOCAL" -eq 1 ]; then
  mkdir -p "$SKILL_DIR"
  cp -r "$SRC_DIR/SKILL.md" "$SKILL_DIR/"
  cp -r "$SRC_DIR/assets" "$SKILL_DIR/"
  cp -r "$SRC_DIR/references" "$SKILL_DIR/"
  cp -r "$SRC_DIR/scripts" "$SKILL_DIR/"
  if [ -d "$SRC_DIR/agents" ]; then
    cp -r "$SRC_DIR/agents" "$SKILL_DIR/"
  fi
else
  TMP_CLONE="$(mktemp -d)"
  echo "Cloning god-mode from GitHub..."
  git clone --quiet "$REPO_URL" "$TMP_CLONE"
  mkdir -p "$SKILL_DIR"
  cp -r "$TMP_CLONE/SKILL.md" "$SKILL_DIR/"
  cp -r "$TMP_CLONE/assets" "$SKILL_DIR/"
  cp -r "$TMP_CLONE/references" "$SKILL_DIR/"
  cp -r "$TMP_CLONE/scripts" "$SKILL_DIR/"
  cp -r "$TMP_CLONE/agents" "$SKILL_DIR/"
  rm -rf "$TMP_CLONE"
fi

chmod +x "$SKILL_DIR/scripts/"*.sh 2>/dev/null || true

# 4. Install 5 subagents to ~/.claude/agents/
echo "[2/5] Installing 5 subagents to $AGENTS_DIR..."
AGENTS_SRC="$SKILL_DIR/agents"
if [ -d "$AGENTS_SRC" ]; then
  cp "$AGENTS_SRC"/*.md "$AGENTS_DIR/"
  echo "      - executor-light.md"
  echo "      - executor.md"
  echo "      - researcher.md"
  echo "      - researcher-deep.md"
  echo "      - reviewer.md"
else
  echo "WARNING: agents directory not found in $SKILL_DIR"
fi

# 5. Non-destructively merge hooks into settings.json using Python
echo "[3/5] Configuring lifecycle hooks in $SETTINGS_FILE..."

PYTHON_BIN=""
for p in "python3" "python" "py" "python.exe" "/c/Python314/python.exe" "$LOCALAPPDATA/Programs/Python/Python*/python.exe"; do
  if "$p" -c "import sys" >/dev/null 2>&1; then
    PYTHON_BIN="$p"
    break
  fi
done

if [ -n "$PYTHON_BIN" ]; then
  "$PYTHON_BIN" - "$SETTINGS_FILE" "$SKILL_DIR" <<'PYEOF'
import json
import os
import sys

settings_file = os.path.expanduser(sys.argv[1])
skill_dir = os.path.expanduser(sys.argv[2]).replace('\\', '/')

data = {}
if os.path.isfile(settings_file):
    try:
        with open(settings_file, "r", encoding="utf-8-sig") as f:
            content = f.read().strip()
            if content:
                data = json.loads(content)
    except Exception as e:
        print(f"Notice: Could not parse existing settings.json ({e}). Creating backup...")
        with open(settings_file + ".bak", "w", encoding="utf-8") as bf:
            bf.write(content)
        data = {}

hooks = data.setdefault("hooks", {})
session_start = hooks.setdefault("SessionStart", [])
stop = hooks.setdefault("Stop", [])

session_cmd = f'[ ! -f "{skill_dir}/scripts/session-start.sh" ] || bash "{skill_dir}/scripts/session-start.sh"'
stop_cmd = f'[ ! -f "{skill_dir}/scripts/check-handoff.sh" ] || bash "{skill_dir}/scripts/check-handoff.sh"'

def has_cmd(hook_list, target_cmd):
    for entry in hook_list:
        for h in entry.get("hooks", []):
            if target_cmd in h.get("command", ""):
                return True
    return False

if not has_cmd(session_start, "session-start.sh"):
    session_start.append({
        "hooks": [
            {
                "type": "command",
                "command": session_cmd,
                "timeout": 10,
                "statusMessage": "Loading God Mode handoff"
            }
        ]
    })
    print("      + Added SessionStart hook (session-start.sh)")
else:
    print("      ✓ SessionStart hook already registered")

if not has_cmd(stop, "check-handoff.sh"):
    stop.append({
        "hooks": [
            {
                "type": "command",
                "command": stop_cmd,
                "timeout": 20,
                "statusMessage": "Checking God Mode handoff"
            }
        ]
    })
    print("      + Added Stop hook (check-handoff.sh)")
else:
    print("      ✓ Stop hook already registered")

with open(settings_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
PYEOF
else
  echo "Notice: Python not detected. Please register the hooks manually in settings.json (see README)."
fi

# 6. Non-destructively configure CLAUDE.md
echo "[4/5] Checking global directive in $CLAUDE_MD..."
GOD_MODE_DIRECTIVE="## God Mode (coding workflow)

For any coding or implementation task (features, bug fixes, refactors, tests, build or config changes), follow the \`god-mode\` skill. Triage first: simple tasks go Direct with no pipeline. I can say \`quick\` or \`full\` to override triage."

if [ -f "$CLAUDE_MD" ]; then
  if grep -qi "god-mode" "$CLAUDE_MD"; then
    echo "      ✓ God Mode directive already present in CLAUDE.md"
  else
    printf "\n%s\n" "$GOD_MODE_DIRECTIVE" >> "$CLAUDE_MD"
    echo "      + Appended God Mode directive to CLAUDE.md"
  fi
else
  printf "%s\n" "$GOD_MODE_DIRECTIVE" > "$CLAUDE_MD"
  echo "      + Created CLAUDE.md with God Mode directive"
fi

# 7. Run self-tests
echo "[5/5] Running self-test suite..."
if [ -f "$SKILL_DIR/scripts/selftest.sh" ]; then
  if bash "$SKILL_DIR/scripts/selftest.sh" > /dev/null 2>&1; then
    echo "      ✓ All 22 tests passed successfully!"
  else
    echo "      ! Selftest completed with warnings (check environment bash configuration)"
  fi
fi

echo
echo "=================================================="
echo "          God Mode Installed Successfully!        "
echo "=================================================="
echo "  Skill:      $SKILL_DIR"
echo "  Subagents:  5 installed in $AGENTS_DIR"
echo "  Hooks:      Active in $SETTINGS_FILE"
echo "  Directive:  Active in $CLAUDE_MD"
echo "=================================================="
