"""
Model Routing Table — Single Source of Truth for K2 Swarm Model Assignments

This is the central model routing table used across the K2 ecosystem:
- k2-backbone (NecroSwarm router, Council router)
- neuroswarm (Council deliberation, refusal routing)
- OpenClaw plugin (k2_route tool)

All model changes go HERE. Downstream repos import from this package.

Updated 2026-06-24 for latest Ollama Cloud best-in-class models.
"""

# ── 10-D Dimension Map: Primary Model Assignments ────────────────────
#
# Each dimension maps to a specific cognitive capability and the
# best-in-class Ollama Cloud model for that capability.
#
# When a model refuses or errors, NEUROSWARM routes to the
# dimension's fallback chain to preserve cognitive diversity.

DIMENSION_MAP = {
    "D1_synthesis":    "kimi-k2.6:cloud",           # Orchestration, convergence, 313K pulls
    "D2_deep_reason":  "qwen3.5:122b:cloud",        # AIME 95.3%, HMMT 100%, 14.1M pulls
    "D3_code":         "glm-5.2:cloud",             # SWE-Marathon #1 open-source, 1M ctx, 48.7K pulls
    "D4_vision":       "minimax-m3:cloud",           # Native multimodal, 1M ctx, 64.7K pulls
    "D5_strategy":     "qwen3.5:397b:cloud",         # 397B reasoning at scale, 14.1M pulls
    "D6_analysis":     "gemma4:31b:cloud",           # Frontier MoE analysis, 15.3M pulls
    "D7_general":      "deepseek-v4-flash:cloud",    # Default workhorse, 1M ctx, 129K pulls
    "D8_verification": "nemotron-3-ultra:cloud",     # 550B verification, 256K ctx, 13K pulls
    "D9_research":     "minimax-m3:cloud",           # BrowseComp 83.5, 1M ctx, 64.7K pulls
    "D10_think":       "deepseek-v4-pro:cloud",      # Deep reasoning, 1M ctx, 137K pulls
}

# ── Dimension-Aware Fallback Chains ──────────────────────────────────
#
# When D_N model fails, route to adjacent dimensions that can cover
# the same cognitive territory — NOT a flat list. This preserves
# the council's cognitive diversity.

DIMENSION_FALLBACK = {
    "D1_synthesis":    ["kimi-k2.7-code:cloud", "deepseek-v4-pro:cloud", "glm-5.2:cloud"],
    "D2_deep_reason":  ["qwen3.5:397b:cloud", "kimi-k2.6:cloud", "glm-5.2:cloud"],
    "D3_code":         ["glm-5.1:cloud", "kimi-k2.7-code:cloud", "qwen3.5:122b:cloud"],
    "D4_vision":       ["qwen3-vl:235b:cloud", "gemma4:31b:cloud"],
    "D5_strategy":     ["kimi-k2.6:cloud", "deepseek-v4-pro:cloud", "qwen3.5:122b:cloud"],
    "D6_analysis":     ["glm-5.2:cloud", "deepseek-v4-pro:cloud", "deepseek-v4-flash:cloud"],
    "D7_general":      ["qwen3.5:122b:cloud", "minimax-m3:cloud", "deepseek-v4-flash:cloud"],
    "D8_verification": ["deepseek-v4-pro:cloud", "gemma4:31b:cloud", "nemotron-3-super:cloud"],
    "D9_research":     ["kimi-k2.6:cloud", "deepseek-v4-pro:cloud", "qwen3.5:122b:cloud"],
    "D10_think":       ["kimi-k2.6:cloud", "qwen3.5:397b:cloud", "deepseek-v4-pro:cloud"],
}

# ── Dimension Descriptions ──────────────────────────────────────────

DIMENSION_DESCRIPTIONS = {
    "D1_synthesis":    "Converge perspectives into coherent whole",
    "D2_deep_reason":  "Analyze deeply, find hidden implications",
    "D3_code":         "Generate, review, verify code",
    "D4_vision":       "See and interpret visual information",
    "D5_strategy":     "Plan strategically, weigh trade-offs",
    "D6_analysis":     "Break down complex systems quantitatively",
    "D7_general":      "Fast general-purpose reasoning",
    "D8_verification": "Fact-check, accuracy gate",
    "D9_research":     "Gather and synthesize information",
    "D10_think":       "Slow, thorough, second-order reasoning",
}

# ── Cost Table (per 1K output tokens, approximate USD) ──────────────

MODEL_COST_USD = {
    "kimi-k2.6:cloud":         3.00,
    "kimi-k2.7-code:cloud":    3.00,
    "qwen3.5:122b:cloud":      4.00,
    "qwen3.5:397b:cloud":      6.00,
    "glm-5.1:cloud":           5.00,
    "glm-5.2:cloud":           5.00,
    "minimax-m3:cloud":        2.50,
    "gemma4:31b:cloud":        1.50,
    "deepseek-v4-flash:cloud": 0.60,
    "deepseek-v4-pro:cloud":   2.50,
    "nemotron-3-ultra:cloud":  1.20,
    "nemotron-3-super:cloud":  1.00,
    "qwen3-vl:235b:cloud":     4.00,
    "gemma4:12b:cloud":        0.40,
    "qwen3.5:9b:cloud":        0.20,
    "nemotron-3-nano:cloud":   0.10,
}

# ── Capability Scores (0-10) per task family ────────────────────────

CAPABILITY_MATRIX = {
    "kimi-k2.6:cloud": {
        "research": 7, "code": 7, "analysis": 8, "writing": 7,
        "optimization": 7, "orchestration": 10, "integration": 9,
    },
    "kimi-k2.7-code:cloud": {
        "research": 7, "code": 9, "analysis": 8, "writing": 7,
        "optimization": 8, "orchestration": 9, "integration": 8,
    },
    "qwen3.5:122b:cloud": {
        "research": 10, "code": 9, "analysis": 10, "writing": 8,
        "optimization": 8, "orchestration": 6, "integration": 5,
    },
    "qwen3.5:397b:cloud": {
        "research": 10, "code": 8, "analysis": 10, "writing": 9,
        "optimization": 9, "orchestration": 7, "integration": 6,
    },
    "glm-5.1:cloud": {
        "research": 6, "code": 10, "analysis": 8, "writing": 6,
        "optimization": 9, "orchestration": 5, "integration": 5,
    },
    "glm-5.2:cloud": {
        "research": 7, "code": 10, "analysis": 9, "writing": 7,
        "optimization": 10, "orchestration": 6, "integration": 6,
    },
    "minimax-m3:cloud": {
        "research": 9, "code": 8, "analysis": 7, "writing": 8,
        "optimization": 7, "orchestration": 6, "integration": 6,
    },
    "gemma4:31b:cloud": {
        "research": 8, "code": 8, "analysis": 8, "writing": 7,
        "optimization": 7, "orchestration": 5, "integration": 5,
    },
    "deepseek-v4-flash:cloud": {
        "research": 6, "code": 7, "analysis": 7, "writing": 5,
        "optimization": 6, "orchestration": 4, "integration": 4,
    },
    "deepseek-v4-pro:cloud": {
        "research": 9, "code": 8, "analysis": 9, "writing": 7,
        "optimization": 8, "orchestration": 6, "integration": 5,
    },
    "nemotron-3-ultra:cloud": {
        "research": 6, "code": 5, "analysis": 7, "writing": 5,
        "optimization": 5, "orchestration": 8, "integration": 7,
    },
    "nemotron-3-super:cloud": {
        "research": 6, "code": 7, "analysis": 7, "writing": 6,
        "optimization": 6, "orchestration": 9, "integration": 8,
    },
    "qwen3-vl:235b:cloud": {
        "research": 4, "code": 5, "analysis": 5, "writing": 4,
        "optimization": 3, "orchestration": 3, "integration": 3,
    },
    # Fallback models
    "gemma4:12b:cloud":       {"research": 5, "code": 6, "analysis": 6, "writing": 4, "optimization": 5, "orchestration": 3, "integration": 3},
    "qwen3.5:9b:cloud":       {"research": 5, "code": 5, "analysis": 6, "writing": 4, "optimization": 4, "orchestration": 3, "integration": 3},
    "nemotron-3-nano:cloud":  {"research": 3, "code": 4, "analysis": 4, "writing": 3, "optimization": 3, "orchestration": 3, "integration": 3},
}

# ── Task Type → Specialized Model Candidates ────────────────────────

SUBTASK_TYPE_TO_SPECIALIZATION = {
    "research":        ["qwen3.5:122b:cloud", "minimax-m3:cloud", "deepseek-v4-pro:cloud"],
    "code_generation": ["glm-5.2:cloud", "kimi-k2.7-code:cloud", "glm-5.1:cloud"],
    "code_review":     ["glm-5.2:cloud", "glm-5.1:cloud", "qwen3.5:122b:cloud"],
    "testing":         ["qwen3.5:122b:cloud", "gemma4:31b:cloud", "deepseek-v4-flash:cloud"],
    "documentation":   ["qwen3.5:122b:cloud", "gemma4:31b:cloud", "kimi-k2.6:cloud"],
    "analysis":        ["qwen3.5:122b:cloud", "deepseek-v4-pro:cloud", "gemma4:31b:cloud"],
    "writing":         ["qwen3.5:122b:cloud", "gemma4:31b:cloud", "deepseek-v4-pro:cloud"],
    "synthesis":       ["kimi-k2.6:cloud", "deepseek-v4-pro:cloud", "qwen3.5:122b:cloud"],
    "optimization":    ["glm-5.2:cloud", "glm-5.1:cloud", "deepseek-v4-pro:cloud"],
    "data_processing": ["deepseek-v4-flash:cloud", "nemotron-3-ultra:cloud", "gemma4:31b:cloud"],
    "visualization":   ["gemma4:31b:cloud", "minimax-m3:cloud", "kimi-k2.6:cloud"],
    "integration":     ["kimi-k2.6:cloud", "nemotron-3-ultra:cloud", "deepseek-v4-pro:cloud"],
}

# ── Task Type → Optimal Single Model ────────────────────────────────

TASK_ROUTING = {
    "orchestration":     "kimi-k2.6:cloud",
    "deep_reasoning":    "qwen3.5:122b:cloud",
    "coding":            "glm-5.2:cloud",
    "vision":            "minimax-m3:cloud",
    "strategy":          "qwen3.5:397b:cloud",
    "analysis":          "gemma4:31b:cloud",
    "general":           "deepseek-v4-flash:cloud",
    "verification":      "nemotron-3-ultra:cloud",
    "research":          "minimax-m3:cloud",
    "think":             "deepseek-v4-pro:cloud",
    "chat":              "qwen3.5:9b:cloud",
    "fast_classify":     "nemotron-3-nano:cloud",
}

# ── Phase Participation ──────────────────────────────────────────────

# Which dimensions participate in the brain phase (WHAT to do)
BRAIN_PHASE_DIMENSIONS = [
    "D1_synthesis", "D2_deep_reason", "D5_strategy",
    "D6_analysis", "D7_general", "D8_verification", "D9_research",
]

# Which dimensions participate in the swarm phase (HOW to do it) — all of them
SWARM_PHASE_DIMENSIONS = list(DIMENSION_MAP.keys())

# ── Legacy Aliases ───────────────────────────────────────────────────

DIMENSION_MAP_V2 = DIMENSION_MAP
DIMENSION_FALLBACK_V2 = DIMENSION_FALLBACK
OLLAMA_CLOUD_MODELS = list(MODEL_COST_USD.keys())
TASK_TYPE_TO_MODEL = TASK_ROUTING
