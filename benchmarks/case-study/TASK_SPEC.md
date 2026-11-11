# Benchmark Case Study: Multi-File Architectural Refactoring

**Date:** November 11–12, 2026  
**Type:** Single-run empirical comparative evaluation  
**Target Codebase:** 41-file synthetic enterprise billing & auth platform (~1,100 lines of Python code, 23 unit tests).  
*Note: This codebase was constructed specifically to model multi-module cross-coupling (core database, telemetry, security, schemas, services, API routers, and test fixtures) without proprietary dependencies or confidential company code.*

---

## 1. Task Prompt

```text
Refactor this codebase to introduce an Event Bus pattern — all services currently call each other directly (billing -> audit, webhook -> subscription, etc.). Decouple them through an event bus so services emit events and other services subscribe to them. Map which services need to emit vs subscribe, and identify every direct cross-service call that needs to be replaced.
```

---

## 2. Models Evaluated

- **Main Session / Planner:** `claude-3-opus-20240229` (also evaluated on `claude-3-7-sonnet-20250219`)
- **Researcher Subagent:** `claude-3-5-haiku-20241022`
- **Executor Subagent:** `claude-3-7-sonnet-20250219`
- **Reviewer Subagent:** `claude-3-7-sonnet-20250219`

---

## 3. Evaluation Setup

Two runs were executed against identical initial git commits (`08a2372`):

1. **Run A (Standard Exploration / No Graph):**  
   The subagent was tasked with answering the architectural refactoring prompt using standard file reading (`read_file`) and directory traversal without access to an AST project map.
2. **Run B (God Mode with AST Graph Indexing):**  
   The subagent was provided with `.godmode/project-map.json` and `.godmode/graph-brief.txt`, generated locally via `scripts/build-graph.py` (0 LLM tokens, 0.8s runtime), and instructed to consult the graph first and only read targeted files.
