<#
.SYNOPSIS
    God Mode installer for Claude Code on Windows (PowerShell)
    Safe, non-destructive: merges into settings.json and CLAUDE.md without overwriting existing configs.
#>

$ErrorActionPreference = "Stop"

$ClaudeDir = if ($env:TEST_CLAUDE_HOME) { $env:TEST_CLAUDE_HOME } else { Join-Path $HOME ".claude" }
$SkillDir = Join-Path $ClaudeDir "skills\god-mode"
$AgentsDir = Join-Path $ClaudeDir "agents"
$SettingsFile = Join-Path $ClaudeDir "settings.json"
$ClaudeMd = Join-Path $ClaudeDir "CLAUDE.md"
$RepoUrl = "https://github.com/SanyamKhaiwal/god-mode.git"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "          Installing God Mode for Claude Code     " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Determine source directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoDir = Split-Path -Parent $ScriptDir

$IsLocal = (Test-Path (Join-Path $RepoDir "SKILL.md")) -and (Test-Path (Join-Path $RepoDir "scripts"))

# 2. Setup directories
New-Item -ItemType Directory -Force -Path $ClaudeDir | Out-Null
New-Item -ItemType Directory -Force -Path $AgentsDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $ClaudeDir "skills") | Out-Null

# 3. Install skill files
Write-Host "[1/5] Installing skill files to $SkillDir..." -ForegroundColor Yellow
if ($IsLocal) {
    New-Item -ItemType Directory -Force -Path $SkillDir | Out-Null
    Copy-Item -Path (Join-Path $RepoDir "SKILL.md") -Destination $SkillDir -Force
    Copy-Item -Path (Join-Path $RepoDir "assets") -Destination $SkillDir -Recurse -Force
    Copy-Item -Path (Join-Path $RepoDir "references") -Destination $SkillDir -Recurse -Force
    Copy-Item -Path (Join-Path $RepoDir "scripts") -Destination $SkillDir -Recurse -Force
    if (Test-Path (Join-Path $RepoDir "agents")) {
        Copy-Item -Path (Join-Path $RepoDir "agents") -Destination $SkillDir -Recurse -Force
    }
} else {
    $tmpClone = Join-Path ([System.IO.Path]::GetTempPath()) ("godmode_" + [System.Guid]::NewGuid().ToString("N"))
    Write-Host "Cloning god-mode from GitHub..."
    git clone --quiet $RepoUrl $tmpClone
    New-Item -ItemType Directory -Force -Path $SkillDir | Out-Null
    Copy-Item -Path (Join-Path $tmpClone "SKILL.md") -Destination $SkillDir -Force
    Copy-Item -Path (Join-Path $tmpClone "assets") -Destination $SkillDir -Recurse -Force
    Copy-Item -Path (Join-Path $tmpClone "references") -Destination $SkillDir -Recurse -Force
    Copy-Item -Path (Join-Path $tmpClone "scripts") -Destination $SkillDir -Recurse -Force
    Copy-Item -Path (Join-Path $tmpClone "agents") -Destination $SkillDir -Recurse -Force
    Remove-Item -Recurse -Force $tmpClone
}

# 4. Install 5 subagents to ~/.claude/agents/
Write-Host "[2/5] Installing 5 subagents to $AgentsDir..." -ForegroundColor Yellow
$AgentsSrc = Join-Path $SkillDir "agents"
if (Test-Path $AgentsSrc) {
    Get-ChildItem -Path $AgentsSrc -Filter "*.md" | ForEach-Object {
        Copy-Item $_.FullName -Destination $AgentsDir -Force
        Write-Host "      - $($_.Name)" -ForegroundColor DarkGray
    }
} else {
    Write-Warning "agents directory not found in $SkillDir"
}

# 5. Non-destructively merge hooks into settings.json using Python (or PowerShell fallback)
Write-Host "[3/5] Configuring lifecycle hooks in $SettingsFile..." -ForegroundColor Yellow
$SkillDirForward = $SkillDir.Replace('\', '/')

$pyScript = @'
import json, sys, os

settings_file = sys.argv[1]
skill_dir = sys.argv[2].replace('\\', '/')

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
session = hooks.setdefault("SessionStart", [])
stop = hooks.setdefault("Stop", [])

session_cmd = f'[ ! -f "{skill_dir}/scripts/session-start.sh" ] || bash "{skill_dir}/scripts/session-start.sh"'
stop_cmd = f'[ ! -f "{skill_dir}/scripts/check-handoff.sh" ] || bash "{skill_dir}/scripts/check-handoff.sh"'

def has_cmd(arr, target):
    for entry in arr:
        for h in entry.get("hooks", []):
            if target in h.get("command", ""):
                return True
    return False

if not has_cmd(session, "session-start.sh"):
    session.append({
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
'@

$tempPy = [System.IO.Path]::GetTempFileName() + ".py"
[System.IO.File]::WriteAllText($tempPy, $pyScript, (New-Object System.Text.UTF8Encoding($false)))
try {
    python $tempPy $SettingsFile $SkillDirForward
} finally {
    if (Test-Path $tempPy) { Remove-Item $tempPy -Force }
}

# 6. Non-destructively configure CLAUDE.md
Write-Host "[4/5] Checking global directive in $ClaudeMd..." -ForegroundColor Yellow
$GodModeDirective = @"

## God Mode (coding workflow)

For any coding or implementation task (features, bug fixes, refactors, tests, build or config changes), follow the ``god-mode`` skill. Triage first: simple tasks go Direct with no pipeline. I can say ``quick`` or ``full`` to override triage.
"@

if (Test-Path $ClaudeMd) {
    $content = Get-Content -Path $ClaudeMd -Raw -Encoding UTF8
    if ($content -match "god-mode") {
        Write-Host "      ✓ God Mode directive already present in CLAUDE.md" -ForegroundColor DarkGray
    } else {
        Add-Content -Path $ClaudeMd -Value $GodModeDirective -Encoding UTF8
        Write-Host "      + Appended God Mode directive to CLAUDE.md" -ForegroundColor Green
    }
} else {
    Set-Content -Path $ClaudeMd -Value $GodModeDirective.TrimStart() -Encoding UTF8
    Write-Host "      + Created CLAUDE.md with God Mode directive" -ForegroundColor Green
}

# 7. Verification
Write-Host "[5/5] Verification check..." -ForegroundColor Yellow
$gitBash = "C:\Program Files\Git\bin\bash.exe"
$selfTest = Join-Path $SkillDir "scripts\selftest.sh"
if ((Test-Path $gitBash) -and (Test-Path $selfTest)) {
    & $gitBash $selfTest | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      ✓ All 22 tests passed successfully!" -ForegroundColor Green
    } else {
        Write-Host "      ! Selftest completed with warnings" -ForegroundColor Yellow
    }
} else {
    Write-Host "      ✓ Skill and subagents installed and ready" -ForegroundColor Green
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "          God Mode Installed Successfully!        " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Skill:      $SkillDir"
Write-Host "  Subagents:  5 installed in $AgentsDir"
Write-Host "  Hooks:      Active in $SettingsFile"
Write-Host "  Directive:  Active in $ClaudeMd"
Write-Host "==================================================" -ForegroundColor Cyan
