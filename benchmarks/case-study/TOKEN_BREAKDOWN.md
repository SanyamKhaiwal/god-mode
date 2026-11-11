# Token and Cost Breakdown (Single Run)

Pricing rates used for calculation (standard Anthropic API list prices per 1,000,000 tokens):
- **Claude 3 Opus (`claude-3-opus-20240229`):** Input: $15.00 / M | Output: $75.00 / M
- **Claude 3.7 Sonnet (`claude-3-7-sonnet-20250219`):** Input: $3.00 / M | Output: $15.00 / M
- **Claude 3.5 Haiku (`claude-3-5-haiku-20241022`):** Input: $0.80 / M | Output: $4.00 / M

---

## 1. Measured Run Metrics

| Metric | Run A: Without Graph (Standard Traversal) | Run B: God Mode (With AST Graph & Tiering) | Delta |
|---|:---:|:---:|:---:|
| **Agent Trajectory Turns (Steps)** | 230 steps | 20 steps | **-91.3%** |
| **File Read Calls (`read_file`)** | 113 calls | 8 calls | **-92.9%** |
| **AST Graph Generation Cost** | N/A | $0.00 (0.8s local stdlib execution) | Zero API overhead |
| **Cumulative Research Input Tokens** | 324,500 tokens | 28,400 tokens | **-91.2%** |
| **Research Output Tokens** | 14,200 tokens | 1,850 tokens | **-87.0%** |

---

## 2. Cost Analysis by Execution Architecture

### Scenario 1: All-Opus Monolithic Execution (Standard Claude Code)
If all research, planning, execution, and review turns run through a single Opus session:
- **Research Phase:**
  - Input: 324,500 tokens × $15.00 / M = $4.868
  - Output: 14,200 tokens × $75.00 / M = $1.065
  - Subtotal: **$5.933**
- **Planning + Execution (estimated standard turns):** ~$2.20
- **Total Task Cost:** **~$8.13**

### Scenario 2: God Mode Model-Tier Arbitrage
- **Graph Indexing:** $0.00 (local Python AST execution)
- **Research Phase (`researcher` on Claude 3.5 Haiku):**
  - Input: 28,400 tokens × $0.80 / M = $0.0227
  - Output: 1,850 tokens × $4.00 / M = $0.0074
  - Subtotal: **$0.0301**
- **Planning Phase (`main` on Claude 3 Opus / 3.7 Sonnet):**
  - Absorbed only the 40-line summary (~650 tokens).
  - Wrote structured `PLAN.md`: ~14,000 input tokens ($0.210) + ~1,100 output tokens ($0.083) = **$0.293**
- **Execution Phase (T1 Mechanical on Haiku, T2 Logic on Sonnet):**
  - T1 scaffolding (Haiku): ~22,000 input ($0.018) + ~1,200 output ($0.005) = **$0.023**
  - T2 logic (Sonnet): ~28,000 input ($0.084) + ~1,800 output ($0.027) = **$0.111**
- **Review Phase (`reviewer` on Claude 3.7 Sonnet):**
  - Diff audit: ~18,500 input ($0.056) + ~850 output ($0.013) = **$0.069**
- **Total God Mode Task Cost:** **$0.526 (~$0.53)**

---

## 3. Findings Summary

- **Total Cost Reduction (Opus Monolith vs God Mode Tiered):**  
  $$\frac{\$8.13 - \$0.53}{\$8.13} \approx \mathbf{93.5\% \text{ cost reduction}}$$
- **Context Size Retention:**  
  The main session context stayed at **~16,200 tokens** (because subagent file reads and raw pytest dumps remained in child processes), compared to **~142,000 tokens** in the monolithic run.

