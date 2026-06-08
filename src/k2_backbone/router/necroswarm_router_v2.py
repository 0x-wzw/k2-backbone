"""NecroSwarm Router v2 — Single Source of Truth via dimension_map.py

Updated 2026-06-08: model definitions imported from neuroswarm/swarm/dimension_map.py.
All model changes go in dimension_map.py — this file reads from there.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import sys
_neuroswarm_path = Path(__file__).parent.parent.parent / "frameworks" / "neuroswarm"
if str(_neuroswarm_path) not in sys.path:
    sys.path.insert(0, str(_neuroswarm_path))

from neuroswarm.swarm.dimension_map import (
    DIMENSION_MAP,
    DIMENSION_FALLBACK,
    DIMENSION_DESCRIPTIONS,
)


# ── Data classes ──────────────────────────────────────────────────────

class ModelTier(str, Enum):
    T0_PREMIUM = "T0"
    T1_STANDARD = "T1"
    T2_BALANCED = "T2"
    T3_ECONOMY = "T3"
    T4_EMERGENCY = "T4"


# ── Model Registry (cost + metadata only; model list from dimension_map) ──

MODEL_COST_USD: dict[str, float] = {
    "kimi-k2.6:cloud":         3.00,
    "qwen3.5:122b:cloud":      4.00,
    "glm-5.1:cloud":           5.00,
    "qwen3-vl:235b:cloud":     4.00,
    "qwen3.5:397b:cloud":      6.00,
    "gemma4:26b:cloud":        1.50,
    "deepseek-v4-flash:cloud": 0.60,
    "nemotron-3-ultra:cloud":  1.20,
    "minimax-m3:cloud":        2.50,
    "deepseek-v4-pro:cloud":   2.50,
    "gemma4:12b:cloud":        0.40,
    "qwen3.5:9b:cloud":        0.20,
    "nemotron-3-nano:cloud":   0.10,
}

MODEL_METADATA: dict[str, dict[str, Any]] = {
    "kimi-k2.6:cloud":         {"context_window": 128000, "max_output_tokens": 16384, "tier": ModelTier.T0_PREMIUM},
    "qwen3.5:122b:cloud":      {"context_window": 128000, "max_output_tokens": 8192, "tier": ModelTier.T1_STANDARD},
    "glm-5.1:cloud":           {"context_window": 128000, "max_output_tokens": 8192, "tier": ModelTier.T1_STANDARD},
    "qwen3-vl:235b:cloud":     {"context_window": 128000, "max_output_tokens": 8192, "tier": ModelTier.T1_STANDARD},
    "qwen3.5:397b:cloud":      {"context_window": 128000, "max_output_tokens": 16384, "tier": ModelTier.T1_STANDARD},
    "gemma4:26b:cloud":        {"context_window": 256000, "max_output_tokens": 8192, "tier": ModelTier.T1_STANDARD},
    "deepseek-v4-flash:cloud": {"context_window": 1000000, "max_output_tokens": 32768, "tier": ModelTier.T2_BALANCED},
    "nemotron-3-ultra:cloud":  {"context_window": 128000, "max_output_tokens": 16384, "tier": ModelTier.T0_PREMIUM},
    "minimax-m3:cloud":        {"context_window": 1000000, "max_output_tokens": 16384, "tier": ModelTier.T0_PREMIUM},
    "deepseek-v4-pro:cloud":   {"context_window": 1000000, "max_output_tokens": 32768, "tier": ModelTier.T0_PREMIUM},
    "gemma4:12b:cloud":        {"context_window": 256000, "max_output_tokens": 8192, "tier": ModelTier.T3_ECONOMY},
    "qwen3.5:9b:cloud":        {"context_window": 128000, "max_output_tokens": 8192, "tier": ModelTier.T3_ECONOMY},
    "nemotron-3-nano:cloud":   {"context_window": 128000, "max_output_tokens": 8192, "tier": ModelTier.T3_ECONOMY},
}

# Task type → best model (synthed from DIMENSION_MAP descriptions)
TASK_ROUTING: dict[str, dict[str, Any]] = {
    "orchestration":     {"model": DIMENSION_MAP["D1_synthesis"],    "tier": ModelTier.T0_PREMIUM},
    "deep_reasoning":    {"model": DIMENSION_MAP["D2_deep_reason"],  "tier": ModelTier.T1_STANDARD},
    "coding":            {"model": DIMENSION_MAP["D3_code"],         "tier": ModelTier.T1_STANDARD},
    "vision":            {"model": DIMENSION_MAP["D4_vision"],       "tier": ModelTier.T1_STANDARD},
    "strategy":          {"model": DIMENSION_MAP["D5_strategy"],     "tier": ModelTier.T1_STANDARD},
    "analysis":          {"model": DIMENSION_MAP["D6_analysis"],     "tier": ModelTier.T1_STANDARD},
    "general":           {"model": DIMENSION_MAP["D7_general"],      "tier": ModelTier.T2_BALANCED},
    "verification":      {"model": DIMENSION_MAP["D8_verification"], "tier": ModelTier.T0_PREMIUM},
    "research":          {"model": DIMENSION_MAP["D9_research"],     "tier": ModelTier.T0_PREMIUM},
    "think":             {"model": DIMENSION_MAP["D10_think"],       "tier": ModelTier.T0_PREMIUM},
    "chat":              {"model": "qwen3.5:9b:cloud",               "tier": ModelTier.T3_ECONOMY},
    "fast_classify":     {"model": "nemotron-3-nano:cloud",           "tier": ModelTier.T3_ECONOMY},
}


# ── Router ───────────────────────────────────────────────────────────

class NecroSwarmRouterV2:
    """Cost-optimized model routing. Model definitions from dimension_map (single source of truth)."""

    def __init__(self, cost_budget: Optional[float] = None):
        self.cost_budget = cost_budget
        self.dimension_map = dict(DIMENSION_MAP)
        self.dimension_fallback = dict(DIMENSION_FALLBACK)
        self.task_routing = dict(TASK_ROUTING)
        self.metadata = MODEL_METADATA
        self.cost_table = MODEL_COST_USD

    def route(self, task_type: str, complexity: str = "MODERATE") -> dict[str, Any]:
        if task_type not in self.task_routing:
            task_type = "general"

        route = dict(self.task_routing[task_type])
        model_id = route["model"]
        meta = self.metadata.get(model_id, {})

        dimension = None
        for dim, mid in self.dimension_map.items():
            if mid == model_id:
                dimension = dim
                break
        if dimension is None:
            dimension = "D7_general"

        fallback = list(self.dimension_fallback.get(dimension, []))

        return {
            "model_id": model_id,
            "dimension": dimension,
            "tier": route["tier"],
            "fallback_chain": fallback,
            "task_type": task_type,
            "complexity": complexity,
            "cost_estimate": self._estimate_cost(model_id, complexity),
            "context_window": meta.get("context_window", 128000),
            "routed_at": datetime.utcnow().isoformat(),
        }

    def get_dimension_model(self, dimension: str) -> Optional[str]:
        return self.dimension_map.get(dimension)

    def list_models_by_tier(self, tier: ModelTier) -> list[dict[str, Any]]:
        return [
            {"model_id": mid, **self.metadata.get(mid, {})}
            for mid in self.dimension_map.values()
            if self.metadata.get(mid, {}).get("tier") == tier
        ]

    def _estimate_cost(self, model_id: str, complexity: str) -> dict:
        base = self.cost_table.get(model_id, 1.0)
        multipliers = {"simple": 0.3, "moderate": 1.0, "complex": 2.5}
        mult = multipliers.get(complexity.lower(), 1.0)
        return {
            "per_request": f"${base * mult:.2f}",
            "model_cost_per_1k": base,
        }