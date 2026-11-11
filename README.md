# God Mode

**An orchestration harness for Claude Code: plans with Opus, delegates execution to specialized subagents (Haiku/Sonnet) by complexity tier, verifies every step with real commands, and persists task state on disk across `/clear` and context compactions.**

[![CI](https://github.com/SanyamKhaiwal/god-mode/actions/workflows/ci.yml/badge.svg)](https://github.com/SanyamKhaiwal/god-mode/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: macOS · Linux · Windows](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-green.svg)](#quick-start)

> "Plan with the strongest model, execute with the cheapest model that can do each step correctly, verify everything, and never lose state."

---

## Case Study: Multi-File Architectural Refactoring (Single Run)

Measured on a 41-file synthetic enterprise platform (~1,100 lines of Python code across API routers, core database, security HMAC, audit services, telemetry, and test suites) constructed specifically to evaluate cross-module coupling without proprietary leaks. Full task prompts, token breakdowns, and raw reviewer logs are recorded in [benchmarks/case-study/](benchmarks/case-study/).

| Metric | Plain Claude Code (Single-Session Opus) | With God Mode (Multi-Tier) | Impact |
|---|---|---|---|
| **Cost per Task** | ~$8.13 *(100% Opus across all turns)* | **~$0.53** *(Opus plan + Haiku T1 + Sonnet T2)* | **93.5% Cost Reduction** |
| **Main Session Context Size** | 142,000 tokens *(bloated, near compaction)* | **16,200 tokens** *(compact & responsive)* | **88.6% Context Reduction** |
| **Mechanical Boilerplate (T1)** | 48,000 Opus tokens ($0.72) | 36,000 Haiku tokens ($0.03) | **95.8% cheaper on scaffolding** |
| **Bugs Caught Before Merge** | *Not evaluated* *(plain run lacked independent review; tests passed so model marked done)* | **5 bugs caught by `reviewer`** | Idempotency replay vulnerability, corrupt import-time timestamps, unwired webhooks caught |
| **Compaction / `/clear` State Retention** | Lossy conversational summary *(loses line numbers & dead ends)* | **100% Structured Disk Ledger** *(Resumed exact step & skipped dead ends)* | Lossless continuity across resets |
| **Turn Exit Without Docs** | Allowed *(status lost)* | **Enforced by Stop Hook** | Enforced handoff ledger |

---

## What It Catches in Real Codebases

| Scenario | Plain Claude Code | With God Mode |
|---|---|---|
| **Cross-cutting feature with unwired APIs** | LLM implements payment logic, runs unit tests, and claims `OK, done`. It misses that webhooks are unwired, audit logs evaluate timestamps once at module import time, and replayed payments don't validate matching amounts. | **`reviewer`** subagent diffs against the base branch and **catches 5 bugs** (including security bypasses and dead code) before merging. |
| **Noisy 1,500-line pytest dump in a 40-file repo** | Dumps 1,500 lines of tracebacks directly into chat context, consuming 15k tokens and triggering conversational lag. | **`filter-output.sh`** trims output to just the failing tail and exit code; logs full traces to `.godmode/test-log.md`. |
| **Long sessions & repeated compactions** | Compaction creates lossy conversational summaries. Details blur, exact outputs vanish, and Claude **re-tries broken approaches that previously failed**. | **`session-start.sh` hook** automatically reloads `.godmode/PLAN.md` and `HANDOFF.md`. Resumes the exact step and **actively avoids all recorded dead ends**. |
| **Exiting a turn without documentation** | Agent finishes turn and stops. Next session has zero record of what was modified or what to do next. | **`check-handoff.sh` Stop hook** requires the agent to update `.godmode/HANDOFF.md` before concluding the turn. |

---

## Architectural Paradigms Compared

| Paradigm | How It Operates | Why God Mode Is Different |
|---|---|---|
| **Prompt Compression Tools** | Compresses syntax and prompts into shorthand to save ~10–15% tokens. | **Model-Tier Arbitrage:** God Mode doesn't truncate language; it routes mechanical steps to Haiku (18.7x cheaper), cutting costs by **~93%** on multi-file tasks without degrading reasoning. |
| **Static Code Indexers** | Builds an AST knowledge graph to help Claude *find* symbols. | **Full Execution Lifecycle:** Code indexers only search code; God Mode pairs a built-in AST indexer with execution subagents, test log filtering, Stop hooks, and diff auditing. |
| **Heavyweight Multi-Agent Frameworks** | Installs background Docker containers, external vector databases, and heavy toolchains. | **Zero Dependencies:** Pure shell harnesses, Python standard library, and 5 focused subagents. Installs in seconds with no external daemons. |
| **Standard Claude Code** | Operates as a single conversation thread that degrades over long tasks. | **Orchestration Harness:** Plans with Opus, delegates execution across isolated subagent tiers, and deterministically persists state across session resets. |

---

## Zero-Dependency AST Graph Indexing (Python · Java · C++)

For large repositories and complex refactoring tasks, God Mode includes a built-in, multi-language AST graph indexer (`scripts/build-graph.py`) that operates with **zero external dependencies and zero LLM token costs**:

- **Languages Supported:** Python (`.py`), Java (`.java`), and C/C++ (`.h`, `.hpp`, `.cpp`, `.cc`).
- **Sub-Second Build & Incremental Cache:** Indexes a 40+ file project in < 1 second; file-hash caching re-indexes modified files in **~20ms**.
- **Hub Centrality Analysis:** Identifies high-fan-in "Hub Nodes" (files with the most incoming dependents) to predict blast radius before modifying code.
- **Atomic File Swapping:** Uses `os.replace` to prevent race conditions during concurrent agent access.
- **Fail-Safe Fallback:** If a file contains non-standard syntax or dynamic macros, the indexer skips it gracefully without breaking the graph, and subagents automatically fall back to native `ripgrep`.

**Case Study Measured Impact (from [benchmarks/case-study/](benchmarks/case-study/)):**
- File reads during research dropped from **113 calls to 8 calls** (**92.9% reduction in I/O**).
- Subagent trajectory exploration steps dropped from **230 steps to 20 steps** (**91.3% reduction**).

---

## Quick Start

### 1-Command Automated Install (Safe & Non-Destructive)

Merges hooks into `~/.claude/settings.json`, configures `~/.claude/CLAUDE.md`, installs the 5 subagents into `~/.claude/agents/`, and runs self-tests. It never overwrites existing configurations.

**macOS / Linux / Git Bash:**
```bash
curl -fsSL https://raw.githubusercontent.com/SanyamKhaiwal/god-mode/main/install/install.sh | bash
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/SanyamKhaiwal/god-mode/main/install/install.ps1 | iex"
```

---

### Manual Setup (4 Steps)

```bash
# 1. Clone into temporary directory
git clone https://github.com/SanyamKhaiwal/god-mode.git /tmp/god-mode

# 2. Copy runtime skill files to ~/.claude/skills/god-mode
mkdir -p ~/.claude/skills/god-mode
cp -r /tmp/god-mode/SKILL.md /tmp/god-mode/assets /tmp/god-mode/references /tmp/god-mode/scripts ~/.claude/skills/god-mode/

# 3. Copy the 5 subagents to ~/.claude/agents
mkdir -p ~/.claude/agents
cp /tmp/god-mode/agents/*.md ~/.claude/agents/

# 4. Clean up temporary clone
rm -rf /tmp/god-mode
```

Then register the hooks in `~/.claude/settings.json`:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "[ ! -f \"$HOME/.claude/skills/god-mode/scripts/session-start.sh\" ] || bash \"$HOME/.claude/skills/god-mode/scripts/session-start.sh\"",
            "timeout": 10,
            "statusMessage": "Loading God Mode handoff"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "[ ! -f \"$HOME/.claude/skills/god-mode/scripts/check-handoff.sh\" ] || bash \"$HOME/.claude/skills/god-mode/scripts/check-handoff.sh\"",
            "timeout": 20,
            "statusMessage": "Checking God Mode handoff"
          }
        ]
      }
    ]
  }
}
```

And add to `~/.claude/CLAUDE.md`:
```markdown
## God Mode (coding workflow)
For any coding or implementation task (features, bug fixes, refactors, tests, build or config changes), follow the `god-mode` skill. Triage first: simple tasks go Direct with no pipeline. I can say `quick` or `full` to override triage.
```

---

## How to Use

### 1. Automatic Execution (Zero Workflow Friction)

**You don't need to remember to type a trigger prefix.**

Because the installer configures your global `~/.claude/CLAUDE.md`, Claude Code **automatically invokes God Mode for any coding or implementation task** (features, refactors, bug fixes, test suites).

Just prompt Claude Code normally:

```text
Add a sliding-window rate limiter with burst capability to src/api.py
```

Claude will automatically triage the task and announce its route in one line:
> *Route: Light — 3 files, clear spec, tests exist.*

- **Simple 1–2 file edits** automatically stay in the **Direct route** (instant execution in the main session, zero overhead).
- **Multi-step or risk-area tasks** automatically activate the multi-tier subagent pipeline.

### 2. Optional Overrides

If you ever want to force a specific mode, just include a single keyword in your prompt:
- **`quick: <task>`** — Forces the **Direct route** (bypasses research, plans, and subagents; executes immediately).
- **`full: <task>`** — Forces the **Full route** (runs parallel research $\rightarrow$ writes concrete plan $\rightarrow$ pauses for user approval gate $\rightarrow$ executes).

---

## Architecture at a Glance

| Subagent | Tier / Role | Model | Write Perms | Output Contract |
|---|---|:---:|:---:|---|
| **`researcher`** | Fast lookups | Haiku | ❌ Read-only | Under 40 lines. Lists key locations (`path:line`), load-bearing claims, and unread files. |
| **`researcher-deep`** | Behavioral tracing | Sonnet | ❌ Read-only | Under 60 lines. Traces call paths, flags **silent limits** (clamps, thresholds, conversions). |
| **`executor-light`** | T1 Mechanical | Haiku | ️ Yes | Boilerplate, renames, wiring patterns, test cases from spec. Touches only listed files. |
| **`executor`** | T2 Logic | Sonnet | ️ Yes | Programming with clear specs, edge cases, bug fixes with known cause. 1 retry on fail. |
| **`reviewer`** | Quality Gate | Sonnet | ❌ Read-only | Diffs against base commit. Prioritizes correctness, broken integrations, and regressions. |

> **Note on Compatibility:** Built natively for Claude Code. The orchestration principles and subagent contracts can also be adapted to other multi-agent developer harnesses.

---

## Contributing

We welcome contributions! To report a bug, suggest an enhancement, or submit benchmark comparisons across models and codebases, please read our [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Distributed under the [MIT License](LICENSE). Copyright (c) 2026 Sanyam Khaiwal.
