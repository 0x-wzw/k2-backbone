from __future__ import annotations
"""
NecroSwarm Router v2 — Updated with Ollama Cloud Best-in-Class Models (2026-06-08)

Based on live benchmark analysis from ollama.com/search?c=cloud and model releases:
- Kimi K2.6: 289K pulls, swarm orchestration (300 agents, 4K steps)
- Minimax M3 (June 1): 1M context, frontier coding + agentic
- Nemotron-3-Ultra (June 4): 550B/55B active, 5.9x throughput vs GLM-5.1
- Qwen3.5 122B: AIME 95.3%, 13.2M pulls, new SOTA reasoning
- Gemma4 26B/31B: frontier reasoning, agentic workflows, SWE-Bench
- DeepSeek V4 Pro: 1M context, $0.60/1K reasoning tokens
- GLM-5.1: SWE-Bench Pro 58.4%, code generation specialist
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
    """An Ollama Cloud model definition."""
    model_id: str                # e.g. "kimi-k2.6:cloud"
    display_name: str            # Human-readable name
    tier: ModelTier              # Cost/quality tier
    dimensions: list[str]        # Which 10-D dimensions this serves
    context_window: int          # Max tokens
    max_output_tokens: int       # Max generation
    description: str             # Why this model is here
    released: str                # Release date or "rolling"
    pulled: str                  # Approximate pull count
    fallback_models: list[str]   # Dimension-aware fallback chain


# ── 2026-06-08 Model Registry ─────────────────────────────────────────
# Updated from ollama.com/search?c=cloud — verified live

MODEL_REGISTRY: dict[str, OllamaModel] = {
    # ── T0 PREMIUM — absolute best, cost-blind ────────────────────────

    "kimi-k2.6:cloud": OllamaModel(
        model_id="kimi-k2.6:cloud",
        display_name="Kimi K2.6",
        tier=ModelTier.T0_PREMIUM,
        dimensions=["D10_think", "D1_synthesis"],
        context_window=128_000,
        max_output_tokens=16_384,
        description="Swarm orchestration, long-horizon coding, proactive autonomous execution. Native multimodal agent.",
        released="2026-05",
        pulled="289K",
        fallback_models=["deepseek-v4-pro:cloud", "glm-5.1:cloud"],
    ),

    "deepseek-v4-pro:cloud": OllamaModel(
        model_id="deepseek-v4-pro:cloud",
        display_name="DeepSeek V4 Pro",
        tier=ModelTier.T0_PREMIUM,
        dimensions=["D2_deep_reason", "D10_think"],
        context_window=1_000_000,
        max_output_tokens=32_768,
        description="Frontier MoE with 1M context, three reasoning modes (deep/creative/standard). $0.60/1K reasoning tokens.",
        released="2026-05",
        pulled="110K",
        fallback_models=["kimi-k2.6:cloud", "glm-5.1:cloud"],
    ),

    "nemotron-3-ultra:cloud": OllamaModel(
        model_id="nemotron-3-ultra:cloud",
        display_name="Nemotron 3 Ultra",
        tier=ModelTier.T0_PREMIUM,
        dimensions=["D8_verification", "D6_analysis"],
        context_window=128_000,
        max_output_tokens=16_384,
        description="550B/55B active. 5.9x throughput vs GLM-5.1, 300+ tok/s output. Best US open model for long-running agents.",
        released="2026-06-04",
        pulled="4K",
        fallback_models=["deepseek-v4-pro:cloud", "glm-5.1:cloud"],
    ),

    "minimax-m3:cloud": OllamaModel(
        model_id="minimax-m3:cloud",
        display_name="MiniMax M3",
        tier=ModelTier.T0_PREMIUM,
        dimensions=["D9_research", "D7_general"],
        context_window=1_000_000,
        max_output_tokens=16_384,
        description="Frontier coding + agentic + 1M context + native multimodality. First open model with all three. MSA architecture.",
        released="2026-06-01",
        pulled="31K",
        fallback_models=["kimi-k2.6:cloud", "deepseek-v4-pro:cloud"],
    ),

    # ── T1 STANDARD — best-in-class for task type ─────────────────────

    "qwen3.5:122b:cloud": OllamaModel(
        model_id="qwen3.5:122b:cloud",
        display_name="Qwen 3.5 122B",
        tier=ModelTier.T1_STANDARD,
        dimensions=["D2_deep_reason", "D5_strategy"],
        context_window=128_000,
        max_output_tokens=8_192,
        description="AIME 95.3%, HMMT 100%. New SOTA open reasoning model. 13M pulls — community favorite.",
        released="2026-05",
        pulled="13.2M",
        fallback_models=["deepseek-v4-flash:cloud", "glm-5.1:cloud"],
    ),

    "qwen3.5:397b:cloud": OllamaModel(
        model_id="qwen3.5:397b:cloud",
        display_name="Qwen 3.5 397B",
        tier=ModelTier.T1_STANDARD,
        dimensions=["D5_strategy", "D10_think"],
        context_window=128_000,
        max_output_tokens=16_384,
        description="Best open general model overall. 397B with 17B active MoE. Used as current October runtime.",
        released="2026-05",
        pulled="13.2M",
        fallback_models=["gemma4:26b:cloud", "glm-5.1:cloud"],
    ),

    "glm-5.1:cloud": OllamaModel(
        model_id="glm-5.1:cloud",
        display_name="GLM-5.1",
        tier=ModelTier.T1_STANDARD,
        dimensions=["D3_code", "D7_general"],
        context_window=128_000,
        max_output_tokens=8_192,
        description="SWE-Bench Pro SOTA (58.4%). Best coding model for agentic engineering. 744B total, 40B active.",
        released="2026-04",
        pulled="2.2M",
        fallback_models=["qwen3.5:122b:cloud", "deepseek-v4-flash:cloud"],
    ),

    "gemma4:26b:cloud": OllamaModel(
        model_id="gemma4:26b:cloud",
        display_name="Gemma 4 26B",
        tier=ModelTier.T1_STANDARD,
        dimensions=["D6_analysis", "D8_verification"],
        context_window=256_000,
        max_output_tokens=8_192,
        description="Google DeepMind's frontier open model. MoE architecture. Strong reasoning + agentic + multimodal. Apache 2.0.",
        released="2026-04",
        pulled="12.4M",
        fallback_models=["glm-5.1:cloud", "deepseek-v4-flash:cloud"],
    ),

    "nemotron-3-super:cloud": OllamaModel(
        model_id="nemotron-3-super:cloud",
        display_name="Nemotron 3 Super",
        tier=ModelTier.T1_STANDARD,
        dimensions=["D8_verification", "D6_analysis"],
        context_window=128_000,
        max_output_tokens=8_192,
        description="120B MoE, 12B active. Efficient multi-agent verification. Good fallback to Ultra.",
        released="2026-04",
        pulled="2.4M",
        fallback_models=["gemma4:26b:cloud", "glm-5.1:cloud"],
    ),

    # ── T2 BALANCED — good performance, cost-aware ────────────────────

    "deepseek-v4-flash:cloud": OllamaModel(
        model_id="deepseek-v4-flash:cloud",
        display_name="DeepSeek V4 Flash",
        tier=ModelTier.T2_BALANCED,
        dimensions=["D2_deep_reason", "D7_general"],
        context_window=1_000_000,
        max_output_tokens=32_768,
        description="284B/13B active MoE. 1M context at $0.60/1K. Current T0 chat model. Efficient for most tasks.",
        released="2026-05",
        pulled="109K",
        fallback_models=["qwen3.5:122b:cloud", "glm-5.1:cloud"],
    ),

    "qwen3.5:9b:cloud": OllamaModel(
        model_id="qwen3.5:9b:cloud",
        display_name="Qwen 3.5 9B",
        tier=ModelTier.T2_BALANCED,
        dimensions=["D7_general"],
        context_window=128_000,
        max_output_tokens=8_192,
        description="Fast general-purpose. Good for routing, classification, fast responses.",
        released="2026-05",
        pulled="13.2M",
        fallback_models=["deepseek-v4-flash:cloud"],
    ),

    "minimax-m2.5:cloud": OllamaModel(
        model_id="minimax-m2.5:cloud",
        display_name="MiniMax M2.5",
        tier=ModelTier.T2_BALANCED,
        dimensions=["D9_research"],
        context_window=128_000,
        max_output_tokens=8_192,
        description="Previous-gen MiniMax. Solid for research synthesis. M3 replacement when budget matters.",
        released="2026-03",
        pulled="2.2M",
        fallback_models=["deepseek-v4-flash:cloud", "qwen3.5:122b:cloud"],
    ),

    # ── T3 ECONOMY — cheap, acceptable quality ────────────────────────

    "gemma4:12b:cloud": OllamaModel(
        model_id="gemma4:12b:cloud",
        display_name="Gemma 4 12B",
        tier=ModelTier.T3_ECONOMY,
        dimensions=["D6_analysis", "D7_general"],
        context_window=256_000,
        max_output_tokens=8_192,
        description="MMLU Pro 77.2%, beats Gemma 3 27B. Strong value. 256K context.",
        released="2026-04",
        pulled="12.4M",
        fallback_models=["qwen3.5:9b:cloud"],
    ),

    "nemotron-3-nano:cloud": OllamaModel(
        model_id="nemotron-3-nano:cloud",
        display_name="Nemotron 3 Nano 4B",
        tier=ModelTier.T3_ECONOMY,
        dimensions=["D7_general", "D8_verification"],
        context_window=128_000,
        max_output_tokens=8_192,
        description="4B parameter efficiency king. Fast classification and verification.",
        released="2026-04",
        pulled="512K",
        fallback_models=["gemma4:12b:cloud"],
    ),

    # ── Vision-Only Models ────────────────────────────────────────────

    "qwen3-vl:235b:cloud": OllamaModel(
        model_id="qwen3-vl:235b:cloud",
        display_name="Qwen3-VL 235B",
        tier=ModelTier.T1_STANDARD,
        dimensions=["D4_vision"],
        context_window=128_000,
        max_output_tokens=8_192,
        description="Best vision-language model. 235B. No vision fallback — this is the only vision dimension.",
        released="2025-11",
        pulled="4M",
        fallback_models=[],  # Vision is specialized, no good fallback
    ),
}


# ── 10-D Dimension Map ────────────────────────────────────────────────

DIMENSION_MAP_V2: dict[str, str] = {
    "D1_synthesis":    "kimi-k2.6:cloud",            # Orchestration, convergence
    "D2_deep_reason":  "qwen3.5:122b:cloud",         # Reasoning SOTA
    "D3_code":         "glm-5.1:cloud",              # SWE-Bench Pro leader
    "D4_vision":       "qwen3-vl:235b:cloud",        # Vision — no substitute
    "D5_strategy":     "qwen3.5:397b:cloud",         # Strategy at scale
    "D6_analysis":     "gemma4:26b:cloud",           # Frontier analysis
    "D7_general":      "deepseek-v4-flash:cloud",    # Default workhorse
    "D8_verification": "nemotron-3-ultra:cloud",     # Verification gate
    "D9_research":     "minimax-m3:cloud",           # 1M context synthesis
    "D10_think":       "deepseek-v4-pro:cloud",      # Deep reasoning
}

# Dimension-aware fallback chains
DIMENSION_FALLBACK_V2: dict[str, list[str]] = {
    "D1_synthesis":    ["deepseek-v4-pro:cloud", "glm-5.1:cloud"],
    "D2_deep_reason":  ["kimi-k2.6:cloud", "glm-5.1:cloud"],
    "D3_code":         ["qwen3.5:122b:cloud", "deepseek-v4-flash:cloud"],
    "D4_vision":       [],  # No vision fallback available
    "D5_strategy":     ["kimi-k2.6:cloud", "deepseek-v4-pro:cloud"],
    "D6_analysis":     ["glm-5.1:cloud", "deepseek-v4-flash:cloud"],
    "D7_general":      ["qwen3.5:122b:cloud", "minimax-m3:cloud"],
    "D8_verification": ["deepseek-v4-pro:cloud", "gemma4:26b:cloud"],
    "D9_research":     ["kimi-k2.6:cloud", "deepseek-v4-pro:cloud"],
    "D10_think":       ["kimi-k2.6:cloud", "qwen3.5:397b:cloud"],
}


# ── Task Type → Optimal Model ────────────────────────────────────────

TASK_ROUTING = {
    "orchestration":     {"model": "kimi-k2.6:cloud",       "tier": ModelTier.T0_PREMIUM},
    "deep_reasoning":    {"model": "qwen3.5:122b:cloud",    "tier": ModelTier.T1_STANDARD},
    "coding":            {"model": "glm-5.1:cloud",         "tier": ModelTier.T1_STANDARD},
    "strategy":          {"model": "qwen3.5:397b:cloud",    "tier": ModelTier.T1_STANDARD},
    "analysis":          {"model": "gemma4:26b:cloud",      "tier": ModelTier.T1_STANDARD},
    "research":          {"model": "minimax-m3:cloud",      "tier": ModelTier.T0_PREMIUM},
    "general":           {"model": "deepseek-v4-flash:cloud","tier": ModelTier.T2_BALANCED},
    "verification":      {"model": "nemotron-3-ultra:cloud","tier": ModelTier.T0_PREMIUM},
    "chat":              {"model": "qwen3.5:9b:cloud",      "tier": ModelTier.T2_BALANCED},
    "fast_classify":     {"model": "nemotron-3-nano:cloud",  "tier": ModelTier.T3_ECONOMY},
}


# ── Router Logic ──────────────────────────────────────────────────────

class NecroSwarmRouterV2:
    """
    NecroSwarm Router v2 — Cost-optimized model routing across Ollama Cloud.
    
    Maps tasks to the optimal model based on:
    - Task type (coding, reasoning, research, etc.)
    - Complexity (SIMPLE / MODERATE / COMPLEX)
    - Cost tier (T0-T4)
    """
    
    def __init__(self, cost_budget: Optional[float] = None):
        self.cost_budget = cost_budget  # $/month cap
        self.model_registry = MODEL_REGISTRY
        self.dimension_map = DIMENSION_MAP_V2
        self.dimension_fallback = DIMENSION_FALLBACK_V2
        self.task_routing = TASK_ROUTING
    
    def route(self, task_type: str, complexity: str = "MODERATE") -> dict[str, Any]:
        """
        Route a task to the optimal model.
        
        Args:
            task_type: Type of task (orchestration, coding, reasoning, etc.)
            complexity: SIMPLE, MODERATE, or COMPLEX
            
        Returns:
            Route result with model, tier, fallback chain, cost estimate
        """
        if task_type not in self.task_routing:
            task_type = "general"
        
        route = dict(self.task_routing[task_type])
        model_id = route["model"]
        model_def = self.model_registry.get(model_id)
        
        # Find which dimension this model serves
        dimension = None
        for dim, mid in self.dimension_map.items():
            if mid == model_id:
                dimension = dim
                break
        if dimension is None and model_def:
            dimension = model_def.dimensions[0] if model_def.dimensions else "D7_general"
        
        # Build fallback chain
        fallback = []
        if dimension and dimension in self.dimension_fallback:
            fallback = self.dimension_fallback[dimension]
        
        result = {
            "model_id": model_id,
            "model": model_def,
            "dimension": dimension,
            "tier": route["tier"],
            "fallback_chain": fallback,
            "task_type": task_type,
            "complexity": complexity,
            "cost_estimate": self._estimate_cost(model_def, complexity),
            "context_window": model_def.context_window if model_def else 128_000,
            "routed_at": datetime.utcnow().isoformat(),
        }
        return result
    
    def get_dimension_model(self, dimension: str) -> Optional[str]:
        """Get the model ID for a specific 10-D dimension."""
        return self.dimension_map.get(dimension)
    
    def list_models_by_tier(self, tier: ModelTier) -> list[OllamaModel]:
        """List all models in a given tier."""
        return [m for m in self.model_registry.values() if m.tier == tier]
    
    def _estimate_cost(self, model: Optional[OllamaModel], complexity: str) -> dict:
        """Rough cost estimate per task based on tier."""
        if model is None:
            return {"per_request": "$0.50", "note": "unknown model"}
        
        base_costs = {
            ModelTier.T0_PREMIUM:  {"simple": "$0.50", "moderate": "$2.00", "complex": "$5.00"},
            ModelTier.T1_STANDARD: {"simple": "$0.25", "moderate": "$1.00", "complex": "$2.50"},
            ModelTier.T2_BALANCED: {"simple": "$0.10", "moderate": "$0.40", "complex": "$1.00"},
            ModelTier.T3_ECONOMY:  {"simple": "$0.05", "moderate": "$0.15", "complex": "$0.40"},
            ModelTier.T4_EMERGENCY:{"simple": "$0.02", "moderate": "$0.05", "complex": "$0.10"},
        }
        return {
            "per_request": base_costs.get(model.tier, base_costs[ModelTier.T2_BALANCED]).get(complexity.lower(), "$0.50"),
            "tier": model.tier.value,
        }