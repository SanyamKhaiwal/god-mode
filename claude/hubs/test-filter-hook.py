"""PreToolUse(Bash) hook: run plain test-runner commands through god-mode's filter-output.sh so long test
output is trimmed (failure lines, failure locations and the tail are kept; the exit code is preserved).

Only simple, single test-runner commands are rewritten. Commands with pipes, redirects, heredocs or
already going through godmode-run.sh / filter-output.sh are left alone. Stdlib only. Always exits 0.

The hook returns only updatedInput and no permissionDecision, so it never approves a command: the user's
normal permission rules and prompts apply to the rewritten command exactly as before. The pattern below is
still deliberately narrow. Disable by setting GODMODE_NO_FILTER=1."""
import json
import os
import re
import shlex
import sys

FILTER = os.path.join(os.path.expanduser("~"), ".claude", "skills", "god-mode", "scripts",
                      "filter-output.sh").replace("\\", "/")

ENV_PREFIX = r"(?:[A-Za-z_][A-Za-z0-9_]*=[^\s;&|<>]+\s+)*"
RUNNER = (r"(?:python3?\s+-m\s+pytest|pytest|py\.test|python3?\s+-m\s+unittest|npm\s+(?:run\s+)?test|"
          r"yarn\s+test|pnpm\s+(?:run\s+)?test|npx\s+(?:jest|vitest|mocha)|jest|vitest|mvn\s+(?:-\S+\s+)*test|"
          r"(?:\./)?gradlew?\s+(?:\S+\s+)*test|ctest|cargo\s+test|go\s+test|dotnet\s+test|make\s+test)")
TEST_CMD = re.compile(r"^\s*" + ENV_PREFIX + RUNNER + r"(?:\s+[^\s;&|<>$`()]+)*\s*$")


def rewrite(command):
    """Return the filtered command, or None when the command should run unchanged."""
    if os.environ.get("GODMODE_NO_FILTER") == "1":
        return None
    if not command or "filter-output.sh" in command or "godmode-run.sh" in command:
        return None
    if "\n" in command or not TEST_CMD.match(command):
        return None
    return f'bash "{FILTER}" bash -c {shlex.quote(command.strip())}'


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    if data.get("tool_name") != "Bash":
        return
    tool_input = data.get("tool_input") or {}
    new = rewrite(str(tool_input.get("command", "")))
    if not new:
        return
    updated = dict(tool_input)
    updated["command"] = new
    # No permissionDecision: the user's normal permission rules still decide whether the command runs.
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "updatedInput": updated}}))


if __name__ == "__main__":
    main()
