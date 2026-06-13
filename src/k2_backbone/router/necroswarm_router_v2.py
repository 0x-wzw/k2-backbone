from __future__ import annotations
"""
NecroSwarm Router v2.1 — Updated with Ollama Cloud Live Models (2026-06-13)

Synced against ollama.com/api/tags (42 models live).
Discontinued: glm-5.1, qwen3.5-122b, gemma4-e2b, qwen3.5-0.8b, gemini-3-flash
Replaced: glm-5.1→glm-5, qwen3.5-122b→qwen3.5, gemini-3-flash→gemini-3-flash-preview
Added: mistral-large-3, glm-4.7, gemma3-4b

T0 Premium: glm-5, qwen3.5
T1 Standard: kimi-k2.6, deepseek-v3.2, gemma4-31b, mistral-large-3
T2 Balanced: nemotron-3-super, devstral-small-2, glm-4.7, deepseek-v4-pro
T3 Economy: deepseek-v4-flash, gemini-3-flash-preview, qwen3-coder-next, minimax-m2.7
T4 Emergency: nemotron-3-nano, gemma3-4b
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


# ── Ollama Cloud Model Definitions ────────────────────────────────────

class ModelTier(str, Enum):
    T0_PREMIUM = "T0"      # Absolute best, cost be damned
    T1_STANDARD = "T1"     # Best-in-class for task type
    T2_BALANCED = "T2"     # Good performance, cost-aware
    T3_ECONOMY = "T3"      # Cheap, acceptable quality
    T4_EMERGENCY = "T4"    # Fallback only


@dataclass
class OllamaModel:
    id: str
    name: str
    params: str
    context: str
    tier: ModelTier
    cost_per_1m_tokens: float  # Estimated USD
    strengths: list[str]
    benchmarks: dict[str, float] = field(default_factory=dict)


OLLAMA_CLOUD_MODELS = {
    # T0 — Premium (cost be damned)
    "glm-5": OllamaModel(
        id="glm-5",
        name="GLM-5",
        params="744B (40B active)",
        context="Standard",
        tier=ModelTier.T0_PREMIUM,
        cost_per_1m_tokens=5.00,
        strengths=["code_generation", "agentic_engineering", "terminal_tasks", "complex_systems"],
        benchmarks={"SWE-Bench-Pro": 58.4, "Terminal-Bench-2.0": 63.5, "NL2Repo": 42.7}
    ),
    "qwen3.5": OllamaModel(
        id="qwen3.5",
        name="Qwen3.5",
        params="397B",
        context="Standard",
        tier=ModelTier.T0_PREMIUM,
        cost_per_1m_tokens=4.00,
        strengths=["reasoning", "math", "multilingual", "research"],
        benchmarks={"AIME-2026": 95.3, "HMMT-Feb-2026": 100, "MMLU-Pro": 87.8}
    ),

    # T1 — Best-in-class per task type
    "kimi-k2.6": OllamaModel(
        id="kimi-k2.6",
        name="Kimi K2.6",
        params="1.04T",
        context="256K",
        tier=ModelTier.T1_STANDARD,
        cost_per_1m_tokens=3.00,
        strengths=["orchestration", "swarm", "long_horizon_coding", "agentic"],
        benchmarks={"BrowseComp-Agent-Swarm": 86.3, "Agents": 300}
    ),
    "deepseek-v3.2": OllamaModel(
        id="deepseek-v3.2",
        name="DeepSeek V3.2",
        params="671B MoE",
        context="160K",
        tier=ModelTier.T1_STANDARD,
        cost_per_1m_tokens=2.00,
        strengths=["reasoning", "agent_performance", "coding", "general"],
        benchmarks={"LiveCodeBench": 81.2, "General": 85.0}
    ),
    "gemma4-31b": OllamaModel(
        id="gemma4-31b",
        name="Gemma4 31B",
        params="31B Dense",
        context="256K",
        tier=ModelTier.T1_STANDARD,
        cost_per_1m_tokens=1.50,
        strengths=["multimodal", "coding", "reasoning", "edge_deployable"],
        benchmarks={"LiveCodeBench-v6": 80.0, "MMLU-Pro": 85.2, "Codeforces-ELO": 2150}
    ),
    "mistral-large-3": OllamaModel(
        id="mistral-large-3",
        name="Mistral Large 3",
        params="675B",
        context="256K",
        tier=ModelTier.T1_STANDARD,
        cost_per_1m_tokens=2.00,
        strengths=["reasoning", "coding", "multilingual", "general"],
        benchmarks={"MMLU-Pro": 86.0, "LiveCodeBench": 82.0}
    ),

    # T2 — Balanced (good performance, cost-aware)
    "nemotron-3-super": OllamaModel(
        id="nemotron-3-super",
        name="Nemotron-3-Super",
        params="120B (12B active)",
        context="Standard",
        tier=ModelTier.T2_BALANCED,
        cost_per_1m_tokens=1.20,
        strengths=["multi_agent", "efficiency", "IT_automation", "long_context"],
        benchmarks={"RULER-256K": 96.3, "SWE-Bench-OpenHands": 60.47, "MMLU-Pro": 83.73}
    ),
    "devstral-small-2": OllamaModel(
        id="devstral-small-2",
        name="Devstral Small 2",
        params="24B",
        context="Standard",
        tier=ModelTier.T2_BALANCED,
        cost_per_1m_tokens=1.00,
        strengths=["code_review", "tool_use", "codebase_exploration", "SWE"],
        benchmarks={"SWE-Bench-Verified": 65.8, "Terminal-Bench": 32.0}
    ),
    "glm-4.7": OllamaModel(
        id="glm-4.7",
        name="GLM-4.7",
        params="Dense",
        context="Standard",
        tier=ModelTier.T2_BALANCED,
        cost_per_1m_tokens=1.80,
        strengths=["complex_systems", "long_horizon", "reasoning"],
        benchmarks={"General": 82.0}
    ),
    "deepseek-v4-pro": OllamaModel(
        id="deepseek-v4-pro",
        name="DeepSeek V4 Pro",
        params="Frontier MoE",
        context="1M",
        tier=ModelTier.T2_BALANCED,
        cost_per_1m_tokens=2.50,
        strengths=["reasoning", "long_context", "three_modes"],
        benchmarks={"Frontier": 88.0}
    ),

    # T3 — Economy (cheap, acceptable)
    "deepseek-v4-flash": OllamaModel(
        id="deepseek-v4-flash",
        name="DeepSeek V4 Flash",
        params="284B (13B active)",
        context="1M",
        tier=ModelTier.T3_ECONOMY,
        cost_per_1m_tokens=0.60,
        strengths=["budget", "long_context", "efficiency"],
        benchmarks={"Efficiency": 85.0}
    ),
    "gemini-3-flash-preview": OllamaModel(
        id="gemini-3-flash-preview",
        name="Gemini 3 Flash Preview",
        params="Dense",
        context="Standard",
        tier=ModelTier.T3_ECONOMY,
        cost_per_1m_tokens=0.50,
        strengths=["speed", "frontier_intelligence", "low_cost"],
        benchmarks={"Speed": 95.0}
    ),
    "qwen3-coder-next": OllamaModel(
        id="qwen3-coder-next",
        name="Qwen3 Coder Next",
        params="Dense",
        context="Standard",
        tier=ModelTier.T3_ECONOMY,
        cost_per_1m_tokens=0.80,
        strengths=["agentic_coding", "local_development"],
        benchmarks={"SWE-Bench": 69.6}
    ),
    "minimax-m2.7": OllamaModel(
        id="minimax-m2.7",
        name="MiniMax M2.7",
        params="Dense",
        context="Standard",
        tier=ModelTier.T3_ECONOMY,
        cost_per_1m_tokens=1.00,
        strengths=["coding", "agentic", "productivity"],
        benchmarks={"General": 78.0}
    ),

    # T4 — Emergency fallback
    "nemotron-3-nano": OllamaModel(
        id="nemotron-3-nano",
        name="Nemotron-3-Nano",
        params="30B",
        context="Standard",
        tier=ModelTier.T4_EMERGENCY,
        cost_per_1m_tokens=0.10,
        strengths=["ultra_cheap", "agentic", "efficient"],
        benchmarks={"Efficiency": 70.0}
    ),
    "gemma3-4b": OllamaModel(
        id="gemma3-4b",
        name="Gemma3 4B",
        params="4B",
        context="128K",
        tier=ModelTier.T4_EMERGENCY,
        cost_per_1m_tokens=0.08,
        strengths=["edge", "multimodal", "ultra_low_cost"],
        benchmarks={"Edge": 60.0}
    ),
}


# ── Task Type → Best Model Mapping ──────────────────────────────────

TASK_TYPE_TO_MODEL = {
    # Chat / Conversation — T3 with deepseek-v4-flash (fast, efficient, good for chat)
    "chat":                ["deepseek-v4-flash", "kimi-k2.6", "deepseek-v3.2"],
    "conversation":        ["deepseek-v4-flash", "kimi-k2.6", "deepseek-v3.2"],
    "dialogue":            ["deepseek-v4-flash", "kimi-k2.6", "deepseek-v3.2"],

    # Premium tasks — use T0/T1
    "code_generation":     ["glm-5", "deepseek-v3.2", "qwen3-coder-next"],
    "optimization":        ["glm-5", "deepseek-v3.2", "gemma4-31b"],
    "analysis":            ["qwen3.5", "deepseek-v3.2", "gemma4-31b"],
    "synthesis":           ["qwen3.5", "kimi-k2.6", "deepseek-v3.2"],
    "research":            ["qwen3.5", "gemma4-31b", "deepseek-v3.2"],
    "integration":         ["kimi-k2.6", "nemotron-3-super", "deepseek-v3.2"],

    # Standard tasks — use T1/T2
    "code_review":         ["devstral-small-2", "glm-5", "gemma4-31b"],
    "testing":             ["qwen3.5", "gemma4-31b", "devstral-small-2"],
    "documentation":       ["qwen3.5", "gemma4-31b", "kimi-k2.6"],
    "writing":             ["qwen3.5", "gemma4-31b", "deepseek-v3.2"],
    "data_processing":     ["deepseek-v3.2", "nemotron-3-super", "gemma4-31b"],
    "visualization":       ["gemma4-31b", "kimi-k2.6", "qwen3.5"],

    # Budget tasks — use T2/T3
    "review":              ["devstral-small-2", "gemma4-31b", "deepseek-v4-flash"],
}

# ── Chat Configuration ────────────────────────────────────────────────
# K2 T0 Chat Model — deepseek-v4-flash:cloud
# Set via environment: export K2_CHAT_MODEL=deepseek-v4-flash
# This makes deepseek-v4-flash the default for chat/conversation tasks

CHAT_MODEL_CONFIG = {
    "default_chat_model": "deepseek-v4-flash",
    "fallback_chat_model": "kimi-k2.6",
    "chat_context_size": 1000000,  # 1M context for long conversations
    "chat_cost_per_1m": 0.60,
    "chat_strengths": ["fast_response", "long_context", "cost_efficient"],
    "chat_benchmarks": {"Response_Time": 95.0, "Context_Retention": 85.0},
}


# ── 10-D Council Configuration ──────────────────────────────────────

COUNCIL_SEATS = [
    {"id": "D1", "name": "Swarm Coordination",     "model": "kimi-k2.6",               "vote_power": 3},
    {"id": "D2", "name": "Engineering",            "model": "glm-5",                   "vote_power": 3},
    {"id": "D3", "name": "Deep Thinking",          "model": "qwen3.5",                 "vote_power": 3},
    {"id": "D4", "name": "General Purpose",        "model": "deepseek-v3.2",           "vote_power": 2},
    {"id": "D5", "name": "Multimodal",             "model": "gemma4-31b",              "vote_power": 2},
    {"id": "D6", "name": "Scale",                  "model": "nemotron-3-super",        "vote_power": 2},
    {"id": "D7", "name": "Code Review",            "model": "devstral-small-2",        "vote_power": 2},
    {"id": "D8", "name": "Economy",                "model": "deepseek-v4-flash",         "vote_power": 1},
    {"id": "D9", "name": "Agentic Coding",         "model": "qwen3-coder-next",        "vote_power": 1},
    {"id": "D10", "name": "Emergency",             "model": "nemotron-3-nano",         "vote_power": 1},
]


# ── Capability Matrix (task_family → model → score 0-10) ────────────

CAPABILITY_MATRIX = {
    "code": {
        "glm-5":               10.0,
        "deepseek-v3.2":       9.0,
        "qwen3-coder-next":    9.0,
        "devstral-small-2":    8.5,
        "gemma4-31b":          8.0,
        "kimi-k2.6":           7.5,
        "deepseek-v4-flash":   6.5,
        "gemini-3-flash-preview": 6.0,
        "nemotron-3-super":    5.5,
        "nemotron-3-nano":     4.0,
    },
    "analysis": {
        "qwen3.5":            10.0,
        "deepseek-v3.2":       9.0,
        "gemma4-31b":          8.0,
        "glm-5":               8.0,
        "kimi-k2.6":           7.5,
        "nemotron-3-super":    7.0,
        "devstral-small-2":    5.0,
        "deepseek-v4-flash":   6.5,
        "gemini-3-flash-preview": 6.0,
        "nemotron-3-nano":     4.0,
    },
    "research": {
        "qwen3.5":            10.0,
        "gemma4-31b":          8.5,
        "deepseek-v3.2":       8.0,
        "kimi-k2.6":           7.0,
        "nemotron-3-super":    6.5,
        "deepseek-v4-flash":   6.0,
        "gemini-3-flash-preview": 5.5,
        "nemotron-3-nano":     4.0,
    },
    "orchestration": {
        "kimi-k2.6":          10.0,
        "nemotron-3-super":    8.5,
        "deepseek-v3.2":       6.5,
        "qwen3.5":             6.0,
        "gemma4-31b":          5.5,
        "glm-5":               5.0,
        "deepseek-v4-flash":   5.0,
        "nemotron-3-nano":     4.5,
    },
    "writing": {
        "qwen3.5":             8.5,
        "gemma4-31b":          7.5,
        "deepseek-v3.2":       7.0,
        "kimi-k2.6":           7.0,
        "glm-5":               6.5,
        "deepseek-v4-flash":   5.5,
        "gemini-3-flash-preview": 5.5,
        "nemotron-3-nano":     4.0,
    },
    "optimization": {
        "glm-5":               9.0,
        "deepseek-v3.2":       8.0,
        "gemma4-31b":          7.0,
        "qwen3.5":             7.0,
        "kimi-k2.6":           7.0,
        "devstral-small-2":    5.0,
        "deepseek-v4-flash":   5.5,
        "nemotron-3-nano":     4.0,
    },
}


# ── Cost Matrix ─────────────────────────────────────────────────────

COST_PER_1K = {model_id: model.cost_per_1m_tokens / 1000 
               for model_id, model in OLLAMA_CLOUD_MODELS.items()}


# ── Legacy imports for compatibility ────────────────────────────────

# Keep old constants for backward compat
OLD_TO_NEW = {
    "kimi": "kimi-k2.6",
    "claude": "glm-5",        # GLM-5 replaces Claude for coding
    "deepseek": "deepseek-v3.2",
    "glm": "glm-5",
    "qwen": "qwen3.5",
    "glm-5.1": "glm-5",       # Discontinued → GLM-5
    "qwen3.5-122b": "qwen3.5", # Discontinued → Qwen3.5
    "gemini-3-flash": "gemini-3-flash-preview",  # Renamed
}


__all__ = [
    'OLLAMA_CLOUD_MODELS',
    'TASK_TYPE_TO_MODEL',
    'COUNCIL_SEATS',
    'CAPABILITY_MATRIX',
    'COST_PER_1K',
    'CHAT_MODEL_CONFIG',
    'ModelTier',
    'OllamaModel',
]
