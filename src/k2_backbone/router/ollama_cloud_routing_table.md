# Ollama Cloud Model Routing Table for K2-Backbone

> **Last Updated:** 2026-05-28
> **Source:** https://ollama.com/search?c=cloud

## Model Inventory (Ollama Cloud)

| Model | Sizes | Context | Type | Best For | Pulls |
|---|---|---|---|---|---|
| **gemma4** | 26B, 31B, E2B, E4B | 128K-256K | Dense + MoE | Reasoning, agentic, coding, multimodal | 10.6M |
| **qwen3.5** | 0.8B-122B | - | MoE | Multimodal, multilingual (201 langs), agents | 12.6M |
| **glm-5.1** | - | - | Dense | **Agentic engineering, coding** (SWE-Bench Pro SOTA) | 2.2M |
| **minimax-m2.7** | - | - | Dense | Coding, agentic workflows | 2.2M |
| **nemotron-3-super** | 120B (12B active) | - | MoE | **Multi-agent, IT automation, efficiency** | 2.4M |
| **glm-5** | 744B total (40B active) | - | MoE | Complex systems, long-horizon tasks | 2.3M |
| **minimax-m2.5** | - | - | Dense | Productivity, coding | 2.2M |
| **glm-4.7** | - | - | Dense | Coding | 2.2M |
| **gemini-3-flash-preview** | - | - | Dense | **Speed, frontier intelligence, low cost** | 2.2M |
| **minimax-m2.1** | - | - | Dense | Multilingual code | 2.1M |
| **qwen3-coder-next** | - | - | Dense | **Agentic coding workflows** | 1.3M |
| **deepseek-v3.2** | 671B | 160K | MoE | **Reasoning, agent performance** | 2.2M |
| **kimi-k2.6** | 1.04T | 256K | Dense | **Swarm orchestration, long-horizon coding** | 269.7K |
| **ministral-3** | 3B, 8B, 14B | - | Dense | Edge deployment | 1.2M |
| **devstral-small-2** | 24B | - | Dense | **Tool use, codebase exploration, SWE** | 845.4K |
| **deepseek-v4-flash** | 284B (13B active) | 1M | MoE | Efficient reasoning, 1M context | 92.7K |
| **deepseek-v4-pro** | - | 1M | MoE | Frontier reasoning, 3 modes | 81.8K |
| **qwen3-next** | 80B | - | MoE | Parameter efficiency, speed | 558.2K |
| **nemotron-3-nano** | 4B, 30B | - | Dense | **Efficient agentic models** | 460.4K |
| **rnj-1** | 8B | - | Dense | Code, STEM | 469.5K |

---

## Best-in-Class by Task Type

### 🏆 **Code Generation & Engineering**

| Rank | Model | Why | Benchmark |
|---|---|---|---|
| 🥇 | **glm-5.1** | SWE-Bench Pro SOTA, NL2Repo leader | SWE-Bench Pro: 58.4% |
| 🥈 | **deepseek-v3.2** | Strong reasoning + agent performance | LiveCodeBench: 81.2% |
| 🥉 | **qwen3-coder-next** | Agentic coding workflows | SWE-Bench: 69.6% |
| 4 | **devstral-small-2** | 24B, tool use, codebase exploration | SWE-Bench Verified: 65.8% |
| 5 | **gemma4 31B** | LiveCodeBench v6: 80.0%, Codeforces ELO: 2150 | LiveCodeBench: 80.0% |

**K2-Backbone Assignment:** `code_generation` → **glm-5.1** (primary), **deepseek-v3.2** (fallback)

### 🏆 **Reasoning & Problem Solving**

| Rank | Model | Why | Benchmark |
|---|---|---|---|
| 🥇 | **qwen3.5 122B** | AIME 2026: 95.3%, HMMT: 100% | AIME: 95.3%, HMMT: 100% |
| 🥈 | **gemma4 31B** | AIME: 89.2%, BigBench Extra Hard: 74.4% | AIME: 89.2% |
| 🥉 | **nemotron-3-super** | AIME25: 90.21%, GPQA: 79.23% | AIME25: 90.21% |
| 4 | **glm-5.1** | AIME 2026: 95.3%, GPQA: 86.2% | AIME: 95.3% |
| 5 | **deepseek-v4-pro** | 1M context, 3 reasoning modes | Frontier MoE |

**K2-Backbone Assignment:** `analysis`, `synthesis` → **qwen3.5 122B** (primary), **gemma4 31B** (fallback)

### 🏆 **Agentic Workflows & Orchestration**

| Rank | Model | Why | Benchmark |
|---|---|---|---|
| 🥇 | **kimi-k2.6** | **300 agents, 4K steps**, swarm orchestration | Native agentic |
| 🥈 | **nemotron-3-super** | 12B active of 120B, multi-agent optimized | Terminal Bench: 31% |
| 🥉 | **glm-5.1** | Sustains optimization over 100s of rounds | Terminal-Bench 2.0: 63.5% |
| 4 | **qwen3.5** | Million-agent RL environments | Agent scaffolds |
| 5 | **deepseek-v3.2** | Harmonizes efficiency + reasoning | Agent performance |

**K2-Backbone Assignment:** `integration`, `orchestration` → **kimi-k2.6** (primary), **nemotron-3-super** (fallback)

### 🏆 **Testing & Validation**

| Rank | Model | Why | Benchmark |
|---|---|---|---|
| 🥇 | **qwen3.5** | IFEval: 94.8%, MultiChallenge: 67.6% | IFEval: 94.8% |
| 🥈 | **gemma4 31B** | Tau2: 76.9%, instruction following | Tau2: 76.9% |
| 🥉 | **glm-5.1** | τ³-Bench: 70.6%, MCP-Atlas: 71.8% | MCP-Atlas: 71.8% |

**K2-Backbone Assignment:** `testing`, `review` → **qwen3.5** (primary), **gemma4 31B** (fallback)

### 🏆 **Research & Data Processing**

| Rank | Model | Why | Benchmark |
|---|---|---|---|
| 🥇 | **qwen3.5 122B** | MMLU-Pro: 87.8%, HLE: 28.7% | MMLU-Pro: 87.8% |
| 🥈 | **gemma4 31B** | MMLU-Pro: 85.2%, BigBench: 74.4% | MMLU-Pro: 85.2% |
| 🥉 | **nemotron-3-super** | MMLU-Pro: 83.73%, long context RULER: 96.3% @ 256K | RULER: 96.3% |
| 4 | **glm-5** | 744B total, complex systems engineering | Complex reasoning |

**K2-Backbone Assignment:** `research`, `data_processing` → **qwen3.5 122B** (primary), **gemma4 31B** (fallback)

### 🏆 **Documentation & Writing**

| Rank | Model | Why | Benchmark |
|---|---|---|---|
| 🥇 | **qwen3.5** | 201 languages, MMMLU: 88.5% | Multilingual: 201 langs |
| 🥈 | **gemma4 31B** | Native system prompt support, 262K vocab | System prompts |
| 🥉 | **glm-5.1** | Strong NL2Repo (documentation generation) | NL2Repo: 42.7% |

**K2-Backbone Assignment:** `documentation`, `writing` → **qwen3.5** (primary), **gemma4 31B** (fallback)

### 🏆 **Cost-Efficient Fallback (T3/Economy)**

| Rank | Model | Why | Cost |
|---|---|---|---|
| 🥇 | **nemotron-3-nano** | 4B params, efficient agentic | Ultra-low |
| 🥈 | **gemma4 E2B** | 2.3B effective, edge-optimized | Ultra-low |
| 🥉 | **qwen3.5 0.8B** | Smallest Qwen, multilingual | Ultra-low |
| 4 | **ministral-3** | 3B-14B, edge deployment | Low |
| 5 | **rnj-1** | 8B, code + STEM | Low |

**K2-Backbone Assignment:** Fallback for all types when budget exceeded

---

## Updated K2-Backbone Router Config

```python
# src/router/necroswarm_router.py — Updated COST_PER_1K and CAPABILITY_MATRIX

COST_PER_1K = {
    # Ollama Cloud models (estimated based on active params)
    "kimi-k2.6":         3.00,   # 1.04T params, premium pricing
    "glm-5.1":           2.50,   # Flagship agentic engineering
    "qwen3.5-122b":      2.00,   # 122B MoE, competitive
    "deepseek-v3.2":     1.50,   # 671B MoE, efficient
    "gemma4-31b":        1.20,   # 31B dense, balanced
    "nemotron-3-super":  1.00,   # 120B (12B active), efficient
    "devstral-small-2":  0.80,   # 24B, SWE-focused
    "glm-5":             1.80,   # 744B (40B active)
    "deepseek-v4-flash": 0.60,   # 284B (13B active), budget
    "deepseek-v4-pro":   2.00,   # 1M context, frontier
    "qwen3-coder-next":  1.00,   # Coding specialist
    "minimax-m2.7":      1.20,   # Coding + agentic
    "gemini-3-flash":    0.50,   # Speed-optimized
    # Economy tier
    "nemotron-3-nano":   0.10,   # 4B, ultra-cheap
    "gemma4-e2b":        0.08,   # 2.3B effective
    "qwen3.5-0.8b":      0.05,   # Ultra-small
}

# Capability scores per task type (0-10)
CAPABILITY_MATRIX = {
    "kimi-k2.6": {
        "orchestration": 10, "code": 8, "analysis": 9,
        "writing": 7, "optimization": 8, "research": 7
    },
    "glm-5.1": {
        "code": 10, "analysis": 9, "research": 8,
        "writing": 7, "optimization": 9, "orchestration": 6
    },
    "qwen3.5-122b": {
        "analysis": 10, "research": 10, "code": 9,
        "writing": 8, "optimization": 8, "orchestration": 7
    },
    "deepseek-v3.2": {
        "code": 9, "analysis": 9, "research": 8,
        "optimization": 8, "writing": 7, "orchestration": 6
    },
    "gemma4-31b": {
        "code": 8, "analysis": 8, "research": 8,
        "writing": 7, "optimization": 7, "orchestration": 6
    },
    "nemotron-3-super": {
        "orchestration": 9, "code": 7, "analysis": 8,
        "research": 7, "optimization": 6, "writing": 6
    },
    "devstral-small-2": {
        "code": 9, "analysis": 6, "research": 5,
        "optimization": 5, "writing": 4, "orchestration": 4
    },
    "gemini-3-flash": {
        "code": 7, "analysis": 7, "research": 6,
        "writing": 6, "optimization": 6, "orchestration": 5
    },
    "deepseek-v4-flash": {
        "code": 7, "analysis": 7, "research": 6,
        "writing": 5, "optimization": 6, "orchestration": 5
    },
    "qwen3-coder-next": {
        "code": 9, "analysis": 6, "research": 5,
        "writing": 5, "optimization": 6, "orchestration": 4
    },
    # Economy tier
    "nemotron-3-nano": {
        "code": 5, "analysis": 5, "research": 4,
        "writing": 4, "optimization": 4, "orchestration": 4
    },
}
```

---

## Key Changes from Previous Routing Table

| Aspect | Before (K2-Backbone v1) | After (Ollama Cloud Update) |
|---|---|---|
| **Models tracked** | 5 (kimi, claude, deepseek, glm, qwen) | 15+ (full Ollama Cloud inventory) |
| **Best coder** | claude-opus-4 | **glm-5.1** (SWE-Bench Pro SOTA) |
| **Best reasoner** | kimi-k2.6 | **qwen3.5 122B** (AIME: 95.3%, HMMT: 100%) |
| **Best agentic** | kimi-k2.6 | **kimi-k2.6** (still king: 300 agents, 4K steps) |
| **Best budget** | qwen2.5 | **nemotron-3-nano** (4B, $0.10/1K) |
| **New entry** | — | **devstral-small-2** (24B SWE specialist) |
| **New entry** | — | **gemma4** (multimodal, edge + cloud) |
| **New entry** | — | **deepseek-v4** (1M context, 3 reasoning modes) |

---

## Recommendation

**Update `src/router/necroswarm_router.py` with this table.**

The key shifts:
1. **glm-5.1 replaces Claude** as top code generation model (SWE-Bench Pro: 58.4%)
2. **qwen3.5 122B is the reasoning king** (AIME: 95.3%, HMMT: 100%)
3. **kimi-k2.6 still dominates agentic** (300 agents, 4K steps, no competition)
4. **Nemotron-3-Super is the efficiency champion** (12B active of 120B, multi-agent optimized)
5. **DeepSeek V4 Flash** is the new budget king for 1M context tasks

**Your 10-D Council should now seat:**
1. **Kimi K2.6** — Agentic orchestration (D1: Swarm Coordination)
2. **GLM-5.1** — Code generation (D2: Engineering)
3. **Qwen3.5 122B** — Reasoning + analysis (D3: Deep Thinking)
4. **DeepSeek V3.2** — Balanced performer (D4: General Purpose)
5. **Gemma4 31B** — Multimodal (D5: Vision + Text)
6. **Nemotron-3-Super** — Multi-agent efficiency (D6: Scale)
7. **Devstral Small 2** — SWE specialist (D7: Code Review)
8. **DeepSeek V4 Flash** — Budget long-context (D8: Economy)
9. **Qwen3 Coder Next** — Agentic coding (D9: Coding)
10. **Nemotron-3-Nano** — Ultra-cheap fallback (D10: Emergency)
