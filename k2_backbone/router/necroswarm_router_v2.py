"""
NecroSwarm Router v2 — Single Source of Truth via model-routing-table

Updated 2026-06-08: model definitions imported from model-routing-table.
All model changes go in model_routing_table/table.py — this file reads from there.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from model_routing_table import (
    DIMENSION_MAP,
    DIMENSION_FALLBACK,
    DIMENSION_DESCRIPTIONS,
)
from model_routing_table.table import (
    MODEL_COST_USD,
    TASK_ROUTING,
)


class ModelTier(str, Enum):
    T0_PREMIUM = "T0"
    T1_STANDARD = "T1"
    T2_BALANCED = "T2"
    T3_ECONOMY = "T3"
    T4_EMERGENCY = "T4"


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


class NecroSwarmRouterV2:
    """Cost-optimized model routing. Model definitions from model-routing-table (single source of truth)."""

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

        model_id = self.task_routing[task_type]
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
            "tier": meta.get("tier", ModelTier.T2_BALANCED),
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
        return {
            "per_request": f"${base * multipliers.get(complexity.lower(), 1.0):.2f}",
            "model_cost_per_1k": base,
        }